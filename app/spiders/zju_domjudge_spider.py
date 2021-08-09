from app.spiders.domjudge_spider import DomjudgeSpider
from app.config.accounts import zju_domjudge_accounts


class ZjuDomjudgeSpider(DomjudgeSpider):
    oj_name = 'zju-domjudge'
    base_url = 'http://acm.zju.edu.cn/domjudge'
    accounts = zju_domjudge_accounts
