# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import datetime
from pymongo import MongoClient
from scrapySpider.items import stockItem


MONGODB_URI = 'mongodb://127.0.0.1:27017/'


class ScrapyspiderPipeline(object):

    def __init__(self, mongodb_uri):
        self.mongodb_uri = mongodb_uri
        self.mongo_client = MongoClient(mongodb_uri)
        self.db = self.mongo_client['stock']
        self.col = self.db['table']
        self.hy = self.db['hy']

    @classmethod
    def from_settings(cls, settings):
        mongodb_uri = settings.get('MONGODB_URI', MONGODB_URI)
        return cls(mongodb_uri)

    # 保存股票价格信息，例子
    # http://xueqiu.com/stock/forchart/stocklist.json?symbol=SZ000681&period=1d&one_min=1
    # http://xueqiu.com/stock/forchartk/stocklist.json?symbol=SZ000681&\
    #   period=1day&type=before&begin=1407602252104&end=1439138252104
    def save_stock_price_info(self, url, data):
        if self.col.find_one() is None:
            self.col.ensure_index('stockId', unique=True, backgroud=True)

        # get stock id
        index = url.find('symbol=')
        if index >= 0:
            stockId = url[index+7:index+15]
        else:
            print 'error to parse stock id'
            return

        _data = self.col.find_one({'stockId': stockId})
        if not _data:
            _data = {'stockId': stockId}

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
                if len(_data['0day']) > 7:
                    _data['0day'] = _data['0day'][1:]
            else:
                _data['0day'][-1] = data['chartlist']
        else:
            print 'error for this kind of url'
            return
        self.col.save(_data)

    # 保存行业的所有股票信息，例子 url = http://q.10jqka.com.cn/interface/stock/detail/zdf/desc/1/1/zq
    def save_hy_info(self, url, data):
        # get mongo data
        if self.hy.find_one() is None:
            self.hy.ensure_index('name', unique=True, backgroud=True)

        hy = url[url.rfind('/')+1:]
        _data = self.hy.find_one({'name':hy})
        if not _data:
            _data = {'name': hy}

        stockIdList = []
        for stockInfo in data['data']:
            stockId = stockInfo['stockcode']
            if stockId[0] == '6':
                stockIdList.append('SH' + stockId)
            elif stockId[0] == '0' or stockId[0] == '3':
                stockIdList.append('SZ' + stockId)
        _data['stockIdList'] = stockIdList
        self.hy.save(_data)

    # 保存股票的行业信息，例子 url = http://stockpage.10jqka.com.cn/spService/000687/Header/realHeader
    def save_stock_hy_info(self, url, data):
        index = url.find("spService")
        stockId = url[index+10:index+16]
        if stockId[0] == '6':
            stockId = 'SH' + stockId
        elif stockId[0] == '0' or stockId[0] == '3':
            stockId = 'SZ' + stockId

        _data = self.col.find_one({'stockId': stockId})
        if not _data: return
        _data['hy'] = data['fieldname']
        _data['hyname'] = data['fieldjp']
        self.col.save(_data)

    # 保存股票股数信息，例子 url = http://xueqiu.com/v4/stock/quote.json?code=SZ000687
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

        # 每股收益 每股净资产 每股股息 市盈率 市净率 市销率
        for key in ['current','volumeAverage','eps','net_assets', 'dividend','pe_ttm','pe_lyr','pb','psr']:
            if data[stockId][key]: _data[key] = float(data[stockId][key])
            else: _data[key] = 0.0
        self.col.save(_data)

    # 保存股票盘口信息，例子 url = http://xueqiu.com/stock/pankou.json?symbol=SZ000687
    def save_stock_pankou_info(self, url, data):
        if self.col.find_one() is None:
            self.col.ensure_index('stockId', unique=True, backgroud=True)

        # get stock id
        stockId = url[-8:]
        _data = self.col.find_one({'stockId': stockId})
        if not _data:
            _data = {'stockId': stockId}

        _data['pankou'] = data
        _data['pankou']['datetime'] = datetime.date.today().ctime()
        self.col.save(_data)


    def process_item(self, item, spider):
        #print item
        url, data = item['src'], item['content']
        if url.startswith("http://q.10jqka.com.cn/interface/stock/detail/zdf/desc/"): # 行业信息
            self.save_hy_info(url, data)

        elif url.startswith("http://stockpage.10jqka.com.cn/spService/"): # 股票行业信息
            self.save_stock_hy_info(url, data)

        elif url.startswith("http://xueqiu.com/v4/stock/quote.json?code="): # 股票基础信息
            self.save_stock_basic_info(url, data)

        elif url.startswith("http://xueqiu.com/stock/pankou.json?symbol="): # 股票盘口信息
            self.save_stock_pankou_info(url, data)

        else: # 股票价格信息
            self.save_stock_price_info(url, data)

        return item


#r = ScrapyspiderPipeline('mongodb://127.0.0.1:27017/')
#r.save()

