import base64
import json
import re
import time

from bs4 import BeautifulSoup

from app.config.accounts import poj_accounts
from app.spiders.base_spider import BaseSpider


class PojSpider(BaseSpider):
    oj_name = 'poj'
    accounts = poj_accounts
    base_url = 'http://poj.org'

    def login(self):
        url = self.base_url + '/login'
        data = {
            'user_id1': self.username,
            'password1': self.password,
            'B1': 'login',
            'url': '.'
        }
        resp = self.http.post(url=url, data=data)
        print('login poj:' + self.username)
        return {
            'resp_text': resp.text,
            'data': data
        }

    def check_login(self):
        cnt = 0
        while cnt < 10:
            resp = self.http.get(url=self.base_url)
            if f'userstatus?user_id={self.username}' in resp.text:
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
        code = self._add_submission_id_to_code(code, lang, submission_id)
        url = self.base_url + '/submit'
        data = {
            'problem_id': problem_id,
            'language': self._get_lang_id(lang),
            'source': base64.encodebytes(code.encode()),
            'submit': 'Submit',
            'encoded': 1
        }
        resp = self.http.post(url=url, data=data)
        soup = BeautifulSoup(resp.text, 'lxml')
        if 'Error Occurred' in resp.text:
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
        url = self.base_url + f'/status?user_id={self.username}'
        resp = self.http.get(url=url)
        soup = BeautifulSoup(resp.text, 'lxml')
        submission = soup.select('tr.in')[0].parent.find_all('tr')[1]
        tds = submission.find_all('td')
        submission_id = tds[0].text
        verdict = tds[3].text
        if verdict == 'Running & Judging':
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
        url = self.base_url + f'//showcompileinfo?solution_id={submission_id}'
        resp = self.http.get(url=url)
        soup = BeautifulSoup(resp.text, 'lxml')
        e = soup.find('pre')
        if e:
            return e.text
        else:
            return ''

    @staticmethod
    def _add_submission_id_to_code(code, lang, submission_id):
        if lang == 'G++':
            return f'//jiudge: {submission_id}\n' + code
        elif lang == 'Java':
            return f'//jiudge: {submission_id}\n' + code
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

    def change_judge_result(self, result):
        dic = {
            'Accepted': 'AC',
            'Presentation Error': 'PE',
            'Time Limit Exceeded': 'TLE',
            'Memory Limit Exceeded': 'MLE',
            'Wrong Answer': 'WA',
            'Runtime Error': 'RE',
            'Compile Error': 'CE',
            'Output Limit Exceeded': 'RE'
        }
        if result in dic:
            return dic[result]
        return 'UNKNOWN'

    def get_problem_info(self, problem_id):
        url = self.base_url + f'/problem?id={problem_id}'
        resp = self.http.get(url=url)
        soup = BeautifulSoup(resp.text, 'lxml')
        st = soup.select_one('.ptt').parent
        st = [i for i in st.contents if i != '\n'][1:-2]
        problem_text = ''.join([str(e) for e in st[2:]])
        problem_name = st[0].text
        limits = st[1].find_all('td')
        time_limit = float(re.findall(r'[0-9.]+', limits[0].text)[0]) / 1000
        space_limit = float(re.findall(r'[0-9.]+', limits[2].text)[0])
        allowed_lang = ['G++', 'Java']
        return {
            'remote_problem_url': url,
            'problem_name': problem_name,
            'time_limit': time_limit,
            'space_limit': space_limit,
            'problem_text': problem_text,
            'allowed_lang': allowed_lang
        }
