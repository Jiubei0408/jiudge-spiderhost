from app.spiders.domjudge_spider import DomjudgeSpider


class ZuccDomjudgeSpider(DomjudgeSpider):
    oj_name = 'zucc-domjudge'
    base_url = 'http://domjudge.newitd.com'
    accounts = [('jiubei', 'jiubei')]


if __name__ == '__main__':
    print(ZuccDomjudgeSpider('jiubei', 'jiubei').get_contest_meta(''))
