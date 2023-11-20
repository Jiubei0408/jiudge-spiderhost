import json
import re
import time
import base64
from urllib.parse import quote
from bs4 import BeautifulSoup

from app.libs.http import Http
from app.spiders.base_spider import BaseSpider
from app.config.accounts import hzcuoj_accounts


class HzcuojSpider(BaseSpider):
    oj_name = 'hzcuoj'
    accounts = hzcuoj_accounts
    base_url = 'https://api.zuccacm.top/zuccoj'
    http_class = Http

    def login(self):
        url = self.base_url + '/user/login'
        data = {
            'username': self.username,
            'password': self.password,
        }
        resp = self.http.post(url=url, data=data).json()
        print('login hzcuoj:' + self.username)
        print(resp)

    def check_login(self):
        cnt = 0
        while cnt < 10:
            resp = self.http.get(url=self.base_url + '/user/get').json()
            print(resp)
            if resp['code'] == 200 and resp['data']['username'] == self.username:
                return True
            login_res = self.login()
            cnt += 1
            time.sleep(1)
        print(self.oj_name + ' login failed: ' + self.username)
        raise Exception(json.dumps({
            'type': 'login error',
            'req_text': resp,
            'login_req_text': login_res
        }))

    def submit_problem(self, problem_id, code, lang, submission_id):
        code = self._add_additional_message_to_code(code, lang, submission_id)
        self.check_login()
        url = self.base_url + '/solution/submit'
        data = {
            'problemId': problem_id,
            'lang': self._get_lang_id(lang),
            'code': code
        }
        resp = self.http.post(url=url, data=data).json()
        if resp['code'] != 200:
            raise Exception(json.dumps({
                'type': 'submit error',
                'req_text': resp,
            }))

        solution_id = resp['data']['solutionId']

        while True:
            time.sleep(3)
            finished, status = self.get_last_problem_status(solution_id)
            if finished:
                return status

    def get_last_problem_status(self, solution_id):
        data = {
            'compile_info': 'There were no compiler errors or warnings.',
            'time_used': -1,
            'memory_used': -1,
            'result': 'PENDING',
            'remote_result': ''
        }
        url = self.base_url + f'/solution/get?solutionId={solution_id}'
        resp = self.http.get(url=url).json()
        if resp['code'] != 200:
            return False, data
        jud_data = resp['data']
        if jud_data['result'] == -1:  # Pending
            return False, data
        data['remote_result'] = self._get_result(jud_data['result'])
        data['result'] = self.change_judge_result(data['remote_result'])
        data['memory_used'] = jud_data['memoryUsed']
        data['time_used'] = jud_data['timeUsed']
        data['compile_info'] = jud_data['remark']
        return True, data

    @staticmethod
    def _add_additional_message_to_code(code, lang, submission_id):
        timestamp = int(time.time())
        if lang in ['C', 'C++']:
            return f'//jiudge: {submission_id}: {timestamp}\n' + code
        else:
            raise Exception('unknown language')

    @staticmethod
    def _get_lang_id(lang):
        dic = {
            'C': 1,
            'C++': 2,
            # 'Java': 3
        }
        if lang in dic:
            return dic[lang]
        else:
            raise Exception('unknown language')

    @staticmethod
    def _get_result(result: int):
        dic = {
            1: 'Compile Error',
            2: 'Time Limit Exceed',
            3: 'Memory Limit Exceed',
            4: 'Output Limit Exceed',
            5: 'Runtime Error',
            6: 'Wrong Answer',
            7: 'Accepted',
            8: 'Presentation Error',
            9: 'System Error'
        }
        if result in dic:
            return dic[result]
        return 'UNKNOWN'

    def change_judge_result(self, result: str):
        dic = {
            'Compile Error': 'CE',
            'Time Limit Exceed': 'TLE',
            'Memory Limit Exceed': 'MLE',
            'Output Limit Exceed': 'OLE',
            'Runtime Error': 'RE',
            'Wrong Answer': 'WA',
            'Accepted': 'AC',
            'Presentation Error': 'PE',
            'System Error': 'SE'
        }
        if result in dic:
            return dic[result]
        return 'UNKNOWN'

    def get_problem_info(self, problem_id):
        url = self.base_url + f'/problem/display?problemId={problem_id}'
        resp = self.http.get(url=url).json()['data']
        problem_name = resp['title']
        time_limit = float(resp['timeLimit']) / 1000
        space_limit = resp['memoryLimit']

        problem_text = f'<div class="problem-statement"><div class="section-title">Statement</div><div>{self.change_html(resp["description"])}</div>'
        problem_text += f'<div class="input-specification"><div class="section-title">Input</div>{self.change_html(resp["input"])}</div>'
        problem_text += f'<div class="output-specification"><div class="section-title">Output</div>{self.change_html(resp["output"])}</div>'
        samples = json.loads(resp['samples'])
        problem_text += '<div class="sample-tests"><div class="section-title">Example</div>'
        for sample in samples:
            problem_text += f'''
                <div class="sample-test">
                <div class="input">
                    <div class="title">Input</div>
                    <pre>\n{sample['input']}\n</pre>
                </div>
                <div class="output">
                    <div class="title">Output</div>
                    <pre>\n{sample['output']}\n</pre>
                </div>
            </div>
            '''
        problem_text += '</div>'
        if len(resp['hint']) > 0:
            problem_text += f'<div class="note"><div class="section-title">Note</div>{self.change_html(resp["hint"])}</div>'
        problem_text += '</div>'

        # print(problem_text)
        allowed_lang = ['C', 'C++']
        return {
            'remote_problem_url': f'https://zuccoj.zuccacm.top/#/problem/{problem_id}/description',
            'problem_name': problem_name,
            'time_limit': time_limit,
            'space_limit': space_limit,
            'problem_text': problem_text,
            'allowed_lang': allowed_lang
        }

    def change_html(self, html: str):
        if 'href' in html:
            return f'<p>{html}</p>'
        res = html.split('\n')
        s = ''
        for i in res:
            i = i.replace('<', '$<$')
            i = i.replace('>', '$>$')
            i = i.replace('&', '$&$')
            s += f'<p>{i}</p>'
        return s
