# -*- coding: utf-8 -*-
import redis
import sys
import time
import datetime
import re
from pymongo import MongoClient


MONGODB_URI = 'mongodb://127.0.0.1:27017/'



class SpiderFeeder(object):

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

    # 抓取行业的股指股票信息
    def get_hy_url_list(self):
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
    def get_stock_hy_info(self):
        stockIdList = self.col.find({}, {'stockId':1, 'hy':1, 'hyname':1})
        for stockIdInfo in stockIdList:
            if 'hy' in stockIdInfo: continue
            stockId = stockIdInfo['stockId']

            url = 'http://stockpage.10jqka.com.cn/spService/' + stockId[2:] + '/Header/realHeader'
            self.update_redis_info(url)

    # 股票逐笔成交信息，例子 url = http://hqdigi2.eastmoney.com/EM_Quote2010NumericApplication/CompatiblePage.aspx?Type=OB&stk=6006631&page=5
    #                           http://hqdigi2.eastmoney.com/EM_Quote2010NumericApplication/CompatiblePage.aspx?Type=OB&stk=0006812&page=2
    def get_stock_trade_info(self):
        pass

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

            _data = self.col.find_one({'stockId': id})
            if isInt and not _data: continue
            if not _data: _data = {}


            end = int(time.time()*1000)
            begin = end - 90*24*3600*1000

            if 'totalShares' not in _data:
                url = 'http://xueqiu.com/v4/stock/quote.json?code=' + id
                self.update_redis_info(url)
            if not _data.get('0day') or _data['0day'][-1][0]['time'] != self.get_time('09:30:00'):
                url = 'http://xueqiu.com/stock/forchart/stocklist.json?symbol=' + id + '&period=1d&one_min=1'
                self.update_redis_info(url)
            if not _data.get('1day') or _data['1day'][-1]['time'] != self.get_time('00:00:00'):
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
    #spider_feed.get_hy_url_list()
    #spider_feed.get_stock_hy_info()
