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



MONGODB_URI = 'mongodb://127.0.0.1:27017/'



class Stock(object):

    def init(self, redis_server):
        self.mongo_client = MongoClient(MONGODB_URI)
        self.db = self.mongo_client['stock']
        self.col = self.db['table'] # 股票信息
        self.hy = self.db['hy'] # 股票行业信息

        self.init_scrapy_redis(redis_server)

        self.cache = {} # 存储部分股票数据


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


    # 股票逐笔成交信息，例子
    # http://hqdigi2.eastmoney.com/EM_Quote2010NumericApplication/CompatiblePage.aspx?Type=OB&stk=6006631&page=5
    # http://hqdigi2.eastmoney.com/EM_Quote2010NumericApplication/CompatiblePage.aspx?Type=OB&stk=0006812&page=2
    # end前5分钟  http://quotes.money.163.com/service/zhubi_ajax.html?symbol=002637&end=13%3A37%3A00
    def crawl_stock_trade_info(self):
        pass


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
    def summary_stock_price_info(self, K=1, default_x=5, stockIdList=None):
        start_time = time.time()
        if not stockIdList:
            stockIdList = self.get_stockId_all()

        ratio, sum = [], 0
        for stockId in stockIdList:
            Info = self.col.find_one({'stockId': stockId}, {'0day':1, 'flag':1, 'current':1})
            if Info.get('flag') != '1' or not Info.get('0day') or Info.get('current')==0: continue
            price_list = Info['0day'][-1]
            n = len(price_list)
            if n < 50: continue

            current, Out, In = None, 0.0, 0.0
            for i in range(0,n,K):
                volume, money = 0.0, 0.0
                for j in range(i, min(n, i+K)):
                    volume += price_list[j]['volume']
                    money += price_list[j]['volume'] * price_list[j]['current']
                if volume == 0.0: continue

                price = money/volume
                if current and current < price: In += volume * (price-current)
                elif current and current > price: Out += volume * (current-price)
                current = price
            if Out+In == 0:
                sum += 1
                continue
            ratio.append(100*(In-Out)/(In+Out))
        print time.time()-start_time
        print 'stock number: ', len(ratio), 'bad case: ', sum
        bin = numpy.arange(-100, 101, default_x)
        pyplot.hist(ratio, bin)
        pyplot.show()


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

        #stockid = [681, 5]
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

            #http://d.10jqka.com.cn/v2/line/hs_300025/01/last.js
            if not _data.get('0day') or _data['0day'][-1][-1]['time'] != self.get_time(flag['0day']):
                url = 'http://xueqiu.com/stock/forchart/stocklist.json?symbol=' + id + '&period=1d&one_min=1'
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
        if value >= 1.0: return 1.0
        elif value <= 1.0: return -1.0
        else: return 0.0

    # 取stockIdList中股票数据
    def generate_training_data(self, default_day=10, test_day=[4,0,2]):
        start_time = time.time()
        stockIdList = self.get_stockId_all()
        print 'time: ', time.time()-start_time

        X, Y, X_test, Y_test, X_latest, IdList = [], [], [], [], [], []
        X_test, Y_test = [[] for i in range(test_day[0])], [[] for i in range(test_day[0])]
        for stockId in stockIdList:
            Info = self.col.find_one({'stockId':stockId}, {'0day':0, 'pankou':0})
            if Info.get('flag')!="1" or Info.get('current')==0: continue # 停牌
            if 'name' in Info and Info['name'].find('ST') >= 0: continue # ST股票
            price_list, name = Info['1day'], Info['name']

            list_len = len(price_list)
            volume = [1.0*price['volume'] for price in price_list]
            turnrate = [price['turnrate'] for price in price_list]
            if list_len < default_day or sum(volume) == 0 or sum(turnrate) == 0: continue

            avg_volume, avg_turnrate = sum(volume)/list_len/1e8, sum(turnrate)/list_len
            min_turnrate, max_turnrate = self.get_turnrate_info(turnrate)
            Total, Float, Avg = Info['totalShares']/1e8, Info['float_shares']/1e8, Info['volumeAverage']/1e8
            for i in range(default_day, list_len): # 第一个数据只使用close价格
                x, decay_x = [], []
                for j in range(i-default_day+1, i+1):
                    #avg_price = sum([price_list[j][key] for key in ['open', 'close', 'high', 'low']]) / 4.0
                    avg_price = price_list[j]['close']
                    decay_x.append([max(price_list[j]['turnrate'],0.0001), avg_price])

                    close = price_list[j-1]['close']
                    for key in ['open', 'close', 'high', 'low']:
                        x.append( 100.0*price_list[j][key]/close-100.0 )
                    for key in ['open', 'high', 'low']:
                        x.append( 100.0*(price_list[j][key]-price_list[j]['close'])/close )
                    for key in ['ma5', 'ma10', 'ma20', 'ma30']:
                        x.append( 100.0*price_list[j][key]/price_list[j]['close']-100.0 )
                    x.append( price_list[j]['turnrate']/avg_turnrate ) # 归一化交易量
                    x.append( (price_list[j]['turnrate']-min_turnrate)/(max_turnrate-min_turnrate)*10.0 )
                    #for key in ['percent', 'dif', 'dea', 'macd']:
                    for key in ['dif', 'dea', 'macd']:
                        x.append(price_list[j][key])
                    x.append(100.0*self.get_decay_feature(decay_x[-3:], decay=0)/price_list[j]['close']-100.0)
                    x.append(100.0*self.get_decay_feature(decay_x[-5:], decay=0)/price_list[j]['close']-100.0)

                    #for id in ['SH000001', 'SZ399001', 'SZ399005', 'SZ399006']: # 沪 深 中小板 创业板
                    #    x.append(self.get_delta_feature(id, price_list[j-1]['time'], price_list[j]['time']))

                close = price_list[i]['close']
                for decay in [0, 1, 2, 4]:
                    x.append(100.0*self.get_decay_feature(decay_x, decay=decay)/close-100.0)
                    #for j in range(len(decay_x)):
                    #    x.append(self.generate_decay_feature(decay_x[j:], decay=decay)/close)
                    #x.extend([0.0, 0.0])
                x.extend([Total, Float, Avg, Total*close, Float*close, Avg*close, avg_volume*close])
                x.extend([Info[key]/close for key in ['eps','net_assets', 'dividend']])
                x.extend([Info[key]*close/Info['current'] for key in ['pe_ttm','pe_lyr','pb','psr']])
                x.append(self.get_flag_feature(stockId))
                #for id in ['SH000001', 'SZ399001', 'SZ399005', 'SZ399006']: # 沪 深 中小板 创业板
                #    x.append(self.get_delta_feature(id, price_list[i-1]['time'], price_list[i]['time']))

                if i < list_len-test_day[0]:
                    X.append(x)
                    Y.append(self.get_target(price_list[i+1]['percent']))
                elif i == list_len-1:
                    X_latest.append(x)
                    IdList.append([stockId, name])
                elif list_len-test_day[0]+test_day[1] <= i and i <= list_len-test_day[0]+test_day[2]:
                    index = i-list_len+test_day[0]
                    X_test[index].append(x)
                    Y_test[index].append(self.get_target(price_list[i+1]['percent']))
        print len(Y), sum(Y)
        print 'time: ', time.time()-start_time
        return X, Y, X_test, Y_test, X_latest, IdList

    def generate_feature(self, close, price_list, avg_volume, K=5):
        x = []
        avg_volume = avg_volume/240.0*K
        for i in range(0, min(240,len(price_list)), K):
            volume, money, KK = 0.0, 0.0, K
            if i==240-K: KK = len(price_list)-i
            for j in range(KK):
                volume += price_list[i+j]['volume']
                #print j, price_list[i+j]
                money += price_list[i+j]['volume']*price_list[i+j]['avg_price']
            if volume > 0:
                x.extend([volume/avg_volume, 100*money/volume/close-100.0])
            else:
                x.extend([0.0, 0.0])
        return x

    def generate_training_data_0day(self, default_day=2, test_day=[2,0,0]):
        start_time = time.time()
        stockIdList = self.col.find({}, {'stockId':1, 'name':1})
        stockIdList = [[Info['stockId'],Info['name']] for Info in stockIdList]
        print 'time: ', time.time()-start_time

        X, Y, X_test, Y_test, X_latest, IdList = [], [], [], [], [], []
        for stockId, name in stockIdList:
            info = self.col.find_one({'stockId':stockId},{'pankou':0})
            if info.get('flag')!="1" or info.get('current')==0: continue # 停牌
            if 'name' in info and info['name'].find('ST') >= 0: continue # ST股票
            if info['0day'][0][0]['time'] != 'Tue Sep 01 09:30:00 +0800 2015': continue # 老数据
            if info['1day'][-7]['time'] != 'Tue Sep 01 00:00:00 +0800 2015': continue # 老数据
            price_list = info['0day']
            #print stockId, name

            list_len = len(price_list)
            volume = [1.0*price['volume'] for price in info['1day']]
            turnrate = [price['turnrate'] for price in info['1day']]
            if sum(volume) == 0 or sum(turnrate) == 0: continue

            avg_volume, avg_turnrate = sum(volume)/list_len, sum(turnrate)/list_len
            #Total, Float, Avg = info['totalShares']/1e8, info['float_shares']/1e8, info['volumeAverage']/1e8
            for i in range(default_day-1, list_len): # 第一个数据只使用close价格
                #avg_price = sum([price['close'] for price in price_list[i-default_day+1:i+1]])/default_day

                x = []
                for j in range(i-default_day+1, i+1):
                    close = info['1day'][j-list_len-1]['close']
                    x.extend(self.generate_feature(close, info['0day'][j], avg_volume, K=5))
                    x.extend(self.generate_feature(close, info['0day'][j], avg_volume, K=10))
                    x.extend(self.generate_feature(close, info['0day'][j], avg_volume, K=20))
                    x.extend(self.generate_feature(close, info['0day'][j], avg_volume, K=30))
                    x.extend(self.generate_feature(close, info['0day'][j], avg_volume, K=60))

                #close = price_list[i]['close']
                #x.extend([Total, Float, Avg, Total*close, Float*close, Avg*close, avg_volume*close])
                #x.extend([info[key]/close for key in ['eps','net_assets', 'dividend']])
                #x.extend([info[key]*close/info['current'] for key in ['pe_ttm','pe_lyr','pb','psr']])
                if i < list_len-test_day[0]:
                    X.append(x)
                    #Y.append(price_list[i+1]['percent']/10.0)
                    Y.append(price_list[i+1][-1]['current']/price_list[i][-1]['current'] > 1.015 and 1. or -1.)
                    #if price_list[i+1]['percent'] > 6.0: # 重复 提高权重
                    #    X.append(x)
                    #    Y.append(1.0)
                elif i == list_len-1:
                    X_latest.append(x)
                    IdList.append([stockId, name])
                elif list_len-test_day[0]+test_day[1] <= i and i <= list_len-test_day[0]+test_day[2]:
                    X_test.append(x)
                    #Y_test.append(price_list[i+1]['percent']/10.0)
                    Y_test.append(price_list[i+1][-1]['current']/price_list[i][-1]['current']>1.015 and 1. or -1.)
        print len(Y), sum(Y)
        print 'time: ', time.time()-start_time
        return X, Y, X_test, Y_test, X_latest, IdList


    def predict_result(self, model, X, Y=None, stockIdList=None, myList=None):
        scoreList, selectList, N = [], [], len(X)
        for i in range(N):
            score = model.predict(X[i])
            score[0] = round(score[0], 3)
            scoreList.append(score[0])
            if stockIdList and myList and stockIdList[i][0] in myList:
                print '$'+stockIdList[i][1]+'('+stockIdList[i][0]+')'+'$', 'score: ', score[0]
            if score[0] >= 0.5 and stockIdList:
                selectList.append([stockIdList[i], score[0]]) #print stockIdList[i]

        for threshold in range(8):
            threshold /= 10.0

            pp, pn, np, nn = 0, 0, 0, 0
            for i in range(N):

                if Y and Y[i] > 0.0:
                    if scoreList[i] >= threshold: pp += 1
                    else: pn += 1
                else:
                    if scoreList[i] >= threshold: np += 1
                    else: nn += 1
            if Y:
                print threshold, pp, pn, np, nn,
                if pp+np and pp+pn and pp+np:
                    print 'P/R:', round(100.*pp/(pp+np),1), round(100.*pp/(pp+pn),1), 'C:', round(100.*(pp+np)/N,1),
                    print round(100.*(pp+pn)/N,1), 'F:', round(200.*pp/(2.*pp+pn+np),1), 'P:', round(100.*(pp+nn)/N,1)
                else: print ''
                #print 'mean error: ', mean_squared_error(Y, model.predict(X))
            elif threshold==0.0:
                print np, nn, 'C:', round(1.0*np/(np+nn),4)

        selectList = sorted(selectList, key=lambda x: x[1], reverse=True)
        for i in range(min(len(selectList), 20)):
            #print selectList[i][0], selectList[i][1]
            print '$'+selectList[i][0][1]+'('+selectList[i][0][0]+')'+'$', selectList[i][1]

        #print 'min score: ', min(scoreList), 'max score: ', max(scoreList)
        bin = numpy.arange(-2, 2, 0.1)
        pyplot.hist(scoreList, bin)
        pyplot.show()


    def training_model(self, X, Y, X_test, Y_test, X_latest, stockIdList):
        start_time = time.time()
        x_train, y_train, x_test, y_test = [], [], [], []
        for i in range(len(X)):
            if random.random() < 0.85:
                x_train.append(X[i])
                y_train.append(Y[i])
            else:
                x_test.append(X[i])
                y_test.append(Y[i])
        GBR = GradientBoostingRegressor(n_estimators=100,learning_rate=0.5,min_samples_leaf=100,\
                                          max_leaf_nodes=6,random_state=0,loss='ls')
        #GBR = GradientBoostingClassifier(n_estimators=100,learning_rate=0.5,min_samples_leaf=100,\
        #                                  max_leaf_nodes=5,random_state=0,loss='deviance')
        model = GBR.fit(x_train,y_train)
        print 'time: ', time.time()-start_time

        print 'training result:'
        self.predict_result(model, x_train, y_train)
        print 'training test result: (total:', len(X), ',test:', len(x_test), ')'
        self.predict_result(model, x_test, y_test)
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
            if i%18 == 0: print ''
            print '{0:4}'.format(fi[i]),
        print ''





