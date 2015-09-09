# -*- coding: utf-8 -*-
import redis
import time
import datetime
import re
import sys
import numpy
import matplotlib.dates as dates
from matplotlib.dates import DateFormatter, WeekdayLocator, HourLocator, DayLocator, MONDAY
import matplotlib.pyplot as pyplot
import matplotlib.finance as finance
from pymongo import MongoClient

from sklearn.metrics import mean_squared_error
from sklearn.datasets import make_friedman1
from sklearn.ensemble import GradientBoostingRegressor

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


    # "Mon Aug 17 09:30:00 +0800 2015"
    def get_time(self, cur_time='09:30:00'):
        Weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'] # 0 1 2 3 4
        Month = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'] # 0 ... 11

        today = datetime.date.today()
        day, weekday, month, year = today.day, today.weekday(), today.month, today.year
        # 周末变周五
        if weekday > 4:
            day = day + 4 - weekday
            weekday = 4
        if day < 10: day = '0' + str(day)

        return Weekday[weekday] + ' ' + Month[month-1] + ' ' + str(day) + ' ' + cur_time + ' +0800 ' + str(year)
    # "Mon Aug 17 09:30:00 +0800 2015"
    def get_datetime(self, time):
        Weekday = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        year, month, day = int(time[-4:]), time[4:7], int(time[8:10])
        for i in range(len(Weekday)):
            if month == Weekday[i]:
                month = i + 1
                break

        return datetime.date(year, month, day)


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
            #print hy
            #continue
            _data = self.hy.find_one({'name':hy})
            #if not _data: continue

            url = "http://q.10jqka.com.cn/interface/stock/detail/zdf/desc/1/1/" + hy
            self.update_redis_info(url)
            url = "http://q.10jqka.com.cn/interface/stock/detail/zdf/desc/2/1/" + hy
            self.update_redis_info(url)


    # http://stockpage.10jqka.com.cn/spService/000687/Funds/realFunds 行业资金流向
    # http://stockpage.10jqka.com.cn/spService/000687/Header/realHeader 股票行业信息
    def crawl_stock_hy_info(self):
        stockIdList = self.col.find({}, {'stockId':1, 'hy':1, 'hyname':1})
        for stockInfo in stockIdList:
            if 'hy' in stockInfo: continue
            stockId = stockInfo['stockId']

            url = 'http://stockpage.10jqka.com.cn/spService/' + stockId[2:] + '/Header/realHeader'
            self.update_redis_info(url)


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
            self.update_redis_info(url)
        self.update_redis_info('http://xueqiu.com')

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
        stockIdList = self.col.find({}, {'stockId':1, 'totalShares':1, 'flag':1, 'eps':1, 'name':1})
        for stockInfo in stockIdList:
            if 'name' in stockInfo and 'flag' in stockInfo and 'eps' in stockInfo:
                continue
            stockId = stockInfo['stockId']

            url = 'http://xueqiu.com/v4/stock/quote.json?code=' + stockId
            self.update_redis_info(url)
        self.update_redis_info('http://xueqiu.com')


    def crawl_stock_price_info(self):
        stockid = [i for i in range(1,101)]
        stockid.extend([i for i in range(150, 167)])
        stockid.extend([301, 333, 338, 1696, 1896])
        stockid.extend([i for i in range(400, 1000)])

        stockid.extend([i for i in range(2000,2777)])
        stockid.extend([i for i in range(300000,300489)])
        stockid.extend([i for i in range(600000,602000)])
        stockid.extend([i for i in range(603000,604000)])
        stockid.extend(['SH000001', 'SZ399006'])

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
            begin = end - 90*24*3600*1000

            if _data.get('flag') != "1": continue # 停牌

            # http://xueqiu.com/stock/pankou.json?symbol=SZ000681&_=1438135032243 盘口数据
            if not _data.get('0day') or _data['0day'][-1][0]['time'] != self.get_time('09:30:00'):
                url = 'http://xueqiu.com/stock/forchart/stocklist.json?symbol=' + id + '&period=1d&one_min=1'
                self.update_redis_info(url)
            if not _data.get('1day') or _data['1day'][-1]['time'] != self.get_time('00:00:00'):
                url = 'http://xueqiu.com/stock/forchartk/stocklist.json?symbol=' + id + '&period=1day&type=before&begin=' + str(begin) + '&end=' + str(end)
                self.update_redis_info(url)

        #self.update_redis_info('http://xueqiu.com/stock/forchart/stocklist.json?symbol=SZ000681\
        # &period=1d&one_min=1')
        #self.update_redis_info('http://xueqiu.com/stock/forchartk/stocklist.json?symbol=SZ000681\
        # &period=1day&type=before&begin=1407602252104&end=1439138252104')
	
        self.update_redis_info('http://xueqiu.com')


    def generate_stockIdList(self, stockId):
        return []

    # 获取股票列表的k线图数据
    def get_forchartk(self, stockIdList, type='totalShares'):
        #print self.get_datetime("Wed Apr 15 00:00:00 +0800 2015")
        #start_time = time.time()
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
        #print time.time()-start_time
        timeList = sorted(set(timeList))
        #print time.time()-start_time, len(timeList), len(valid_stockIdList), valid_stockIdList

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
        #print time.time()-start_time
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

    # 取stockIdList中股票数据
    def generate_training_data(self, stockIdList=None, default_day=10, test_day=5):
        start_time = time.time()
        if stockIdList is None:
            stockIdList = self.col.find({}, {'stockId':1, 'name':1})
            stockIdList = [[Info['stockId'],Info['name']] for Info in stockIdList]
        print 'time: ', time.time()-start_time

        X, Y, X_test, Y_test, X_latest, IdList = [], [], [], [], [], []
        for stockId, name in stockIdList:
            info = self.col.find_one({'stockId':stockId},{'0day':0})
            if info.get('flag')!="1" or info.get('current')==0: continue # 停牌
            if 'name' in info and info['name'].find('ST') >= 0: continue # ST股票
            price_list = info['1day']

            list_len = len(price_list)
            volume = [1.0*price['volume'] for price in price_list]
            turnrate = [price['turnrate'] for price in price_list]
            if sum(volume) == 0 or sum(turnrate) == 0: continue

            avg_volume, avg_turnrate = sum(volume)/list_len/1e8, sum(turnrate)/list_len
            Total, Float, Avg = info['totalShares']/1e8, info['float_shares']/1e8, info['volumeAverage']/1e8
            for i in range(default_day, list_len): # 第一个数据只使用close价格
                avg_price = sum([price['close'] for price in price_list[i-default_day+1:i+1]])/default_day

                x = []
                for j in range(i-default_day+1, i+1):
                    for key in ['open', 'close', 'high', 'low']:
                        x.append( 100.0*price_list[j][key]/price_list[j-1]['close']-100.0 )
                    for key in ['ma5', 'ma10', 'ma20', 'ma30']:
                        x.append( 100.0*price_list[j][key]/price_list[j]['close']-100.0 )
                    x.append(price_list[j]['turnrate']/avg_turnrate) # 归一化交易量
                    #for key in ['percent', 'dif', 'dea', 'macd']:
                    for key in ['dif', 'dea', 'macd']:
                        x.append(price_list[j][key])

                close = price_list[i]['close']
                x.extend([Total, Float, Avg, Total*close, Float*close, Avg*close, avg_volume*close])
                x.extend([info[key]/close for key in ['eps','net_assets', 'dividend']])
                x.extend([info[key]*close/info['current'] for key in ['pe_ttm','pe_lyr','pb','psr']])
                if i < list_len-test_day:
                    X.append(x)
                    #Y.append(price_list[i+1]['percent']/10.0)
                    Y.append(price_list[i+1]['percent'] > 1.5 and 1. or -1.)
                    #if price_list[i+1]['percent'] > 6.0: # 重复 提高权重
                    #    X.append(x)
                    #    Y.append(1.0)
                elif i == list_len-1:
                    X_latest.append(x)
                    IdList.append([stockId, name])
                else:
                    X_test.append(x)
                    #Y_test.append(price_list[i+1]['percent']/10.0)
                    Y_test.append(price_list[i+1]['percent'] > 1.5 and 1. or -1.)
        print len(Y), sum(Y)
        print 'time: ', time.time()-start_time
        return X, Y, X_test, Y_test, X_latest, IdList

    def predict_result(self, model, X, Y=None, stockIdList=None, myList=None):
        pp, pn, np, nn = 0, 0, 0, 0
        scoreList, selectList = [], []
        for i in range(len(X)):
            score = model.predict(X[i])
            score[0] = round(score[0], 3)
            scoreList.append(score[0])
            if stockIdList and myList and stockIdList[i][0] in myList:
                print '$'+stockIdList[i][1]+'('+stockIdList[i][0]+')'+'$', 'score: ', score[0]
            if score[0] >= 0.5 and stockIdList:
                selectList.append([stockIdList[i], score[0]]) #print stockIdList[i]

            if Y and Y[i] > 0.0:
                if score[0] >= 0.5: pp += 1
                else: pn += 1
            else:
                if score[0] >= 0.5: np += 1
                else: nn += 1
        if Y:
            print pp, pn, np, nn, 'P/R: ', 1.0*pp/(pp+np), 1.0*pp/(pp+pn), 'predict p: ', 1.0*(pp+np)/(len(X))
            print 'mean error: ', mean_squared_error(Y, model.predict(X))
        else:
            print np, nn, 'predict p: ', 1.0*np/(np+nn)

        selectList = sorted(selectList, key=lambda x: x[1], reverse=True)
        for i in range(min(len(selectList), 20)):
            #print selectList[i][0], selectList[i][1]
            print '$'+selectList[i][0][1]+'('+selectList[i][0][0]+')'+'$', selectList[i][1]

        print 'min score: ', min(scoreList), 'max score: ', max(scoreList)
        bin = numpy.arange(-2, 2, 0.1)
        pyplot.hist(scoreList, bin)
        pyplot.show()



    def training_model(self, X, Y, X_test, Y_test, X_latest, stockIdList):
        start_time = time.time()
        x_train, y_train, x_test, y_test = [], [], [], []
        for i in range(len(X)):
            if random.random() < 0.7:
                x_train.append(X[i])
                y_train.append(Y[i])
            else:
                x_test.append(X[i])
                y_test.append(Y[i])
        GBR = GradientBoostingRegressor(n_estimators=100,learning_rate=0.5,min_samples_leaf=100,\
                                          max_leaf_nodes=5,random_state=0,loss='ls')
        model = GBR.fit(x_train,y_train)
        print 'time: ', time.time()-start_time

        print 'old data result: (total:', len(X), ',test:', len(x_test), ')'
        self.predict_result(model, x_test, y_test)
        print 'test result:'
        self.predict_result(model, X_test, Y_test)
        myList = {'SZ300025', 'SZ000681', 'SZ002637', 'SH600285', 'SZ000687', 'SH600677', 'SH600397', 'SZ000698'}
        print 'latest result:'
        self.predict_result(model, X_latest, Y=None, stockIdList=stockIdList, myList=myList)

        fi = GBR.feature_importances_
        fi = [round(v,4) for v in fi]
        for i in range(0,len(fi),12):
            print fi[i:i+12]





