#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
import codecs
import urllib2
import requests
import time
import json
import logging
import datetime
import os
import random



def crawl_content(url):
    try:
        r = urllib2.urlopen(url, 60)
        print r.getcode()
        print r.read()
        if r.getcode() != 200:
            return False
        result = json.loads(r.read())
        return result
    except Exception as e:
        return False


def crawl(url, try_num=3):
    try:
        for i in range(try_num):
            r = requests.get(url, timeout = 60)
            print r.status_code,
            if r.status_code != requests.codes.ok:
                return False
            r = r.text
            return r
    except Exception as e:
        return False

#http://data.10jqka.com.cn/market/longhu/date/2015-07-23/  总排行榜
# 按页排行榜
#http://data.10jqka.com.cn/market/longhu/cate/ALL/field/REMARK/page/2/date/2015-07-23/
#http://data.10jqka.com.cn/market/longhu/cate/ALL/field/REMARK/page/2/date/2015-07-23/order/asc/ajax/1/

# http://xueqiu.com/v4/stock/quote.json?code=SZ000681  个股最新价格
# http://xueqiu.com/stock/forchart/stocklist.json?symbol=SZ000681&period=1d&one_min=1  个股当天销售数据
# http://xueqiu.com/stock/pankou.json?symbol=SZ000681&_=1438135032243 盘口数据
# http://xueqiu.com/stock/forchartk/stocklist.json?symbol=SZ000687&period=1day&type=before&begin=1407602252104&end=1439138252104&_=1439138252105
# http://xueqiu.com/stock/forchartk/stocklist.json?symbol=SZ000687&period=1week&type=normal&begin=1312994077246&end=1439138077246&_=1439138077247
headers = {
    #'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'
    'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.107 Safari/537.36'
}
req = urllib2.Request(
    url = 'http://xueqiu.com/S/SZ000681',
    #data = postdata,
    headers = headers
)
r = urllib2.urlopen(req).read()
#print r



r = requests.get("http://xueqiu.com/S/SZ000681", headers=headers)

print r.status_code
print type(r.text)
print r.text

# 个股详情
#http://data.10jqka.com.cn/market/longhu/cjmx/300226/    获取有效日期
#r = requests.get("http://data.10jqka.com.cn/interface/market/cjmx/300226/2015-07-20", timeout=60)
#print r.status_code
#r = json.loads(r.text)  #print r.json()
#print r
#print r["data"]
#print type(r)

'''



from scrapy import log
#from scrapy import Request
from scrapy_redis.spiders import RedisSpider
from scrapySpider.items import stockItem
import codecs
import json


class StockSpider(RedisSpider):

    name = 'stockSpider'
    redis_key = 'stockSpider:start_urls'

    def parse(self, response):
        #print type(response)
        #print response.url

        item = stockItem()
        try:
            item['src'] = response.url
            item['content'] = json.loads(response.body_as_unicode())
            if 'success' in item['content'] and item['content']['success']=='true' \
                    and 'chartlist' in item['content'] and item['content']['chartlist']:
                yield item
            else:
                index = item['src'].find('code=')
                if index >= 0 and item['src'][index+5:index+13] in item['content']:
                    yield item
        except Exception as e:
            self.log('fail to parse content from response. url: {0}, err: {1}.'
                     ''.format(response.url, e), level=log.WARNING)

        #print response
		#file = codecs.open('data.txt','a','utf-8')
		#file.writelines(response.body_as_unicode())
		#pass


