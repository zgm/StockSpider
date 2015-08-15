# -*- coding: utf-8 -*-
import scrapy


class ExampleSpider(scrapy.Spider):
    name = "example"
    #allowed_domains = ["example.com"]
    start_urls = (
        'http://xueqiu.com/',
    )

    def parse(self, response):

        print 'success to', response.url, type(response),

        #print type(response), response.url
        #print response
        #print response.body_as_unicode()

        pass
