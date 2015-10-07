# -*- coding: utf-8 -*-
import redis
import time
import datetime
import re
import sys
import numpy
import math
import matplotlib.dates as dates
from matplotlib.dates import DateFormatter, WeekdayLocator, HourLocator, DayLocator, MONDAY
import matplotlib.pyplot as pyplot
import matplotlib.finance as finance
from pymongo import MongoClient

from sklearn.metrics import mean_squared_error
from sklearn.datasets import make_friedman1
from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier

import codecs
import random
import copy
import json



MONGODB_URI = 'mongodb://127.0.0.1:27017/'



class Stock(object):

    def init(self, redis_server):
        self.mongo_client = MongoClient(MONGODB_URI)
        self.db = self.mongo_client['stock']
        self.col = self.db['table'] # 股票信息
        self.hy = self.db['hy'] # 股票行业信息

        self.init_scrapy_redis(redis_server)

        self.cache = {} # 存储部分股票数据
        self.line = 10 # 股票特征重要度 每列显示的个数


    def init_scrapy_redis(self, redis_server):
        self.redis_key_prefix = 'stockSpider:'

        host, port = redis_server.split(':')
        self.redis_client = redis.StrictRedis(host=host, port=int(port))
        print self.redis_client


    def push_redis_url(self, url):
        key = self.redis_key_prefix + 'start_urls'
        self.redis_client.lpush(key, url)


    # "Mon Aug 17 09:30:00 +0800 2015"
    def get_time(self, Time='09:30:00'):
        Weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'] # 0 1 2 3 4
        Month = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'] # 0 ... 11

        today, delta = datetime.date.today(), datetime.timedelta(1)
        # 周末变周五
        while today.weekday() > 4:
            today = today - delta
        day, weekday, month, year = today.day, today.weekday(), today.month, today.year
        if day < 10: day = '0' + str(day)

        return Weekday[weekday] + ' ' + Month[month-1] + ' ' + str(day) + ' ' + Time + ' +0800 ' + str(year)

    def get_datetime(self, Time='Mon Aug 17 09:30:00 +0800 2015'):
        Weekday = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        year, month, day = int(Time[-4:]), Time[4:7], int(Time[8:10])
        for i in range(len(Weekday)):
            if month == Weekday[i]:
                month = i + 1
                break

        return datetime.date(year, month, day)

    def get_stockId_all(self):
        stockIdList = self.col.find({}, {'stockId':1})
        stockIdList = [Info['stockId'] for Info in stockIdList \
                       if Info['stockId'] not in ['SH000001', 'SZ399001', 'SZ399005', 'SZ399006']]

        return stockIdList



    # 抓取行业的股指股票信息
    def crawl_hy_url_list(self):
        page = '<a href="http://q.10jqka.com.cn/stock/thshy/bsjd/">白色家电</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/bdtjyj/">半导体及元件</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/bzys/">包装印刷</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/bxjqt/">保险及其他</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/cjfw/">采掘服务</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/cm/">传媒</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/dl/">电力</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/dqsb/">电气设备</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/dzzz/">电子制造</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/fdckf/">房地产开发</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/fzzz/">纺织制造</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/fqcjy/">非汽车交运</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/fzjf/">服装家纺</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/gt/">钢铁</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/gkhy/">港口航运</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/gj/">公交</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/gltlys/">公路铁路运输</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/gxgdz/">光学光电子</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/gfjg/">国防军工</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/hghccl/">化工合成材料</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/hgxcl/">化工新材料</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/hxzp/">化学制品</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/hxzy/">化学制药</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/hbgc/">环保工程</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/jchy/">机场航运</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/jchx/">基础化学</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/jsjsb/">计算机设备</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/jsjyy/">计算机应用</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/jyqg/">家用轻工</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/jzcl/">建筑材料</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/jzzs/">建筑装饰</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/jysbfw/">交运设备服务</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/jdjly/">景点及旅游</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/jdjcy/">酒店及餐饮</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/ls/">零售</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/my/">贸易</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/mtkc/">煤炭开采</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/ncpjg/">农产品加工</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/nyfw/">农业服务</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/qtdz/">其他电子</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/qclbj/">汽车零部件</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/qczc/">汽车整车</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/rqsw/">燃气水务</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/swzp/">生物制品</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/sykykc/">石油矿业开采</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/spjgzz/">食品加工制造</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/stqc/">视听器材</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/txfw/">通信服务</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/txsb/">通信设备</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/tysb/">通用设备</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/wl/">物流</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/xcl/">新材料</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/yzy/">养殖业</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/ylqxfw/">医疗器械服务</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/yysy/">医药商业</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/yqyb/">仪器仪表</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/yx/">银行</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/ylzz/">饮料制造</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/ysyljg/">有色冶炼加工</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/yqkf/">园区开发</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/zz/">造纸</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/zq/">证券</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/zy/">中药</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/zzyyly/">种植业与林业</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/zysb/">专用设备</a>\
                <a href="http://q.10jqka.com.cn/stock/thshy/zh/">综合</a>\
        '
        HY = re.findall("thshy/[a-z]*/", page)

        for hy in HY:
            hy = hy[6:-1]
            _data = self.hy.find_one({'name':hy})
            #if not _data: continue

            url = "http://q.10jqka.com.cn/interface/stock/detail/zdf/desc/1/1/" + hy
            self.push_redis_url(url)
            url = "http://q.10jqka.com.cn/interface/stock/detail/zdf/desc/2/1/" + hy
            self.push_redis_url(url)


    # http://stockpage.10jqka.com.cn/spService/000687/Funds/realFunds 行业资金流向
    # http://stockpage.10jqka.com.cn/spService/000687/Header/realHeader 股票行业信息
    def crawl_stock_hy_info(self):
        stockIdList = self.col.find({}, {'stockId':1, 'hy':1, 'hyname':1})
        for stockInfo in stockIdList:
            if 'hy' in stockInfo: continue
            stockId = stockInfo['stockId']

            url = 'http://stockpage.10jqka.com.cn/spService/' + stockId[2:] + '/Header/realHeader'
            self.push_redis_url(url)


    # http://xueqiu.com/stock/pankou.json?symbol=SZ000681
    # http://stockpage.10jqka.com.cn/spService/300025/Header/realHeader
    def crawl_stock_pankou_info(self):
        stockIdList = self.col.find({}, {'stockId':1, 'pankou':1, 'flag':1})
        for stockInfo in stockIdList:
            if stockInfo.get('flag') != '1': continue
            if 'pankou' in stockInfo and stockInfo['pankou']['datetime'] == datetime.date.today().ctime():
                continue
            stockId = stockInfo['stockId']

            url = 'http://xueqiu.com/stock/pankou.json?symbol=' + stockId
            self.push_redis_url(url)
        self.push_redis_url('http://xueqiu.com')

    def summary_stock_pankou_info(self, default_x=5):
        stockIdList = self.col.find({}, {'stockId':1, 'pankou':1, 'flag':1})
        ratio = []
        for stockInfo in stockIdList:
            if stockInfo.get('flag') != '1' or not stockInfo.get('pankou'): continue
            ratio.append(stockInfo['pankou']['ratio'])

        bin = numpy.arange(-100, 101, default_x)
        pyplot.hist(ratio, bin)
        pyplot.show()


    # http://xueqiu.com/v4/stock/quote.json?code=SZ000681
    def crawl_stock_basic_info(self):
        stockIdList = self.col.find({}, {'stockId':1, 'datetime':1})
        for stockInfo in stockIdList:
            if 'datetime' in stockInfo and stockInfo['datetime'] == datetime.date.today().ctime():
                continue
            stockId = stockInfo['stockId']

            url = 'http://xueqiu.com/v4/stock/quote.json?code=' + stockId
            self.push_redis_url(url)
        self.push_redis_url('http://xueqiu.com')

    # K分钟资金流入流出委比
    def summary_money_info(self, K=1, default_x=5, stockIdList=None):
        start_time = time.time()
        if not stockIdList:
            stockIdList = self.get_stockId_all()

        ratio, sum = [], 0
        for stockId in stockIdList:
            Info = self.col.find_one({'stockId': stockId}, {'minute':1, 'flag':1, 'current':1})
            if Info.get('flag') != '1' or not Info.get('minute') or Info.get('current')==0: continue
            date = max([key for key in Info['minute']])
            price = json.loads( Info['minute'][date] )
            n = len(price)
            if n < 50: continue

            current, Out, In = None, 0.0, 0.0
            for i in range(0,n,K):
                volume, money = 0.0, 0.0
                for j in range(i, min(n, i+K)):
                    volume += price[j][-2]
                    money += price[j][-2] * price[j][-4]
                if volume == 0.0: continue

                avg_price = money/volume
                if current and current < avg_price: In += volume * (avg_price-current)
                elif current and current > avg_price: Out += volume * (current-avg_price)
                current = avg_price
            if Out+In == 0:
                sum += 1
                continue
            ratio.append(100*(In-Out)/(In+Out))
        print time.time()-start_time
        print 'stock number: ', len(ratio), 'bad case: ', sum
        bin = numpy.arange(-100, 101, default_x)
        pyplot.hist(ratio, bin)
        pyplot.show()

    # 1分钟资金交易价格，在均价上：在均价下
    def summary_stock_price_info(self, default_x=5, stockIdList=None):
        start_time = time.time()
        if not stockIdList:
            stockIdList = self.get_stockId_all()

        ratio, sum = [], 0
        for stockId in stockIdList:
            Info = self.col.find_one({'stockId': stockId}, {'minute':1, 'flag':1, 'current':1})
            if Info.get('flag') != '1' or not Info.get('minute') or Info.get('current')==0: continue
            date = max([key for key in Info['minute']])
            price = json.loads( Info['minute'][date] )
            n = len(price)
            if n < 50: continue

            High, Low = 0.0, 0.0
            for i in range(n):
                delta = price[i][-4] - price[i][-1]
                if delta > 0.0:
                    High += 100.0 * price[i][-2] * delta
                elif delta < 0.0:
                    Low -= 100.0 * price[i][-2] * delta
            if High + Low == 0:
                sum += 1
                continue
            ratio.append(100*(High-Low)/(High+Low))
        print time.time()-start_time
        print 'stock number: ', len(ratio), 'bad case: ', sum
        bin = numpy.arange(-100, 101, default_x)
        pyplot.hist(ratio, bin)
        pyplot.show()


    # http://finance.ifeng.com/app/hq/stock/sz300025/
    # http://api.finance.ifeng.com/aminhis/?code=sz300025&type=five
    # http://api.finance.ifeng.com/aminhis/?code=sz300025&type=early
    # http://api.finance.ifeng.com/akdaily/?code=sz000016&type=fq
    def crawl_stock_price_info(self, flag={'0day': '15:00:00','1day': True}):
        stockid = [i for i in range(1,101)]
        stockid.extend([i for i in range(150, 167)])
        stockid.extend([301, 333, 338, 1696, 1896])
        stockid.extend([i for i in range(400, 1000)])

        stockid.extend([i for i in range(2000,2777)])
        stockid.extend([i for i in range(300000,300489)])
        stockid.extend([i for i in range(600000,602000)])
        stockid.extend([i for i in range(603000,604000)])
        stockid.extend(['SH000001', 'SZ399001', 'SZ399005', 'SZ399006']) # 沪 深 中小板 创业板

        for id in stockid:
            isInt = isinstance(id, int)
            if isInt:
                if id < 600000:
                    id = 'SZ' + '0'*(6-len(str(id))) + str(id)
                else:
                    id = 'SH' + str(id)

            _data = self.col.find_one({'stockId': id})
            if isInt and not _data: continue
            if not _data: _data = {}

            end = int(time.time()*1000)
            begin = end - 100*24*3600*1000
            if not isInt: begin -= 20*24*3600*1000  # 板块数据 多抓些

            if 'flag' in _data and _data.get('flag') != "1": continue # 停牌

            #if not _data.get('0day') or _data['0day'][-1][-1]['time'] != self.get_time(flag['0day']):
            #    url = 'http://xueqiu.com/stock/forchart/stocklist.json?symbol=' + id + '&period=1d&one_min=1'
            #    self.push_redis_url(url)

            #if _data.get('minute_early_datetime') != datetime.date.today().ctime():
            #if 'minute_early_datetime' not in _data:
            #    url = 'http://api.finance.ifeng.com/aminhis/?code=' + id.lower() + '&type=early'
            #    self.push_redis_url(url)
            if _data.get('minute_five_datetime') != datetime.date.today().ctime():
                url = 'http://api.finance.ifeng.com/aminhis/?code=' + id.lower() + '&type=five'
                self.push_redis_url(url)

            if flag.get('1day') and (not _data.get('1day') or _data['1day'][-1]['time'] != self.get_time('00:00:00')):
                url = 'http://xueqiu.com/stock/forchartk/stocklist.json?symbol=' + id + '&period=1day&type=before&begin=' + str(begin) + '&end=' + str(end)
                self.push_redis_url(url)

        #self.push_redis_url('http://xueqiu.com/stock/forchart/stocklist.json?symbol=SZ000681\
        # &period=1d&one_min=1')
        #self.push_redis_url('http://xueqiu.com/stock/forchartk/stocklist.json?symbol=SZ000681\
        # &period=1day&type=before&begin=1407602252104&end=1439138252104')
	
        self.push_redis_url('http://xueqiu.com')


    # 获取股票列表的k线图数据
    def get_forchartk(self, stockIdList, type='totalShares'):
        stockInfo, timeList, valid_stockIdList = {}, [], []
        for stockId in stockIdList:
            result = self.col.find_one({'stockId':stockId}, {'totalShares':1, 'float_shares':1, '1day':1})
            if not result: continue
            valid_stockIdList.append(stockId)
            info = {'totalShares':result['totalShares'], 'float_shares':1.0} #result['float_shares']}
            for priceInfo in result['1day']:
                t = self.get_datetime(priceInfo['time'])
                timeList.append(t)
                info[t] = {key: priceInfo[key] for key in ['open','close','high','low']}
                for key in ['open','close','high','low']:
                    if 'price_' + key not in info:
                        info['price_' + key] = priceInfo[key]
            stockInfo[stockId] = info
        timeList = sorted(set(timeList))

        total_k_value, value_basic = [], None
        for t in timeList:
            total_value = {'open':0.0, 'close':0.0, 'high':0.0, 'low':0.0}
            cur_valid_stock_num = 0
            for stockId in valid_stockIdList:
                if t in stockInfo[stockId]:
                    cur_valid_stock_num += 1
                    for key in ['open','close','high','low']:
                        stockInfo[stockId]['price_' + key] = stockInfo[stockId][t][key]
                for key in ['open','close','high','low']:
                    total_value[key] += stockInfo[stockId]['price_'+key]* float(stockInfo[stockId][type])
            if cur_valid_stock_num*3 < len(valid_stockIdList): continue # 股票量太少

            #basic = {'totalShares':4909.0, 'float_shares': 4000.0}
            if value_basic is None: value_basic = total_value['open']/4909.0
            tmp = [dates.date2num(t)]
            tmp.extend([total_value[key]/value_basic for key in ['open','close','high','low']])
            total_k_value.append(tmp)

        return total_k_value

    # 显示多个股票列表的k线图（叠加）
    def draw_forchartk(self, stockIdList):
        fig, ax = pyplot.subplots(figsize=(10,5))
        pyplot.xlabel("Date")
        pyplot.ylabel("Number")

        mondays = WeekdayLocator(MONDAY)        # major ticks on the mondays
        alldays    = DayLocator()              # minor ticks on the days
        weekFormatter = DateFormatter('%b %d')  # Eg, Jan 12
        dayFormatter = DateFormatter('%d')      # Eg, 12

        ax.xaxis.set_major_locator(mondays)
        ax.xaxis.set_minor_locator(alldays)
        ax.xaxis.set_major_formatter(weekFormatter)
        #ax.xaxis.set_minor_formatter(dayFormatter)

        for stockId in stockIdList:
            if not isinstance(stockId, list): stockId = [stockId]
            value = self.get_forchartk(stockId)
            finance.candlestick(ax, value, width=0.6, colorup='r', colordown='g', alpha=1.0)

            #value = self.get_forchartk(stockId, type='float_shares')
            #finance.candlestick(ax, value, width=0.5, colorup='r', colordown='g')

        ax.xaxis_date()
        #ax.autoscale_view()

        pyplot.legend()
        pyplot.show()

    # data = [[volume, price], [volume, price]]
    def get_decay_feature(self, data, decay=0):
        Decay = {0:1.0, 1:0.5, 2:math.pow(0.5,1/2.0), 4:math.pow(0.5,1/4.0)}

        weight, value, d = 0.0, 0.0, Decay[decay]
        for w, v in data[::-1]:
            weight += w*d
            value += w*d*v
            d *= Decay[decay]

        return value/weight

    def get_decay_feature_percent(self, close, priceInfo, decay=0.5):
        volume = sum([priceInfo[p] for p in priceInfo])

        price = sorted(priceInfo.iteritems(),key=lambda x:x[0]) # 按key排序，结果是列表 [(key,value), (key,value)]
        x, p, N, v = [], -1, len(price), 0.0
        for k in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
            while p < N-1 and v < k*volume:
                p += 1
                v += price[p][1]
            x.append(100.0*price[p][0]/close-100.0)
        #print close, x
        if len(x)!=9: print price, x
        return x

    def get_turnrate_info(self, turnrate, threshold=0.8):
        s = sorted(turnrate)
        Min, Max, N = s[0], s[-1], len(turnrate)
        for i in range(N):
            if N-i >= N*threshold: Min = s[i]
            if i+1 < N*threshold: Max = s[i]
        return Min, Max

    def get_flag_feature(self, stockId):
        #['SH000001', 'SZ399001', 'SZ399005', 'SZ399006'] # 沪 深 中小板 创业板
        if stockId.startswith('SH6'):
            return 0.0
        elif stockId.startswith('SZ000') or stockId.startswith('SZ001'):
            return 1.0
        elif stockId.startswith('SZ002'):
            return 5.0
        elif stockId.startswith('SZ300'):
            return 6.0
        else:
            print 'error: ', stockId

    # 获取板块数据两天之间的差值   Day: "Thu Sep 17 00:00:00 +0800 2015"
    def get_delta_feature(self, stockId, Yesterday, Today):
        if stockId not in self.cache:
            Info = self.col.find_one({'stockId': stockId})
            self.cache[stockId] = {}
            for price in Info['1day']:
                self.cache[stockId][price['time']] = price['close']
        if Yesterday not in self.cache[stockId] or Today not in self.cache[stockId]:
            print 'error: ', Yesterday, Today, stockId
            return 0.0
        y_price, t_price = self.cache[stockId][Yesterday], self.cache[stockId][Today]

        return 100.0*t_price/y_price-100.0

    def get_target(self, value):
        return round(value/5.0,2)
        if value >= 1.0: return 1.0
        elif value <= 1.0: return -1.0
        else: return 0.0

    def generate_training_data_old(self, default_day=10, test_day=[4,0,2]):
        start_time = time.time()
        stockIdList = self.get_stockId_all()
        print 'time: ', time.time()-start_time

        X, Y, X_latest, IdList = [], [], [], []
        X_test, Y_test = [[] for i in range(test_day[0])], [[] for i in range(test_day[0])]
        for stockId in stockIdList:
            Info = self.col.find_one({'stockId':stockId}, {'0day':0, 'pankou':0, 'minute':0})
            if Info.get('flag')!="1" or Info.get('current')==0: continue # 停牌
            if 'name' in Info and Info['name'].find('ST') >= 0: continue # ST股票
            price, name = Info['1day'], Info['name']

            N = len(price)
            volume = [1.0*p['volume'] for p in price]
            turnrate = [p['turnrate'] for p in price]
            if N < default_day or sum(volume) == 0 or sum(turnrate) == 0: continue

            avg_volume, avg_turnrate = sum(volume)/N/1e8, sum(turnrate)/N
            min_turnrate, max_turnrate = self.get_turnrate_info(turnrate)
            Total, Float, Avg = Info['totalShares']/1e8, Info['float_shares']/1e8, Info['volumeAverage']/1e8
            for i in range(default_day, N): # 第一个数据只使用close价格
                x, decay_x = [], []
                for j in range(i-default_day+1, i+1):
                    close = price[j-1]['close']
                    for key in ['open', 'close', 'high', 'low']:
                        x.append( 100.0*price[j][key]/close-100.0 )
                    for key in ['open', 'high', 'low']:
                        x.append( 100.0*(price[j][key]-price[j]['close'])/close )
                    for key in ['ma5', 'ma10', 'ma20', 'ma30']:
                        x.append( 100.0*price[j][key]/price[j]['close']-100.0 )

                    x.append( price[j]['turnrate']/avg_turnrate*10.0 ) # 归一化交易量
                    x.append( (price[j]['turnrate']-min_turnrate)/(max_turnrate-min_turnrate)*10.0 )
                    #for key in ['percent', 'dif', 'dea', 'macd']:
                    for key in ['dif', 'dea', 'macd']:
                        x.append(price[j][key])


                    avg_price = price[j]['close']
                    decay_x.append([max(price[j]['turnrate'],0.0001), avg_price])

                    x.append(100.0*self.get_decay_feature(decay_x[-2:], decay=0)/price[j]['close']-100.0)
                    x.append(100.0*self.get_decay_feature(decay_x[-3:], decay=0)/price[j]['close']-100.0)
                    x.append(100.0*self.get_decay_feature(decay_x[-4:], decay=0)/price[j]['close']-100.0)
                    x.append(100.0*self.get_decay_feature(decay_x[-5:], decay=0)/price[j]['close']-100.0)
                self.line = len(x)/default_day

                close = price[i]['close']
                for decay in [0, 1, 2, 4]:
                    x.append(100.0*self.get_decay_feature(decay_x, decay=decay)/close-100.0)
                x = [round(value,2) for value in x] # 统一数字

                x.extend([Total, Float, Avg, Total*close, Float*close, Avg*close, avg_volume*close])
                x.extend([Info[key]/close for key in ['eps','net_assets', 'dividend']])
                x.extend([Info[key]*close/Info['current'] for key in ['pe_ttm','pe_lyr','pb','psr']])
                x.append(self.get_flag_feature(stockId))
                #for id in ['SH000001', 'SZ399001', 'SZ399005', 'SZ399006']: # 沪 深 中小板 创业板
                #    x.append(self.get_delta_feature(id, price_list[i-1]['time'], price_list[i]['time']))

                if i < N-test_day[0]:
                    X.append(x)
                    Y.append(self.get_target(price[i+1]['percent']))
                elif i == N-1:
                    X_latest.append(x)
                    IdList.append([stockId, name])
                elif N-test_day[0]+test_day[1] <= i and i <= N-test_day[0]+test_day[2]:
                    index = i-N+test_day[0]
                    X_test[index].append(x)
                    Y_test[index].append(self.get_target(price[i+1]['percent']))
        print len(Y), sum(Y)
        print 'time: ', time.time()-start_time
        return X, Y, X_test, Y_test, X_latest, IdList


    def generate_minute_feature(self, minute, K=4):
        x, priceInfo = [], {}

        N = len(minute)
        total_volume = sum([minute[i][-2] for i in range(N)])
        total_out_volume, total_in_volume, total_out, total_in = 0.0, 0.0, 0.0, 0.0

        cur_price, percent, volume, Out_volume, In_volume, Out, In = None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        L, close = N/K, minute[-1][-4]/(1.0+0.01*minute[-1][-3])
        for i in range(N):
            price = minute[i][-4]
            percent = minute[i][-3]
            volume += minute[i][-2]

            if price in priceInfo: priceInfo[price] += volume
            else: priceInfo[price] = volume

            if cur_price and cur_price > price:
                Out_volume += minute[i][-2]
                Out += minute[i][-2] * (cur_price-price)
            elif cur_price and cur_price < price:
                In_volume += minute[i][-2]
                In += minute[i][-2] * (price-cur_price)
            cur_price = price

            if (i!=0 and i%L==0 and i<K*L) or i==N-1:
                x.extend([percent, 100.0*minute[i][-1]/close-100.0])
                #x.extend([100*volume/total_volume, 100*Out_volume/total_volume, 100*In_volume/total_volume])
                x.extend([100*volume/total_volume, 100*In_volume/total_volume])
                if In+Out: x.append( 100*(In-Out)/(In+Out) )
                elif percent > 9.5: x.append( 100.0 )
                elif percent < -9.5: x.append( -100.0 )
                else: x.append( 0.0 )

                total_out_volume += Out_volume
                total_in_volume += In_volume
                total_out += Out
                total_in += In
                volume, Out_volume, In_volume, Out, In = 0.0, 0.0, 0.0, 0.0, 0.0
        #x.extend([100*total_out_volume/total_volume, 100*total_in_volume/total_volume])
        x.extend([100*total_in_volume/total_volume])
        if total_in+total_out: x.append( 100*(total_in-total_out)/(total_in+total_out) )
        elif percent > 9.5: x.append( 100.0 )
        elif percent < -9.5: x.append( -100.0 )
        else: x.append( 0.0 )

        return x, priceInfo


    def generate_training_data(self, default_day=10, test_day=[4,0,2]):
        start_time = time.time()
        stockIdList = self.get_stockId_all()
        #stockIdList = ['SZ300025']
        print 'time: ', time.time()-start_time

        X, Y, X_latest, IdList = [], [], [], []
        X_test, Y_test = [[] for i in range(test_day[0])], [[] for i in range(test_day[0])]
        for stockId in stockIdList:
            Info = self.col.find_one({'stockId':stockId})
            if Info.get('flag')!="1" or Info.get('current')==0: continue # stop stock
            if 'name' in Info and Info['name'].find('ST') >= 0: continue # ST stock

            price, name = Info['1day'], Info['name']
            minute = {date:json.loads(Info['minute'][date]) for date in Info['minute']}

            N = len(price)
            volume, turnrate = [1.0*p['volume'] for p in price], [p['turnrate'] for p in price]
            if N < default_day or sum(volume) == 0 or sum(turnrate) == 0: continue

            avg_volume, avg_turnrate = sum(volume)/N/1e8, sum(turnrate)/N
            min_turnrate, max_turnrate = self.get_turnrate_info(turnrate)
            Total, Float, Avg = Info['totalShares']/1e8, Info['float_shares']/1e8, Info['volumeAverage']/1e8

            minute_feature, valid = {}, 0
            minute_price = {decay:{} for decay in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]}
            for i in range(1, N): # 第一个数据只使用close价格
                date = str( self.get_datetime(price[i]['time']) )
                if minute.get(date):
                    valid += 1
                    minute_feature[date], priceInfo = self.generate_minute_feature(minute[date])
                    for decay in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
                        for p in minute_price[decay]:
                            minute_price[decay][p] *= decay
                        for p in priceInfo:
                            if p in minute_price[decay]: minute_price[decay][p] += priceInfo[p]
                            else: minute_price[decay][p] = priceInfo[p]
                elif valid:
                    valid = 0
                    #print stockId, price[i]['time'], date, [key for key in minute]
                if valid < default_day: continue

                x, decay_x = [], []
                for j in range(i-default_day+1, i+1):
                    close = price[j-1]['close']
                    #for key in ['open', 'close', 'high', 'low']:
                    for key in ['open', 'high', 'low']:
                        x.append( 100.0*price[j][key]/close-100.0 )
                    #for key in ['open', 'high', 'low']:
                    #    x.append( 100.0*(price[j][key]-price[j]['close'])/close )
                    for key in ['ma5', 'ma10', 'ma20', 'ma30']:
                        x.append( 100.0*price[j][key]/price[j]['close']-100.0 )

                    x.append( price[j]['turnrate']/avg_turnrate*10.0 ) # 归一化交易量
                    x.append( (price[j]['turnrate']-min_turnrate)/(max_turnrate-min_turnrate)*10.0 )
                    #for key in ['dif', 'dea', 'macd']:
                    #    x.append(price[j][key])


                    date = str( self.get_datetime(price[j]['time']) )
                    avg_price = minute[date][-1][-1]
                    #avg_price = price[j]['close']
                    decay_x.append([max(price[j]['turnrate'],0.0001), avg_price])

                    #x.append(100.0*avg_price/close-100.0)
                    x.append(100.0*self.get_decay_feature(decay_x[-2:], decay=0)/price[j]['close']-100.0)
                    x.append(100.0*self.get_decay_feature(decay_x[-3:], decay=0)/price[j]['close']-100.0)
                    x.append(100.0*self.get_decay_feature(decay_x[-4:], decay=0)/price[j]['close']-100.0)
                    x.append(100.0*self.get_decay_feature(decay_x[-5:], decay=0)/price[j]['close']-100.0)
                    x.extend(minute_feature[date])
                self.line = len(x)/default_day

                close = price[i]['close']
                for decay in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
                    x.extend(self.get_decay_feature_percent(close, minute_price[decay]))

                #for decay in [0, 1, 2, 4]:
                #    x.append(100.0*self.get_decay_feature(decay_x, decay=decay)/close-100.0)
                x = [round(value,2) for value in x] # 统一数字

                x.extend([Total, Float, Avg, Total*close, Float*close, Avg*close, avg_volume*close])
                x.extend([Info[key]/close for key in ['eps','net_assets', 'dividend']])
                x.extend([Info[key]*close/Info['current'] for key in ['pe_ttm','pe_lyr','pb','psr']])
                x.append(self.get_flag_feature(stockId))
                #for id in ['SH000001', 'SZ399001', 'SZ399005', 'SZ399006']: # 沪 深 中小板 创业板
                #    x.append(self.get_delta_feature(id, price_list[i-1]['time'], price_list[i]['time']))

                if i < N-test_day[0]:
                    X.append(x)
                    Y.append(self.get_target(price[i+1]['percent']))
                elif i == N-1:
                    X_latest.append(x)
                    IdList.append([stockId, name])
                elif N-test_day[0]+test_day[1] <= i and i <= N-test_day[0]+test_day[2]:
                    index = i-N+test_day[0]
                    X_test[index].append(x)
                    Y_test[index].append(self.get_target(price[i+1]['percent']))
        print len(Y), sum(Y)
        print 'time: ', time.time()-start_time
        return X, Y, X_test, Y_test, X_latest, IdList


    def predict_result(self, model, X, Y=None, stockIdList=None, myList=None, Show=True):
        scoreList, selectList, N = [], [], len(X)
        for i in range(N):
            score = model.predict(X[i])
            score[0] = round(score[0], 3)
            scoreList.append(score[0])
            if stockIdList and myList and stockIdList[i][0] in myList:
                print '$'+stockIdList[i][1]+'('+stockIdList[i][0]+')'+'$', 'score: ', score[0]
            if score[0] >= 0.5 and stockIdList:
                selectList.append([stockIdList[i], score[0]]) #print stockIdList[i]

        for threshold in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]:
            pp, pn, np, nn, pY = 0, 0, 0, 0, []
            for i in range(N):
                if Y and scoreList[i] >= threshold: pY.append(Y[i])
                if Y and Y[i] > 0.0:
                    if scoreList[i] >= threshold: pp += 1
                    else: pn += 1
                else:
                    if scoreList[i] >= threshold: np += 1
                    else: nn += 1
            if Y:
                print threshold, pp, pn, np, nn,
                if pp+np and pp+pn and pp+np:
                    print 'P/R:',round(100.*pp/(pp+np),1),round(100.*pp/(pp+pn),1), 'C:',round(100.*(pp+np)/N,1),
                    print round(100.*(pp+pn)/N,1), 'P:', round(100.*(pp+nn)/N,1), 'pY:', round(sum(pY)/len(pY),3)
                else: print ''
                #print 'mean error: ', mean_squared_error(Y, model.predict(X))
            elif threshold==0.0:
                print np, nn, 'C:', round(1.0*np/(np+nn),4)

        selectList = sorted(selectList, key=lambda x: x[1], reverse=True)
        for i in range(min(len(selectList), 20)):
            print '$'+selectList[i][0][1]+'('+selectList[i][0][0]+')'+'$', selectList[i][1]

        if Show:
            #print 'min score: ', min(scoreList), 'max score: ', max(scoreList)
            bin = numpy.arange(-2, 2, 0.1)
            pyplot.hist(scoreList, bin)
            pyplot.show()


    def training_model(self, X, Y, X_test, Y_test, X_latest, stockIdList):
        start_time = time.time()
        x_train, y_train, x_test, y_test = [], [], [], []
        for i in range(len(X)):
            if True or random.random() < 0.85:
                x_train.append(X[i])
                y_train.append(Y[i])
            else:
                x_test.append(X[i])
                y_test.append(Y[i])
        GBR = GradientBoostingRegressor(n_estimators=100,learning_rate=0.8,min_samples_leaf=100,\
                                          max_leaf_nodes=7,random_state=0,loss='ls')
        #GBR = GradientBoostingClassifier(n_estimators=100,learning_rate=0.5,min_samples_leaf=100,\
        #                                  max_leaf_nodes=5,random_state=0,loss='deviance')
        model = GBR.fit(x_train,y_train)
        print 'time: ', time.time()-start_time

        print 'training result:'
        self.predict_result(model, x_train, y_train)
        print 'training test result: (total:', len(X), ',test:', len(x_test), ')'
        if len(x_test): self.predict_result(model, x_test, y_test)
        print 'test result:'
        for i in range(len(X_test)):
            if len(X_test[i]) == 0: continue
            print len(X_test[i]), len(Y_test[i])
            self.predict_result(model, X_test[i], Y_test[i])

        myList = {'SZ300025', 'SZ000681', 'SZ002637', 'SH600285', 'SZ000687', 'SH600677', 'SH600397', 'SZ000698'\
                  ,'SZ300104', 'SH600886'
        }
        print 'latest result:'
        self.predict_result(model, X_latest, Y=None, stockIdList=stockIdList, myList=myList)

        fi = GBR.feature_importances_
        fi = [round(100*v,2) for v in fi]
        for i in range(len(fi)):
            if i%self.line == 0: print ''
            print '{0:4}'.format(fi[i]),
        print ''

    # train paramater
    def model_para(self, X, Y, X_test, Y_test):
        for n in [100]:
            for rate in [0.6, 0.7, 0.8, 0.9, 1.0]:
                for leaf in [100]:
                    for nodes in [6, 7, 8]:
                        print n, rate, leaf, nodes
                        start_time = time.time()
                        GBR = GradientBoostingRegressor(n_estimators=n,learning_rate=rate,min_samples_leaf=leaf,\
                                          max_leaf_nodes=nodes,random_state=0,loss='ls')
                        model = GBR.fit(X, Y)
                        print 'time', time.time()-start_time

                        print 'training result:'
                        self.predict_result(model, X, Y, Threshold=1, Show=False)
                        print 'test result:'
                        for i in range(len(X_test)):
                            if len(X_test[i]) == 0: continue
                            print len(X_test[i]), len(Y_test[i])
                            self.predict_result(model, X_test[i], Y_test[i], Threshold=1, Show=False)




