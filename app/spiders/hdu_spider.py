import json
import re
import time
import base64
from urllib.parse import quote
from bs4 import BeautifulSoup

from app.libs.http import Http
from app.spiders.base_spider import BaseSpider
from app.config.accounts import hdu_accounts


class HduSpider(BaseSpider):
    oj_name = 'hdu'
    accounts = hdu_accounts
    base_url = 'https://acm.hdu.edu.cn'
    http_class = Http

    def login(self):
        url = self.base_url + '/userloginex.php?action=login'
        data = {
            'username': self.username,
            'userpass': self.password,
            'login': 'Sign In'
        }
        self.http.post(url=url, data=data)
        print('login hdu:' + self.username)

    def check_login(self):
        cnt = 0
        while cnt < 10:
            resp = self.http.get(url=self.base_url)
            if f'userstatus.php?user={self.username}' in resp.text:
                return True
            login_res = self.login()
            cnt += 1
            time.sleep(1)
        print(self.oj_name + ' login failed: ' + self.username)
        raise Exception(json.dumps({
            'type': 'login error',
            'req_text': resp.text,
            'login_req_text': login_res
        }))

    def submit_problem(self, problem_id, code, lang, submission_id):
        code = self._add_additional_message_to_code(code, lang, submission_id)
        self.check_login()
        url = self.base_url + '/submit.php?action=submit'
        data = {
            'check': '0',
            '_usercode': base64.encodebytes(quote(code).encode()),
            'problemid': problem_id,
            'language': '0'
        }
        resp = self.http.post(url=url, data=data)
        soup = BeautifulSoup(resp.text, 'lxml')
        if 'ERROR(s) occurred.' in resp.text:
            error = soup.find('li')
            if error:
                return {
                    'compile_info': error.text,
                    'time_used': 0,
                    'memory_used': 0,
                    'result': 'CE',
                    'remote_result': ''
                }

        while True:
            time.sleep(3)
            finished, status = self.get_last_problem_status()
            if finished:
                return status

    def get_last_problem_status(self):
        data = {
            'compile_info': 'There were no compiler errors or warnings.',
            'time_used': -1,
            'memory_used': -1,
            'result': 'PENDING',
            'remote_result': ''
        }
        url = self.base_url + f'/status.php?user=jiudge001'
        resp = self.http.get(url=url)
        soup = BeautifulSoup(resp.text, 'lxml')
        submission = soup.select('.table_text')[0].find_all('tr')[1]
        tds = submission.find_all('td')
        submission_id = tds[0].text
        verdict = tds[2].text
        if verdict in ['Queuing', 'Running']:
            print('test', verdict)
            return False, data
        data['result'] = self.change_judge_result(verdict)
        data['remote_result'] = verdict
        time.sleep(1)
        compile_info = self.get_compiler_info(submission_id)
        time_used = re.findall(r'([0-9]*)', tds[4].text)[0]
        memory_used = re.findall(r'([0-9]*)', tds[5].text)[0]
        data['time_used'] = float(time_used) if time_used else -1
        data['memory_used'] = float(memory_used) if memory_used else -1
        if compile_info != '':
            data['compile_info'] = compile_info
        return True, data

    def get_compiler_info(self, submission_id):
        url = self.base_url + f'/viewerror.php?rid={submission_id}'
        resp = self.http.get(url=url)
        soup = BeautifulSoup(resp.text, 'lxml')
        e = soup.find('pre')
        if e:
            return e.text
        else:
            return ''

    @staticmethod
    def _add_additional_message_to_code(code, lang, submission_id):
        timestamp = int(time.time())
        if lang == 'G++':
            return f'//jiudge: {submission_id}: {timestamp}\n' + code
        elif lang == 'Java':
            return f'//jiudge: {submission_id}: {timestamp}\n' + code
        else:
            raise Exception('unknown language')

    @staticmethod
    def _get_lang_id(lang):
        dic = {
            'G++': 0,
            'Java': 2
        }
        if lang in dic:
            return dic[lang]
        else:
            raise Exception('unknown language')

    def change_judge_result(self, result: str):
        dic = {
            'Accepted': 'AC',
            'Presentation Error': 'PE',
            'Time Limit Exceeded': 'TLE',
            'Memory Limit Exceeded': 'MLE',
            'Wrong Answer': 'WA',
            'Compilation Error': 'CE',
            'Output Limit Exceeded': 'WA'
        }
        if result in dic:
            return dic[result]
        if result.startswith('Runtime Error'):
            return 'RE'
        return 'UNKNOWN'

    def get_problem_info(self, problem_id):
        url = self.base_url + f'/showproblem.php?pid={problem_id}'
        resp = self.http.get(url=url, encoding='gb2312')
        soup = BeautifulSoup(resp.text, 'lxml')
        titles = soup.select('.panel_title')
        contents = soup.select('.panel_content')
        problem_text = ''
        for i, title in enumerate(titles):
            if title.text in ['Source']:
                continue
            problem_text += str(title)
            problem_text += str(contents[i])

        problem_name = soup.find('h1').text
        time_limit = float(re.findall(r'([0-9.]+) MS', resp.text)[0]) / 1000
        space_limit = float(re.findall(r'([0-9.]+) K', resp.text)[0])
        allowed_lang = ['G++', 'Java']
        return {
            'remote_problem_url': url,
            'problem_name': problem_name,
            'time_limit': time_limit,
            'space_limit': space_limit,
            'problem_text': problem_text,
            'allowed_lang': allowed_lang
        }