if __name__ == '__main__':

    #if len(sys.argv) != 2:
    #    print 'Usage: {0} conf_file'.format(__file__)
    #    sys.exit(1)

    stock = Stock()
    #stock.init(sys.argv[1])
    stock.init('127.0.0.1:6379')

    if len(sys.argv) < 2:
        pass

    elif sys.argv[1] == 'model':
        X, Y, X_test, Y_test, X_latest, IdList = stock.generate_training_data(None,default_day=10,test_day=4)
        print len(X), len(Y), len(X_test), len(Y_test), len(X_latest), len(IdList)
        #print X[-1], Y[-1]
        scoreList = stock.training_model(X, Y, X_test, Y_test, X_latest, IdList)

    elif sys.argv[1] == 'stock_price':
        stock.crawl_stock_price_info()

    elif sys.argv[1] == 'stock_basic':
        stock.crawl_stock_basic_info()

    elif sys.argv[1] == 'stock_pankou':
        stock.crawl_stock_pankou_info()

    elif sys.argv[1] == 'stock_pankou_summary':
        stock.summary_stock_pankou_info()

    elif sys.argv[1] == 'hy_url':
        stock.crawl_hy_url_list()

    elif sys.argv[1] == 'stock_hy':
        stock.crawl_stock_hy_info()

    elif sys.argv[1] == 'draw_forchartk':
        stockIdList = ['SH'+str(key) for key in range(600000, 604000)]
        stock.draw_forchartk([stockIdList])