if __name__ == '__main__':

    stock = Stock()
    #stock.init(sys.argv[1])
    stock.init('127.0.0.1:6379')

    if len(sys.argv) < 2:
        print stock.get_time('00:00:00')
        X, Y = [], []
        p, n = 0, 0
        for i in range(10000):
            flag, start = random.randint(0,2), random.randint(0,100)
            flag = i%4
            if flag == 0:
                X.append([10, start, start+10, i, i+1, i+2, i+3, i+4, i+5, i+6, i+7])
                Y.append(-1)
                n += 1
            else:
                X.append([5, start, start+5, i, i+1, i+2, i+3, i+4, i+5, i+6, i+7])
                Y.append(1)
                p += 1
        GBR = GradientBoostingRegressor(n_estimators=1,learning_rate=1.1,min_samples_leaf=10,\
                          max_leaf_nodes=2,random_state=0,loss='ls')
        GBR.fit(X, Y)
        print n, p
        print GBR.feature_importances_
        x = [10, 10, 20, 0, 1, 2, 3, 4, 5, 6, 7]
        print GBR.predict(x)
        #x = [9, 10, 20, 0, 1, 2, 3, 4, 5, 6, 7]
        #print GBR.predict(x)
        #x = [8, 10, 20, 0, 1, 2, 3, 4, 5, 6, 7]
        #print GBR.predict(x)
        #x = [7, 10, 20, 0, 1, 2, 3, 4, 5, 6, 7]
        #print GBR.predict(x)
        #x = [6, 10, 20, 0, 1, 2, 3, 4, 5, 6, 7]
        #print GBR.predict(x)
        x = [5, 10, 15, 0, 1, 2, 3, 4, 5, 6, 7]
        print GBR.predict(x)
        #stock.generate_training_data_minute(default_day=10, test_day=[4,0,2])

        #stock.push_redis_url('http://www.qq.com')
        pass

    elif sys.argv[1] == 'model':
        X, Y, X_test, Y_test, X_latest, IdList = stock.generate_training_data(default_day=10,test_day=[5,0,3])
        print len(X), len(Y), len(X_test), len(Y_test), len(X_latest), len(IdList)
        print X[-1], Y[-1]
        stock.training_model(X, Y, X_test, Y_test, X_latest, IdList)
        #stock.model_para(X, Y, X_test, Y_test)

    elif sys.argv[1] == 'price':
        stock.crawl_stock_price_info()

    elif sys.argv[1] == 'price_0day':
        stock.crawl_stock_price_info(flag={'0day':'11:30:00'})

    elif sys.argv[1] == 'price_0day_summary':
        stock.summary_stock_price_info()

        stock.summary_money_info(K=1, default_x=5)
        stock.summary_money_info(K=5, default_x=5)

    elif sys.argv[1] == 'basic':
        stock.crawl_stock_basic_info()

    elif sys.argv[1] == 'pankou':
        stock.crawl_stock_pankou_info()

    elif sys.argv[1] == 'pankou_summary':
        stock.summary_stock_pankou_info()

    elif sys.argv[1] == 'hy':
        stock.crawl_stock_hy_info()

    elif sys.argv[1] == 'hy_url':
        stock.crawl_hy_url_list()

    elif sys.argv[1] == 'drawK':
        stockIdList = ['SH'+str(key) for key in range(600000, 604000)]
        stock.draw_forchartk([stockIdList])


