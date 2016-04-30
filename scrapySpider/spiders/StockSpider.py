#!/usr/bin/env python
# -*- coding: utf-8 -*-


#from scrapy import log
import logging
#from scrapy import Request
from scrapy_redis.spiders import RedisSpider
from scrapySpider.items import stockItem
#import codecs
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
            if item['src'].startswith("http://q.10jqka.com.cn/interface/stock/detail/zdf/desc/"): # 概念信息
                if item['content'].get('data'):
                    yield item

            elif item['src'].startswith("https://xueqiu.com/stock/forchart/stocklist.json?symbol=") or\
                item['src'].startswith("https://xueqiu.com/stock/forchartk/stocklist.json?symbol="): # 股票价格
                if item['content'].get('success')=='true' and item['content'].get('chartlist'):
                    if item['content']['chartlist'][0].get('current') != 0: # 没有停牌
                        yield item

            elif item['src'].startswith("https://xueqiu.com/v4/stock/quote.json?code="): # 股票基础信息（股数等）
                index = item['src'].find('code=')
                if index >= 0 and item['src'][index+5:index+13] in item['content']:
                    yield item

            elif item['src'].startswith("http://api.finance.ifeng.com/aminhis/?code="): # 股票1分钟级数据
                if item['content'] and item['content'][0].get('record'):
                    yield item

        except Exception as e:
            self.log('fail to parse content from response. url: {0}, err: {1}.'
                     ''.format(response.url, e), level=logging.WARNING)

        #print response
		#file = codecs.open('data.txt','a','utf-8')
		#file.writelines(response.body_as_unicode())
		#pass


