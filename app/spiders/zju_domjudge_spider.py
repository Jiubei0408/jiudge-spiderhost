from app.spiders.base_spider import BaseSpider


class ZjuDomjudgeSpider(BaseSpider):
    accounts = [
        ('jiubei', 'jiubei'),
        ('test', 'test')
    ]

    oj_name = 'zju-domjudge'