if __name__ == '__main__':

    stock = Stock()
    #stock.init(sys.argv[1])
    stock.init('127.0.0.1:6379')

    if len(sys.argv) < 2:
        print stock.get_time('00:00:00')

        #stock.push_redis_url('http://www.qq.com')
        pass

    elif sys.argv[1] == 'model':
        X, Y, X_test, Y_test, X_latest, IdList = stock.generate_training_data(default_day=10,test_day=[4,0,2])
        #X, Y, X_test, Y_test, X_latest, IdList = stock.generate_training_data_0day(default_day=2,test_day=[2,0,0])
        print len(X), len(Y), len(X_test), len(Y_test), len(X_latest), len(IdList)
        #print X[-1], Y[-1]
        stock.training_model(X, Y, X_test, Y_test, X_latest, IdList)

    elif sys.argv[1] == 'price':
        stock.crawl_stock_price_info()

    elif sys.argv[1] == 'price_0day':
        stock.crawl_stock_price_info(flag={'0day':'11:30:00'})

    elif sys.argv[1] == 'price_0day_summary':
        stock.summary_stock_price_info(K=1, default_x=5)
        stock.summary_stock_price_info(K=5, default_x=5)
        stock.summary_stock_price_info(K=10, default_x=5)
        #stock.summary_stock_price_info(K=15, default_x=5)

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


