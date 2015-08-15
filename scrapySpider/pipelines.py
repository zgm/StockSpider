# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html


from pymongo import MongoClient
from scrapySpider.items import stockItem


MONGODB_URI = 'mongodb://127.0.0.1:27017/'


class ScrapyspiderPipeline(object):

    def __init__(self, mongodb_uri):
        self.mongodb_uri = mongodb_uri
        self.mongo_client = MongoClient(mongodb_uri)
        self.db = self.mongo_client['stock']
        self.col = self.db['table']

    @classmethod
    def from_settings(cls, settings):
        mongodb_uri = settings.get('MONGODB_URI', MONGODB_URI)
        return cls(mongodb_uri)

    def save(self, url, data):
        # get stock id
        index, index2 = url.find('symbol='), url.find('code')
        if index >= 0:
            stockId = url[index+7:index+15]
        elif index2 >= 0:
            stockId = url[index2+5:index2+13]
        else:
            print 'error to parse stock id'
            return

        # get mongo data
        if self.col.find_one() is None:
            self.col.ensure_index('stockId', backgroud=True)

        spec = {'stockId': stockId}
        _data = self.col.find_one(spec)
        if not _data:
            _data = {'stockId': stockId}

        if url.find('period=1d') >= 0 and not data.get('chartlist'):
            print 'empty in the charlist!'
            return

        # get data field
        if url.find('period=1day') >= 0:
            _data['1day'] = data['chartlist']
        elif url.find('period=1d&one_min=1') >= 0:
            if '0day' not in _data:
                _data['0day'] = [data['chartlist']]
            elif _data['0day'][-1][0]['time'] != data['chartlist'][0]['time']:
                _data['0day'].append(data['chartlist'])
                if len(_data['0day']) > 7:
                    _data['0day'] = _data['0day'][1:]
            else:
                _data['0day'][-1] = data['chartlist']
        elif url.find('code=') >= 0:
            _data['totalShares'] = data[stockId]['totalShares']
            _data['float_shares'] = data[stockId]['float_shares']
            _data['current'] = data[stockId]['current']
        else:
            print 'error for this kind of url'
            return

        # write data
        self.col.save(_data)


    def process_item(self, item, spider):
        #print item

        self.save(item['src'], item['content'])

        return item


#r = ScrapyspiderPipeline('mongodb://127.0.0.1:27017/')
#r.save()

