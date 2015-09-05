nohup mongod --dbpath /Users/zgm/program/mongodb/data/db &
nohup redis-server &
python scrapySpider/spiders/spider_feeder.py
scrapy crawl stockSpider
