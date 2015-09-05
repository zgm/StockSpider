# MyScrapy
scrapy spider for stock data, and then generate training data, train the model to predict stock price.


stock web (url list) => redis => scrapy (spider) => mongo (database)
mongo data => training data => model => stock price

process:
1. setup up python 2.7, redis and mongo, with scrapy and scrapy_redis and mongo module.

2. run mongod and redis-server, then scrapy crawl stockSpider (spider name)

3. cd scrapySpider/spider, run python stock.py stock_price to sent url list to redis-server

4. scrapy spider will read urls from redis-server, and then download the web data, save data to mongo.

5. step 4 will crawl stock basic info, run python stock.py stock_price again, stock price info will be crawled.

6. run python stock.py model, will generate training data, train the model, and then predict next stock price 


