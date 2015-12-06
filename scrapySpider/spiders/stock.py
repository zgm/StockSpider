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
import pickle
import os
import urllib2
import requests


MONGODB_URI = 'mongodb://127.0.0.1:27017/'



class Stock(object):

    def init(self, redis_server):
        self.mongo_client = MongoClient(MONGODB_URI)
        self.db = self.mongo_client['stock']
        self.col = self.db['table'] # 股票信息
        self.gn = self.db['gn'] # 股票概念信息

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


    # 抓取概念板块的股票信息
    def crawl_gn_url_list(self):
        page = '<a href="http://q.10jqka.com.cn/stock/gn/albbgn/">阿里巴巴概念</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/af/">安防</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/bj/">白酒</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/cgjr/">参股金融</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/cgqs/">参股券商</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/cgxg/">参股新股</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/cgl/">草甘膦</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/cd/">超导</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/clw/">车联网</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/cdz/">充电桩</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/cmp/">触摸屏</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/ct/">创投</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/dfj/">大飞机</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/dsj/">大数据</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/dsn/">迪士尼</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/dxgw/">地下管网</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/dlgg/">电力改革</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/dzfp/">电子发票</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/dzsw/">电子商务</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/dmzmq/">东盟自贸区</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/dlldc/">动力/锂电池</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/etgn/">二胎概念</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/fsrl/">分散染料</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/fd/">风电</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/fn/">风能</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/fhg/">氟化工</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/fjzmq/">福建自贸区</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/gdzb/">高端装备</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/gsz/">高送转</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/gszyq/">高送转预期</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/gt/">高铁</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/gx/">高校</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/gy40/">工业4.0</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/gyljr/">供应链金融</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/gdzc/">股东增持</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/gfcl/">固废处理</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/gfgn/">光伏概念</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/gcrj/">国产软件</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/hgzb/">海工装备</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/hzyyh/">杭州亚运会</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/hd/">核电</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/hlwcp/">互联网彩票</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/hlwjr/">互联网金融</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/hgtgn/">沪港通概念</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/hj/">黄金</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/jqrgn/">机器人概念</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/jycx/">基因测序</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/jcdl/">集成电路</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/jydq/">家用电器</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/jzjn/">建筑节能</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/jkzg/">健康中国</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/jsgzgg/">江苏国资改革</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/jnhb/">节能环保</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/jnzm/">节能照明</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/jric/">金融IC</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/jjjyth/">京津冀一体化</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/jp/">举牌</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/jg/">军工</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/o2ogn/">O2O概念</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/kjds/">跨境电商</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/kdzg/">宽带中国</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/lbs/">蓝宝石</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/llwl/">冷链物流</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/ldc/">锂电池</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/ltygg/">两桶油改革</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/mygn/">马云概念</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/mhg/">煤化工</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/mlzg/">美丽中国</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/myyy/">民营医院</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/myyx/">民营银行</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/nyhlw/">能源互联网</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/ncds/">农村电商</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/nj/">农机</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/nyxdh/">农业现代化</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/p2pgn/">P2P概念</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/pm25/">PM2.5</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/pppgn/">PPP概念</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/stbk/">ST板块</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/pggn/">苹果概念</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/qhgn/">期货概念</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/qcdz/">汽车电子</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/qlg/">禽流感</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/rzrq/">融资融券</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/ry/">乳业</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/shgzgg/">上海国资改革</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/shzmq/">上海自贸区</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/sgt/">深港通</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/szgzgg/">深圳国资改革</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/stny/">生态农业</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/swyy/">生物医药</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/swzn/">生物质能</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/smx/">石墨烯</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/spaq/">食品安全</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/sjyx/">手机游戏</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/sl/">水利</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/tyn/">太阳能</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/tbf/">钛白粉</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/txw/">碳纤维</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/tg/">特钢</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/tgy/">特高压</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/tsl/">特斯拉</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/tycy/">体育产业</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/tjzmq/">天津自贸区</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/trq/">天然气</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/tyhk/">通用航空</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/tdlz/">土地流转</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/tltx/">脱硫脱硝</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/wyw/">王亚伟</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/wlaq/">网络安全</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/wlcp/">网络彩票</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/wlyx/">网络游戏</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/wsszj/">维生素涨价</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/wqzl/">尾气治理</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/wxdh/">卫星导航</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/whcm/">文化传媒</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/wscl/">污水处理</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/wrj/">无人机</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/wlw/">物联网</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/wldspt/">物流电商平台</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/xazmq/">西安自贸区</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/xqds/">西气东输</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/xqzy/">稀缺资源</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/xtyc/">稀土永磁</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/xjs/">小金属</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/xclgn/">新材料概念</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/xgycxg/">新股与次新股</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/xjzx/">新疆振兴</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/xny/">新能源</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/xnyqc/">新能源汽车</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/xsb/">新三板</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/xxczh/">新型城镇化</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/xnxs/">虚拟现实</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/xxgng/">徐翔概念股</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/ylgn/">养老概念</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/yyq/">页岩气</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/ydyl/">一带一路</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/ylgg/">医疗改革</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/ylqx/">医疗器械</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/yyds/">医药电商</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/ydhlw/">移动互联网</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/ydzf/">移动支付</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/ypgg/">油品改革</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/ypsj/">油品升级</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/ygazmq/">粤港澳自贸区</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/yjs/">云计算</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/zxjy/">在线教育</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/zxly/">在线旅游</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/zxdb/">振兴东北</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/zjcg/">证金持股</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/zyjy/">职业教育</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/zhcs/">智慧城市</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/zncd/">智能穿戴</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/znds/">智能电视</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/zndw/">智能电网</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/znjj/">智能家居</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/znyl/">智能医疗</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/zhzmq/">中韩自贸区</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/zr/">猪肉</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/zrqbd/">转融券标的</a>\
                <a href="http://q.10jqka.com.cn/stock/gn/zqgn/">足球概念</a>\
        '
        GN = re.findall("gn/[a-z0-9]*/", page)
        GN_name = re.findall(">[^<]*</a", page)

        index = 0
        for gn in GN:
            gn = gn[3:-1]
            #print gn, GN_name[index][1:-3]
            _data = self.gn.find_one({'name':gn})
            if not _data: _data = {'name':gn}
            _data['gn'] = GN_name[index][1:-3]
            index += 1
            self.gn.save(_data)
            #continue
            for i in range(1,8):
                url = "http://q.10jqka.com.cn/interface/stock/detail/zdf/desc/" + str(i) + "/3/" + gn
                self.push_redis_url(url)

    def summary_stock_gn_info(self):
        gnList = self.gn.find({}, {'name':1, 'stockIdList':1, 'gn':1})

        stockGnInfo = {}
        for gn in gnList:
            name, gn_name = gn['name'], gn['gn']
            for stockId in gn['stockIdList']:
                if stockId not in stockGnInfo:
                    stockGnInfo[stockId] = [[name, gn_name]]
                else:
                    stockGnInfo[stockId].append([name, gn_name])

        for stockId in stockGnInfo:
            _data = self.col.find_one({'stockId':stockId})
            if _data:
                _data['gn'] = stockGnInfo[stockId]
                if 'pankou' in _data: del _data['pankou']
                if '60m' in _data: del _data['60m']
                if '60m_datetime' in _data: del _data['60m_datetime']
                print stockId, _data['gn']
                self.col.save(_data)


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
            #if isInt and not _data: continue
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
        #if value < 0.0: return round(2*value/1.0,1)
        return round(value/1.0,1)
        if value >= 1.0: return 5.0
        elif value <= 1.0: return -5.0
        else: return 0.0


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
        print 'time: ', time.time()-start_time
        minute_time = time.time()-start_time
        decay_time = minute_time

        X, Y, X_latest, IdList = [], [], [], []
        X_test, Y_test = [[] for i in range(test_day[0])], [[] for i in range(test_day[0])]
        for stockId in stockIdList:
            Info = self.col.find_one({'stockId':stockId})
            if Info.get('flag')!="1" or Info.get('current')==0: continue # stop stock
            if 'name' in Info and Info['name'].find('ST') >= 0: continue # ST stock

            price, name, gn = Info['1day'], Info['name'], Info.get('gn')
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
                    minute_time1 = time.time()
                    minute_feature[date], priceInfo = self.generate_minute_feature(minute[date])
                    for decay in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
                        for p in minute_price[decay]:
                            minute_price[decay][p] *= decay
                        for p in priceInfo:
                            if p in minute_price[decay]: minute_price[decay][p] += priceInfo[p]
                            else: minute_price[decay][p] = priceInfo[p]
                    minute_time += time.time()-minute_time1
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
                decay_time1 = time.time()
                for decay in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
                    x.extend(self.get_decay_feature_percent(close, minute_price[decay]))
                decay_time += time.time()-decay_time1

                #for decay in [0, 1, 2, 4]:
                #    x.append(100.0*self.get_decay_feature(decay_x, decay=decay)/close-100.0)
                x = [round(value,2) for value in x] # 统一数字

                x.extend([Total, Float, Avg, Total*close, Float*close, Avg*close, avg_volume*close])
                x.extend([Info[key]/close for key in ['eps','net_assets', 'dividend']])
                x.extend([Info[key]*close/Info['current'] for key in ['pe_ttm','pe_lyr','pb','psr']])
                x.append(self.get_flag_feature(stockId))
                #for id in ['SH000001', 'SZ399001', 'SZ399005', 'SZ399006']: # 沪 深 中小板 创业板
                #    x.append(self.get_delta_feature(id, price_list[i-1]['time'], price_list[i]['time']))

                if i == N-1:
                    X_latest.append(x)
                    IdList.append([stockId, name, gn])
                else:
                    y0 = self.get_target( 100.0*(price[i+1]['close']-price[i+1]['open'])/close )
                    y1 = self.get_target(price[i+1]['percent'])
                    y2 = 100.0*(price[i+1]['close']-price[i+1]['open'])/close
                    if i <= N-3 and y2 > 0 and price[i+2]['percent'] > 0: y2 += price[i+2]['percent']
                    y2 = self.get_target( y2 )

                    if i < N-test_day[0]:
                        X.append(x)
                        Y.append([y0, y1, y2])
                    elif N-test_day[0]+test_day[1] <= i and i <= N-test_day[0]+test_day[2]:
                        index = i-N+test_day[0]
                        X_test[index].append(x)
                        Y_test[index].append([y0, y1, y2])
        print len(Y), sum([y[0] for y in Y]), sum([y[1] for y in Y]), sum([y[2] for y in Y])
        print 'time: ', time.time()-start_time, minute_time, decay_time
        return X, Y, X_test, Y_test, X_latest, IdList


    # minute[]: price / percent / volume / avg_price
    def generate_minute_feature_daily(self, minute, K=8):
        x = []

        N = len(minute)
        total_volume = sum([minute[i][-2] for i in range(N)])
        total_out_volume, total_in_volume, total_out, total_in = 0.0, 0.0, 0.0, 0.0

        cur_price, percent, volume, Out_volume, In_volume, Out, In = None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        L, close = N/K, minute[-1][-4]/(1.0+0.01*minute[-1][-3])
        for i in range(N):
            price = minute[i][-4]
            percent = minute[i][-3]
            volume += minute[i][-2]

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

        return x


    def generate_training_data_daily(self, test_day=[4,0,2]):
        start_time = time.time()
        stockIdList = self.get_stockId_all()
        print 'time: ', time.time()-start_time
        minute_time = time.time()-start_time
        decay_time = minute_time

        X, Y = [], []
        X_test, Y_test = [[] for i in range(test_day[0])], [[] for i in range(test_day[0])]
        #stockIdList = ['SZ300024']
        for stockId in stockIdList:
            Info = self.col.find_one({'stockId':stockId})
            if Info.get('flag')!="1" or Info.get('current')==0: continue # stop stock
            if 'name' in Info and Info['name'].find('ST') >= 0: continue # ST stock

            price, name = Info['1day'], Info['name']
            minute = {date:json.loads(Info['minute'][date]) for date in Info['minute']}

            N = len(price)
            for i in range(1, N): # 第一个数据只使用close价格
                date = str( self.get_datetime(price[i]['time']) )
                if not minute.get(date) or len(minute[date])<200: continue
                L = len(minute[date])
                M = L/2
                #close = minute[date][-1][-4]/(1.0+0.01*minute[date][-1][-3])
                x = self.generate_minute_feature_daily(minute[date][0:M])
                x = [round(value,2) for value in x] # 统一数字
                y0 = self.get_target( minute[date][-1][-3]-minute[date][M-1][-3] )
                y1 = self.get_target( minute[date][-1][-3] )

                if i < N-test_day[0]:
                    X.append(x)
                    Y.append([y0, y1])
                elif N-test_day[0]+test_day[1] <= i and i <= N-test_day[0]+test_day[2]:
                    index = i-N+test_day[0]
                    X_test[index].append(x)
                    Y_test[index].append([y0, y1])
        print len(Y), sum([y[0] for y in Y]), sum([y[1] for y in Y])
        print 'time: ', time.time()-start_time, minute_time, decay_time
        return X, Y, X_test, Y_test


    def predict_result(self, model, X, Y=None, yIndex=None, stockIdList=None, myList=None, Show=True):
        scoreList, selectList, N = [], [], len(X)
        for i in range(N):
            score = model.predict(X[i])
            score[0] = round(score[0], 3)
            scoreList.append(score[0])
            if stockIdList and myList and stockIdList[i][0] in myList:
                print '$'+stockIdList[i][1]+'('+stockIdList[i][0]+')'+'$', 'score: ', score[0]
            if score[0] >= 3.0 and stockIdList:
                selectList.append([stockIdList[i], score[0]]) #print stockIdList[i]

        #for threshold in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]:
        for threshold in [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]:
            pp, pn, np, nn, pY = 0, 0, 0, 0, []
            for i in range(N):
                if Y and scoreList[i] >= threshold: pY.append(Y[i][yIndex])
                if Y and Y[i][yIndex] > 0.0:
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

        S = sorted(selectList, key=lambda x: x[1], reverse=True)
        for i in range(min(len(S), 20)):
            print '$'+S[i][0][1]+'('+S[i][0][0]+')'+'$', S[i][1],
            if S[i][0][2]:
                for gn in S[i][0][2]: print gn[1],
            print ''

        if Show:
            #print 'min score: ', min(scoreList), 'max score: ', max(scoreList)
            bin = numpy.arange(-10, 10, 0.5)
            pyplot.hist(scoreList, bin)
            pyplot.show()


    def training_model(self, X, Y, X_test, Y_test, X_latest, stockIdList, yIndex):
        start_time = time.time()
        x_train, y_train, x_train2, y_train2, x_test, y_test = [], [], [], [], [], []
        for i in range(len(X)):
            if True or random.random() < 0.85:
                x_train.append(X[i])
                y_train.append(Y[i][yIndex])
                if yIndex < 0 and Y[i][yIndex] < -0.0:
                    x_train.append(X[i])
                    y_train.append(Y[i][yIndex])
                x_train2.append(X[i])
                y_train2.append(Y[i])
            else:
                x_test.append(X[i])
                y_test.append(Y[i])
        if True or not os.path.exists('model.p'):
            model = GradientBoostingRegressor(n_estimators=100,learning_rate=0.8,min_samples_leaf=100,\
                                          max_leaf_nodes=7,random_state=0,loss='ls').fit(x_train,y_train)
            #GBR = GradientBoostingClassifier(n_estimators=100,learning_rate=0.5,min_samples_leaf=100,\
            #                                  max_leaf_nodes=5,random_state=0,loss='deviance')
            file = open('model.p','wb')
            pickle.dump(model, file)
            file.close()
        else:
            file = open('model.p','rb')
            model = pickle.load(file)
            print 'load', type(model)
        print 'time: ', time.time()-start_time

        print 'training result:'
        self.predict_result(model, x_train2, y_train2, yIndex)
        print 'training test result: (total:', len(X), ',test:', len(x_test), ')'
        if len(x_test): self.predict_result(model, x_test, y_test, yIndex)
        print 'test result:'
        for i in range(len(X_test)):
            if len(X_test[i]) == 0: continue
            print len(X_test[i]), len(Y_test[i])
            self.predict_result(model, X_test[i], Y_test[i], yIndex)

        myList = {'SZ300025', 'SZ000681', 'SZ000687', 'SH600677', 'SH600397', 'SZ300427'\
                  ,'SZ300104', 'SZ300120', 'SH603918', 'SZ300163', 'SZ002733', 'SZ300239', 'SZ002599'
        }
        print 'latest result:'
        if X_latest:
            self.predict_result(model, X_latest, Y=None, stockIdList=stockIdList, myList=myList)

        fi = model.feature_importances_
        fi = [round(100*v,2) for v in fi]
        for i in range(len(fi)):
            if i%self.line == 0: print ''
            print '{0:4}'.format(fi[i]),
        print ''

        return model


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



