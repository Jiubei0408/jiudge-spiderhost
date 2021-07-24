import importlib
import time
from threading import Thread
from app.libs.quest_queue import queue
from app.config.settings import *


class SpiderThread(Thread):
    def __init__(self, spider, **kwargs):
        super().__init__(**kwargs)
        self.spider = spider
        self.keys = [f'quest_queue_{spider.oj_name}', f'quest_queue_{spider.oj_name}:{spider.username}']

    def run(self) -> None:
        while True:
            task = queue.blpop(self.keys)[1]
            # todo: 分析crawl任务
            time.sleep(.5)
            print(self.spider.username, self.spider.password, task)


class SpiderPool:
    def __init__(self):
        self.pool = {}
        url = SERVER_URL + '/v1/oj'
        import requests
        resp = requests.get(url).json()
        for oj in resp['data']:
            self.init_spider(oj['name'])

    def init_spider(self, oj_name):
        spider_class = self.get_spider_class(oj_name)
        self.pool[oj_name] = []
        for username, password in spider_class.accounts:
            thread = SpiderThread(spider_class(username, password))
            self.pool[oj_name].append(thread)
            thread.start()

    @staticmethod
    def get_spider_class(oj_name: str):
        module_name = 'app.spiders.' + oj_name.lower().replace('-', '_') + '_spider'
        module = importlib.import_module(module_name)
        spider_name = ''.join([i.capitalize() for i in oj_name.split('-')]) + 'Spider'
        return getattr(module, spider_name)
