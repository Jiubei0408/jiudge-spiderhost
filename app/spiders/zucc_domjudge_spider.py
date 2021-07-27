from app.spiders.domjudge_spider import DomjudgeSpider


class ZuccDomjudgeSpider(DomjudgeSpider):
    oj_name = 'zucc-domjudge'
    base_url = 'http://domjudge.newitd.com'
    accounts = [
        ('jiudge1', 'jiudge1'),
        ('jiudge2', 'jiudge2'),
        ('jiudge3', 'jiudge3'),
        ('jiudge4', 'jiudge4'),
        ('jiudge5', 'jiudge5')
    ]


if __name__ == '__main__':
    print(ZuccDomjudgeSpider('jiudge1', 'jiudge1').check_login())
