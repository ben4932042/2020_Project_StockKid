import requests
from bs4 import BeautifulSoup
import pandas as pd
from google.cloud import storage
import random
from confluent_kafka import Consumer, KafkaException, KafkaError
import sys

secretFile = json.load(open("secretFile.txt",'r'))
server=secretFile['server']+':'+ secretFile['sever_port']

storage_client = storage.Client()
bucket = storage_client.get_bucket('stock_news')
# 用來接收從Consumer instance發出的error訊息
def error_cb(err):
    print('Error: %s' % err)


# 轉換msgKey或msgValue成為utf-8的字串
def try_decode_utf8(data):
    if data:
        return data.decode('utf-8')
    else:
        return None


# 當發生Re-balance時, 如果有partition被assign時被呼叫
def print_assignment(consumer, partitions):
    result = '[{}]'.format(','.join([p.topic + '-' + str(p.partition) for p in partitions]))
    print('Setting newly assigned partitions:', result)


# 當發生Re-balance時, 之前被assigned的partition會被移除
def print_revoke(consumer, partitions):
    result = '[{}]'.format(','.join([p.topic + '-' + str(p.partition) for p in partitions]))
    print('Revoking previously assigned partitions: ' + result)


if __name__ == '__main__':
    # 步驟1.設定要連線到Kafka集群的相關設定
    # Consumer configuration
    props = {
        'bootstrap.servers': server,         
        'group.id': 'iii',                       
        'auto.offset.reset': 'earliest',         
        'error_cb': error_cb             
    }

    # 步驟2. 產生一個Kafka的Consumer的實例
    consumer = Consumer(props)
    # 步驟3. 指定想要訂閱訊息的topic名稱
    topicName = 'PyETLbeta3'
    # 步驟4. 讓Consumer向Kafka集群訂閱指定的topic
    consumer.subscribe([topicName], on_assign=print_assignment, on_revoke=print_revoke)

    # 步驟5. 持續的拉取Kafka有進來的訊息
    try:
        while True:
            # 請求Kafka把新的訊息吐出來
            records = consumer.consume(num_messages=1, timeout=1000.0)  # 批次讀取
            if records is None:
                continue

            for record in records:
                # 檢查是否有錯誤
                if record is None:
                    continue
                if record.error():
                    # Error or event
                    if record.error().code() == KafkaError._PARTITION_EOF:
                        print('')
                    else:
                        raise KafkaException(record.error())
                else:

                    topic = record.topic()
                    partition = record.partition()
                    offset = record.offset()
                    timestamp = record.timestamp()
                    # 取出msgKey與msgValue
                    msgKey = try_decode_utf8(record.key())
                    msgValue = try_decode_utf8(record.value())

                    # 秀出metadata與msgKey & msgValue訊息
                    print(msgValue)
                    
                    Dict = eval(str(msgValue))
                    stock_name = [i for i in Dict.keys()][0]
                    stock_iid = [i for i in Dict.values()][0]

                    headerlist = [
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
                            "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36 OPR/43.0.2442.991",
                            "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36 OPR/42.0.2393.94",
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36 OPR/47.0.2631.39",
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36",
                            "Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36",
                            "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36",
                            "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0",
                            "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0",
                            "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:56.0) Gecko/20100101 Firefox/56.0",
                            "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko"
                                ]
                    cookies = {
                            'GED_PLAYLIST_ACTIVITY':'W3sidSI6ImpjSjciLCJ0c2wiOjE1OTQ1MzUzODEsIm52IjoxLCJ1cHQiOjE1OTQ1MzM2NTQsImx0IjoxNTk0NTM1MzgxfV0.',
                            'gliaplayer_ssid':'add53ac0-c403-11ea-a0ee-55725f3cbfcc',
                            'gliaplayer_uid':'add4eca0-c403-11ea-a0ee-55725f3cbfcc',
                            'gliaplayer_user_info':'{%22city%22:%22shinjuku%20city%22%2C%22ip%22:%222001:b400:e353:4cee:f814:ecb4:cda5:35eb%22%2C%22region%22:%2213%22%2C%22source%22:%22CF%22%2C%22latlong%22:%2235.693825%2C139.703356%22%2C%22country%22:%22TW%22}'
                                }
                    print('Start to clawer {}-{}'.format(stock_name,stock_iid))
                    for page in range(1,2):
                        url = "https://ess.api.cnyes.com/search/api/v1/news/keyword?q={}&limit=10&page={}".format(stock_name,page)
                        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'}
                        res = requests.get(url, headers=headers, cookies=cookies)
                        data = pd.read_json(res.text)
                        data = data.drop(columns = ['statusCode','message']).T.to_dict()
                        for subdata in data['items']['data']:
                            user_agent = random.choice(headerlist)
                            headers = {'User-Agent': user_agent}
                            try:
                                news_title = subdata['title'].replace('<mark>','').replace('</mark>','')
                                newID = subdata['newsId']
                                newsurl = 'https://news.cnyes.com/news/id/{}?exp=a'.format(newID)
                                news_summary = subdata['summary']
                                article_res = requests.get(newsurl, headers=headers, cookies=cookies)
                                article_soup = BeautifulSoup(article_res.text, 'html.parser')
                                news_date = article_soup.select('div[id="content"]')[0].time["datetime"].split('T')[0]
                                news_content = article_soup.select('div[itemprop="articleBody"]')[0].text
                                result = str({'title':news_title,
                                         'time':news_date,
                                         'summary':news_summary,
                                         'content':news_content,
                                         'url':newsurl})

                                blob = bucket.blob('{}/{}/{}.json'.format(stock_iid,news_date,newID))
                                blob.upload_from_string(result)
                                result = ''
                                print('{} success!'.format(news_title))

                            except:
                                pass # undefined
                    print('='*60)
                    
                    
                    
    except KeyboardInterrupt as e:
        sys.stderr.write('Aborted by user\n')
    except Exception as e:
        sys.stderr.write(e)

    finally:
        # 步驟6.關掉Consumer實例的連線
        consumer.close()





