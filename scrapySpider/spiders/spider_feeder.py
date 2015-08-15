# -*- coding: utf-8 -*-
import redis
import sys
import time
from pymongo import MongoClient


MONGODB_URI = 'mongodb://127.0.0.1:27017/'



class SpiderFeeder(object):

    def init(self, redis_server):

        self.mongo_client = MongoClient(MONGODB_URI)
        self.db = self.mongo_client['stock']
        self.col = self.db['table']

        self.init_scrapy_redis(redis_server)


    def init_scrapy_redis(self, redis_server):
        self.redis_key_prefix = 'stockSpider:'

        host, port = redis_server.split(':')
        self.redis_client = redis.StrictRedis(host=host, port=int(port))
        print self.redis_client

        return True


    def update_redis_info(self, src):
        key = self.redis_key_prefix + 'start_urls'
        self.redis_client.lpush(key, src)

        return True


    def run(self):
        self.update_redis_info('http://xueqiu.com')
        time.sleep(5)
        #self.update_redis_info('http://www.google.com')

        stockid = [i for i in range(1,101)]
        stockid.extend([i for i in range(150, 167)])
        stockid.extend([301, 333, 338])
        stockid.extend([i for i in range(400, 1000)])

        stockid.extend([i for i in range(2000,2777)])
        stockid.extend([i for i in range(300000,300489)])
        stockid.extend([i for i in range(600000,602000)])
        #stockid.extend([i for i in range(603000,604000)])
        stockid.extend(['SH000001', 'SZ399006'])

        #stockid = [681, 5]
        for id in stockid:
            isInt = isinstance(id, int)
            if isInt:
                if id < 600000:
                    id = 'SZ' + '0'*(6-len(str(id))) + str(id)
                else:
                    id = 'SH' + str(id)

            spec = {'stockId': id}
            _data = self.col.find_one(spec)
            if isInt and not _data: continue
            if not _data: _data = {}

            end = int(time.time()*1000)
            begin = end - 90*24*3600*1000

            if 'totalShares' not in _data:
                url = 'http://xueqiu.com/v4/stock/quote.json?code=' + id
                self.update_redis_info(url)
            if not _data.get('0day') or _data['0day'][-1][0]['time'] != "Fri Aug 14 09:30:00 +0800 2015":
                url = 'http://xueqiu.com/stock/forchart/stocklist.json?symbol=' + id + '&period=1d&one_min=1'
                self.update_redis_info(url)
            if not _data.get('1day') or _data['1day'][-1]['time'] != "Fri Aug 14 00:00:00 +0800 2015":
                url = 'http://xueqiu.com/stock/forchartk/stocklist.json?symbol=' + id + '&period=1day&type=before&begin=' + str(begin) + '&end=' + str(end)
                self.update_redis_info(url)

            #self.update_redis_info('http://xueqiu.com/stock/forchart/stocklist.json?symbol=SZ000681&period=1d&one_min=1')
            #self.update_redis_info('http://xueqiu.com/stock/forchartk/stocklist.json?symbol=SZ000681&period=1day&type=before&begin=1407602252104&end=1439138252104')





if __name__ == '__main__':

    #if len(sys.argv) != 2:
    #    print 'Usage: {0} conf_file'.format(__file__)
    #    sys.exit(1)

    spider_feed = SpiderFeeder()
    #spider_feed.init(sys.argv[1])
    spider_feed.init('127.0.0.1:6379')

    spider_feed.run()
