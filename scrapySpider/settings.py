# -*- coding: utf-8 -*-

# Scrapy settings for scrapySpider project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#     http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#     http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'scrapySpider'

SPIDER_MODULES = ['scrapySpider.spiders']
NEWSPIDER_MODULE = 'scrapySpider.spiders'


SCHEDULER = "scrapy_redis.scheduler.Scheduler"
SCHEDULER_PERSIST = True
SCHEDULER_IDLE_BEFORE_CLOSE = 10



# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'scrapySpider (+http://www.yourdomain.com)'
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.107 Safari/537.36'


# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS=32

# Configure a delay for requests for the same website (default: 0)
# See http://scrapy.readthedocs.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
#DOWNLOAD_DELAY=3
DOWNLOAD_DELAY = 0.4
DOWNLOAD_TIMEOUT = 3
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN=16
#CONCURRENT_REQUESTS_PER_IP=16
CONCURRENT_REQUESTS = 100
CONCURRENT_REQUESTS_PER_IP = 3


# Disable cookies (enabled by default)
#COOKIES_ENABLED=False
COOKIES_ENABLED=True

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED=False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}


# Enable or disable spider middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    'scrapySpider.middlewares.MyCustomSpiderMiddleware': 543,
#}

# Enable or disable downloader middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    'scrapySpider.middlewares.MyCustomDownloaderMiddleware': 543,
#    'scrapy_crawlera.CrawleraMiddleware': 600
#}

#CRAWLERA_ENABLED = True
#CRAWLERA_USER = '3b464d27244643899b3de5bfebbc03ec'
# 1533ab8deec34348961954468fbf39dc
#CRAWLERA_PASS = ''

# Enable or disable extensions
# See http://scrapy.readthedocs.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    'scrapy.telnet.TelnetConsole': None,
#}

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
#ITEM_PIPELINES = {
#    'scrapySpider.pipelines.SomePipeline': 300,
#}
ITEM_PIPELINES = {
    'scrapySpider.pipelines.ScrapyspiderPipeline': 300,
#    'scrapy_redis.pipelines.RedisPipeline': 400,
    }


# Enable and configure the AutoThrottle extension (disabled by default)
# See http://doc.scrapy.org/en/latest/topics/autothrottle.html
# NOTE: AutoThrottle will honour the standard settings for concurrency and delay
#AUTOTHROTTLE_ENABLED=True
# The initial download delay
#AUTOTHROTTLE_START_DELAY=5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY=60
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG=False

#RETRY_TIMES = 1
RETRY_ENABLED = False


# Enable and configure HTTP caching (disabled by default)
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED=True
#HTTPCACHE_EXPIRATION_SECS=0
#HTTPCACHE_DIR='httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES=[]
#HTTPCACHE_STORAGE='scrapy.extensions.httpcache.FilesystemCacheStorage'

REDIS_URL = 'redis://localhost:6379'
MONGODB_URI = 'mongodb://127.0.0.1:27017/'

#LOG_FILE = './log/ne.log'
#LOG_LEVEL = 'INFO'
