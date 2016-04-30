# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import datetime
import json
from pymongo import MongoClient
from scrapySpider.items import stockItem


MONGODB_URI = 'mongodb://127.0.0.1:27017/'


class ScrapyspiderPipeline(object):

    def __init__(self, mongodb_uri):
        self.mongodb_uri = mongodb_uri
        self.mongo_client = MongoClient(mongodb_uri)
        self.db = self.mongo_client['stock']
        self.col = self.db['table']
        self.gn = self.db['gn']

    @classmethod
    def from_settings(cls, settings):
        mongodb_uri = settings.get('MONGODB_URI', MONGODB_URI)
        return cls(mongodb_uri)

    # 保存股票价格信息，例子
    # https://xueqiu.com/stock/forchart/stocklist.json?symbol=SZ000681&period=1d&one_min=1
    # https://xueqiu.com/stock/forchartk/stocklist.json?symbol=SZ000681&\
    #   period=1day&type=before&begin=1407602252104&end=1439138252104
    def save_stock_price_info(self, url, data):
        if self.col.find_one() is None:
            self.col.ensure_index('stockId', unique=True, backgroud=True)

        # get stock id
        index = url.find('symbol=')
        stockId = url[index+7:index+15]

        _data = self.col.find_one({'stockId': stockId})
        if not _data: _data = {'stockId': stockId}

        # get data field
        if url.find('period=1day') >= 0:
            _data['1day'] = data['chartlist']
        elif url.find('period=1d&one_min=1') >= 0:
            # delete time info except the first and last one
            for i in range(1, len(data['chartlist'])-1):
                del data['chartlist'][i]['time']
            if '0day' not in _data:
                _data['0day'] = [data['chartlist']]
            elif _data['0day'][-1][0]['time'] != data['chartlist'][0]['time']:
                _data['0day'].append(data['chartlist'])
                if len(_data['0day']) > 20:
                    _data['0day'] = _data['0day'][1:]
            else:
                _data['0day'][-1] = data['chartlist']
        else:
            print 'error for this kind of url'
            return
        self.col.save(_data)

    # http://api.finance.ifeng.com/aminhis/?code=sz002131&type=early
    # http://api.finance.ifeng.com/aminhis/?code=sz002131&type=five
    def save_stock_minute_info(self, url, data):
        index = url.find('code=')
        stockId = url[index+5:index+13].upper()

        _data = self.col.find_one({'stockId': stockId})
        if not _data: _data = {'stockId': stockId}

        if not url.endswith('early') and not url.endswith('five'):
            print 'error to save trade info: ', url, data
            return
        elif url.endswith('early'):
            _data['minute_early_datetime'] = datetime.date.today().ctime()
            _data['minute'] = {}
        elif url.endswith('five'):
            _data['minute_five_datetime'] = datetime.date.today().ctime()
            if 'minute' not in _data: _data['minute'] = {}

        del_date = []
        for date in _data['minute']:
            delta = datetime.date.today() - datetime.date(int(date[0:4]),int(date[5:7]),int(date[8:10]))
            if delta.days > 120:
                del_date.append(date)
        for date in del_date:
                del _data['minute'][date]

        for Info in data:
            date = Info['record'][0][0][0:10]
            if date == '2015-10-07': continue
            value, index, N = [], 0, len(Info['record'])
            for s in Info['record']:
                s = [v.replace(',','') for v in s[:5]] # time price percent volume avg_price
                if index == 0 or index == N-1:
                    value.append([s[0],float(s[1]),float(s[2]),float(s[3]),float(s[4])])
                else:
                    value.append([float(s[1]),float(s[2]),float(s[3]),float(s[4])])
                index += 1
            _data['minute'][date] = json.dumps(value)
        self.col.save(_data)

    # 保存概念板块的所有股票信息，例子 URL = http://q.10jqka.com.cn/interface/stock/detail/zdf/desc/5/3/xgycxg
    def save_gn_info(self, url, data):
        # get mongo data
        if self.gn.find_one() is None:
            self.gn.ensure_index('name', unique=True, backgroud=True)

        gn = url[url.rfind('/')+1:]
        _data = self.gn.find_one({'name':gn})
        if not _data:
            _data = {'name': gn}

        stockIdList = []
        for stockInfo in data['data']:
            stockId = stockInfo['stockcode']
            if stockId[0] == '6':
                stockIdList.append('SH' + stockId)
            elif stockId[0] == '0' or stockId[0] == '3':
                stockIdList.append('SZ' + stockId)
        if 'stockIdList' not in _data:
            _data['stockIdList'] = stockIdList
        else:
            _data['stockIdList'].extend(stockIdList)
        self.gn.save(_data)

    # 保存股票股数信息，例子 url = https://xueqiu.com/v4/stock/quote.json?code=SZ000687
    def save_stock_basic_info(self, url, data):
        if self.col.find_one() is None:
            self.col.ensure_index('stockId', unique=True, backgroud=True)

        # get stock id
        stockId = url[-8:]
        _data = self.col.find_one({'stockId': stockId})
        if not _data:
            _data = {'stockId': stockId}

        _data['name'] = data[stockId]['name']
        _data['totalShares'] = float(data[stockId]['totalShares'])
        _data['float_shares'] = float(data[stockId]['float_shares'])
        _data['flag'] = data[stockId]['flag']  # "2"：停牌  “1”：正常  "0"：退市  “3”: 新股
        _data['datetime'] = datetime.date.today().ctime()

        # 每股收益 每股净资产 每股股息 市盈率 市净率 市销率
        for key in ['current','volumeAverage','eps','net_assets', 'dividend','pe_ttm','pe_lyr','pb','psr']:
            if data[stockId][key]: _data[key] = float(data[stockId][key])
            else: _data[key] = 0.0
        self.col.save(_data)

    def process_item(self, item, spider):
        #print item
        url, data = item['src'], item['content']
        if url.startswith("http://q.10jqka.com.cn/interface/stock/detail/zdf/desc/"): # 概念信息
            self.save_gn_info(url, data)

        elif url.startswith("https://xueqiu.com/v4/stock/quote.json?code="): # 股票基础信息
            self.save_stock_basic_info(url, data)

        elif url.startswith("http://api.finance.ifeng.com/aminhis/?code="): # 股票1分钟级数据
            self.save_stock_minute_info(url, data)

        else: # 股票价格信息
            self.save_stock_price_info(url, data)

        return item


#r = ScrapyspiderPipeline('mongodb://127.0.0.1:27017/')
#r.save()

