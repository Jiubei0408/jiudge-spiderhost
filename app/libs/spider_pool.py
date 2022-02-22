import importlib
import time
from threading import Thread
from app.libs.quest_queue import queue
from app.config.settings import *
from app.libs.http import Http
import json
from app.spiders.base_spider import BaseSpider


class SpiderThread(Thread):
    def __init__(self, spider: BaseSpider, **kwargs):
        super().__init__(**kwargs)
        self.http = Http()
        self.spider = spider
        self.keys = [f'quest_queue_{spider.oj_name}', f'quest_queue_{spider.oj_name}:{spider.username}']

    def do_submit(self, task):
        try:
            problem_id = task['remote_problem_id']
            code = task['code']
            lang = task['lang']
            if 'remote_contest_id' in task:
                res = self.spider.submit_contest_problem(task['remote_contest_id'], problem_id, code, lang)
            else:
                res = self.spider.submit_problem(problem_id, code, lang, task['submission_id'])
        except Exception as e:
            self.http.post(url=f'{SERVER_URL}/spider/judge_result/{task["submission_id"]}', json={
                'quest_id': task['quest_id'],
                'token': task['token'],
                'data': {
                    'result': 'SpiderError'
                }
            })
            raise e
        self.http.post(url=f'{SERVER_URL}/spider/judge_result/{task["submission_id"]}', json={
            'quest_id': task['quest_id'],
            'token': task['token'],
            'data': res
        })

    def do_crawl_contest_meta(self, task):
        res = self.spider.get_contest_meta(task['remote_contest_id'])
        self.http.post(url=f'{SERVER_URL}/spider/contest_meta/{task["contest_id"]}', json={
            'quest_id': task['quest_id'],
            'token': task['token'],
            'data': {
                'oj_id': task['oj_id'],
                'problem_list': res
            }
        })

    def resolve_task(self, task):
        if task['type'] == 'submit':
            self.do_submit(task)
        if task['type'] == 'crawl_contest_info':
            self.do_crawl_contest_meta(task)

    def run(self) -> None:
        while True:
            try:
                task = json.loads(queue.blpop(self.keys)[1])
            except:
                print('task resolve failed')
                continue
            print(self.spider.username, self.spider.password, task)
            try:
                self.resolve_task(task)
            except Exception as e:
                self.http.post(url=SERVER_URL + '/spider/failed', json={
                    'quest_id': task['quest_id'],
                    'token': task['token'],
                    'data': {
                        'message': str(e)
                    }
                })


class SpiderPool:
    def __init__(self):
        self.pool = {}
        url = SERVER_URL + '/oj'
        import requests
        resp = requests.get(url).json()
        for oj in resp['data']:
            self.init_spider(oj['name'])

    def init_spider(self, oj_name):
        try:
            spider_class = self.get_spider_class(oj_name)
        except:
            print(f'Can\'t find {oj_name} spider')
        self.pool[oj_name] = []
        for username, password in spider_class.accounts:
            thread = SpiderThread(spider_class(username, password))
            self.pool[oj_name].append(thread)
            thread.start()
            time.sleep(.5)

    @staticmethod
    def get_spider_class(oj_name: str):
        module_name = 'app.spiders.' + oj_name.lower().replace('-', '_') + '_spider'
        module = importlib.import_module(module_name)
        spider_name = ''.join([i.capitalize() for i in oj_name.split('-')]) + 'Spider'
        return getattr(module, spider_name)