def crawl_content(url):
    print url
    try:
        print 'start'
        r = urllib2.urlopen(url, 60)
        print 'end'
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
            #print r.status_code,
            if r.status_code != requests.codes.ok:
                return False
            r = r.text
            #print r
            return r
    except Exception as e:
        return False



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
        X, Y, X_test, Y_test, X_latest, IdList = stock.generate_training_data(default_day=10,test_day=[4,0,2])
        print len(X), len(Y), len(X_test), len(Y_test), len(X_latest), len(IdList)
        print X[-1], Y[-1]
        for yIndex in [0, 1, 2, -3, -2, -1]:
            stock.training_model(X, Y, X_test, Y_test, X_latest, IdList, yIndex)
        #stock.model_para(X, Y, X_test, Y_test)

    elif sys.argv[1] == 'model_daily':
        stockIdList = stock.get_stockId_all()
        #stockIdList = ['SZ300024']
        XX, IdList = [], []
        for stockId in stockIdList:
            url = 'http://api.finance.ifeng.com/aminhis/?code=' + stockId.lower() + '&type=five'
            data = crawl(url)
            if not data: continue
            data = json.loads(data)

            #print type(data), data
            for Info in data:
                #print stockId, Info
                date = Info['record'][0][0][0:10]
                if date != str(datetime.date.today()): continue
                minute, N = [], len(Info['record'])
                for s in Info['record']:
                    s = [v.replace(',','') for v in s]
                    minute.append([float(s[1]),float(s[2]),float(s[3]),float(s[4])])

                x = stock.generate_minute_feature_daily(minute[0:N])
                x = [round(value,2) for value in x] # 统一数字
                if not XX: print x, stockId
                XX.append(x)
                IdList.append(stockId)
        print len(XX), len(IdList)

        X, Y, X_test, Y_test = stock.generate_training_data_daily(test_day=[3,0,2])
        print len(X), len(Y), len(X_test), len(Y_test)
        print X[-1], Y[-1]
        for yIndex in [0, 1, -2, -1]:
            model = stock.training_model(X, Y, X_test, Y_test, None, None, yIndex)

            scoreList, selectList = [], []
            for i in range(len(XX)):
                score = model.predict(XX[i])
                scoreList.append(score[0])
                selectList.append([IdList[i], score[0]])
            S = sorted(selectList, key=lambda x: x[1], reverse=True)
            for i in range(min(len(S), 10)):
                print '$(' + S[i][0] + ')$', S[i][1]

            bin = numpy.arange(-10, 10, 0.5)
            pyplot.hist(scoreList, bin)
            pyplot.show()

    elif sys.argv[1] == 'price':
        stock.crawl_stock_price_info()

    elif sys.argv[1] == 'basic':
        stock.crawl_stock_basic_info()

    elif sys.argv[1] == 'gn_url':
        stock.crawl_gn_url_list()

    elif sys.argv[1] == 'gn_summary':
        stock.summary_stock_gn_info()

    elif sys.argv[1] == 'drawK':
        stockIdList = ['SH'+str(key) for key in range(600000, 604000)]
        stock.draw_forchartk([stockIdList])


