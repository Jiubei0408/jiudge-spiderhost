from app.spiders.domjudge_spider import DomjudgeSpider


class ZjuDomjudgeSpider(DomjudgeSpider):
    oj_name = 'zju-domjudge'
    base_url = 'http://acm.zju.edu.cn/domjudge'
    accounts = []


if __name__ == '__main__':
    print(ZjuDomjudgeSpider('team-702', 'harbmn').get_contest_meta(''))
