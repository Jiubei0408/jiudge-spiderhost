from app.spiders.domjudge_spider import DomjudgeSpider


class ZjuDomjudgeSpider(DomjudgeSpider):
    oj_name = 'zju-domjudge'
    base_url = 'http://acm.zju.edu.cn/domjudge'
    accounts = [
        ('team-701', 'hxcvqh'),
        ('team-702', 'harbmn'),
        ('team-703', 'b9wh6b'),
        ('team-704', 'zc7uvf'),
        ('team-705', 'qsgm99'),
        ('team-706', 'br4zzz'),
        ('team-707', 'cpc6de'),
        ('team-708', 'mzxjzw'),
        ('team-709', '7jy54a'),
        ('team-710', 'srdja8'),
        ('team-711', '6ygyht'),
        ('team-712', '5ra988'),
        ('team-713', 'f83gqh'),
        ('team-714', 'jj3we6'),
        ('team-715', '2kmqmv')
    ]


if __name__ == '__main__':
    print(ZjuDomjudgeSpider('team-702', 'harbmn').get_contest_meta(''))
