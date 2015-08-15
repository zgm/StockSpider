# MyScrapy
scrapy spider for stock data


stock web (url list) => redis => scrapy (spider) => mongo (database)

process:
1. setup up python 2.7, redis and mongo, with scrapy and scrapy_redis and mongo module.
2. run mongod and redis-server, scrapy crawl stockSpider (spider name)
3. run python spider_feeder.py to sent url list to redis-server
4. scrapy spider will read urls from redis-server, and then download the web data, save data to mongo.



