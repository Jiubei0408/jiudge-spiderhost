from app.spiders.base_spider import BaseSpider


class TestSpider(BaseSpider):
    accounts = [(i, i) for i in range(3)]
    oj_name = 'test'
