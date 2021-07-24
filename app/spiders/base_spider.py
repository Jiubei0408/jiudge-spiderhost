from app.libs.http import Http


class BaseSpider:
    accounts = []
    oj_name = ''

    def __init__(self, username, password):
        self.spider_http = Http()
        self.username = username
        self.password = password
        self.login()

    def login(self):
        pass

    def check_login(self):
        pass
