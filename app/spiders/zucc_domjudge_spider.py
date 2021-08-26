from app.spiders.domjudge_spider import DomjudgeSpider
from app.config.accounts import zucc_domjudge_accounts


class ZuccDomjudgeSpider(DomjudgeSpider):
    oj_name = 'zucc-domjudge'
    base_url = 'http://domjudge.newitd.com'
    accounts = zucc_domjudge_accounts


if __name__ == '__main__':
    print(ZuccDomjudgeSpider('jiudge1', 'jiudge1').check_login())
