import json
import re
import time

from app.spiders.base_spider import BaseSpider
from app.config.accounts import cf_accounts
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from app.libs.http import Http
from binascii import hexlify, unhexlify


class CodeforcesHttp(Http):
    def _end_request(self, res, encoding):
        if 'Redirecting...' not in res.text:
            return res
        return self._set_RCPC(res)

    def _set_RCPC(self, resp):
        res = re.findall('toNumbers\("(.+?)"\)', resp.text)
        text = unhexlify(res[2].encode('utf-8'))
        key = unhexlify(res[0].encode('utf-8'))
        iv = unhexlify(res[1].encode('utf-8'))

        aes = AES.new(key, AES.MODE_CBC, iv)
        res = hexlify(aes.decrypt(text)).decode('utf-8')
        self.sess.cookies.set('RCPC', res, domain='.codeforces.com', path='/')
        url = re.findall('href="(.+?)"', resp.text)[0]
        return self.get(url=url)


class CodeforcesSpider(BaseSpider):
    oj_name = 'codeforces'
    accounts = cf_accounts
    base_url = 'https://codeforces.com'
    http_class = CodeforcesHttp

    def login(self):
        url = self.base_url + '/enter'
        resp = self.http.get(url=url, noprint=True)
        csrf = self._get_csrf_token(resp.text)
        data = {
            'csrf_token': csrf,
            'action': 'enter',
            'handleOrEmail': self.username,
            'password': self.password,
            '_tta': 176,
            'remember': 'on'
        }
        resp = self.http.post(url=url, data=data)
        print('login:' + self.username)
        return {
            'resp_text': resp.text,
            'data': data
        }

    def check_login(self):
        cnt = 0
        while cnt < 10:
            url = self.base_url + '/problemset/customtest'
            res = self.http.get(url=url, noprint=True)
            if len(res.history) == 0:
                return True
            login_res = self.login()
            cnt += 1
        print(self.oj_name + ' login failed: ' + self.username)
        raise Exception(json.dumps({
            'type': 'login error',
            'req_text': res.text,
            'login_req_text': login_res
        }))

    def get_problem_info(self, problem_id):
        contest_id, problem_index = re.findall(r'(.*)([A-Z].*)', problem_id)[0]
        is_gym = False
        if int(contest_id) > 100000:
            is_gym = True
        if is_gym:
            url = self.base_url + f'/gym/{contest_id}/problem/{problem_index}'
        else:
            url = self.base_url + f'/problemset/problem/{contest_id}/{problem_index}'
        html_code = self.http.get(url=url).text
        soup = BeautifulSoup(html_code, 'lxml')
        statement = soup.find('div', class_='problem-statement')
        header = statement.contents[0]
        if is_gym:
            remote_problem_url = url
        else:
            remote_problem_url = url
        problem_name = header.contents[0].text[3:]
        time_limit = float(re.search(r'[0-9.]+', header.contents[1].text)[0])
        space_limit = float(re.search(r'[0-9.]+', header.contents[2].text)[0]) * 1024
        problem_text = '<div class="problem-statement"><div class="section-title">Statement</div>' + \
                       ''.join([str(i) for i in statement.contents[1:]]) + '</div>'
        allowed_lang = ['GNU G++14 6.4.0', 'GNU G++17 7.3.0', 'GNU G++17 9.2.0 (64 bit)',
                        'Python 3.8.10', 'java 11.0.6']
        return {
            'remote_problem_url': remote_problem_url,
            'problem_name': problem_name,
            'time_limit': time_limit,
            'space_limit': space_limit,
            'problem_text': problem_text,
            'allowed_lang': allowed_lang
        }

    def submit_problem(self, problem_id, code, lang, submission_id):
        code = self._add_additional_message_to_code(code, lang, submission_id)
        self.check_login()
        url = self.base_url + '/problemset/submit'
        resp = self.http.get(url=url)
        csrf = self._get_csrf_token(resp.text)
        data = {
            'submittedProblemCode': problem_id,
            'programTypeId': self._get_lang_id(lang),
            'source': code,
            'csrf_token': csrf,
            'action': 'submitSolutionFormSubmitted'
        }
        resp = self.http.post(url=url, data=data)
        if len(resp.history) == 0:
            soup = BeautifulSoup(resp.text, 'lxml')
            error_span = soup.find('span', class_='error for__source')
            if error_span:
                return {
                    'compile_info': error_span.text,
                    'time_used': 0,
                    'memory_used': 0,
                    'result': 'CE',
                    'remote_result': ''
                }
            raise Exception('submit failed')
        while True:
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
        url = self.base_url + f'/problemset/status?my=on'
        resp = self.http.get(url=url)
        soup = BeautifulSoup(resp.text, 'lxml')
        tr = soup.find_all('tr', attrs={'data-submission-id': re.compile(r'\d+')})[0]
        tds = tr.find_all('td')
        submission_id = tds[0].text.strip()
        verdict = tds[5].text.strip()
        if verdict.startswith('Running') or verdict.startswith('In queue'):
            return False, data
        result = self.change_judge_result(verdict)
        data['result'] = result
        data['remote_result'] = verdict
        compile_info = self.get_compiler_info(submission_id)
        data['time_used'] = int(re.findall(r'\d+', tds[-2].text)[0])
        data['memory_used'] = int(re.findall(r'\d+', tds[-1].text)[0])
        if compile_info != '':
            data['compile_info'] = compile_info
        return True, data

    def get_compiler_info(self, submission_id):
        url = self.base_url + '/data/judgeProtocol'
        resp = self.http.get(url=self.base_url + '/problemset/status?my=on')
        csrf = self._get_csrf_token(resp.text)
        data = {
            'submissionId': submission_id,
            'csrf_token': csrf
        }
        resp = self.http.post(url=url, data=data).json()
        return resp

    def change_judge_result(self, result: str):
        prefix_dic = {
            'Accepted': 'AC',
            'Compilation error': 'CE',
            'Time limit exceeded': 'TLE',
            'Memory limit exceeded': 'MLE',
            'Runtime error': 'RE',
            'Wrong answer': 'WA'
        }
        for prefix, res in prefix_dic.items():
            if result.startswith(prefix):
                return res
        return 'UNKNOWN'

    @staticmethod
    def _get_lang_id(lang):
        dic = {
            'GNU G++14 6.4.0': 50,
            'GNU G++17 7.3.0': 54,
            'GNU G++17 9.2.0 (64 bit)': 61,
            'Python 3.8.10': 31,
            'java 11.0.6': 60
        }
        if lang in dic:
            return dic[lang]
        else:
            raise Exception('unknown language')

    @staticmethod
    def _add_additional_message_to_code(code, lang, submission_id):
        timestamp = int(time.time())
        if lang in ['GNU G++14 6.4.0', 'GNU G++17 7.3.0', 'GNU G++17 9.2.0 (64 bit)']:
            return f'//jiudge: {submission_id}: {timestamp}\n' + code
        elif lang == 'Python 3.8.10':
            return f'# jiudge: {submission_id}: {timestamp}\n' + code
        elif lang == 'java 11.0.6':
            return f'//jiudge: {submission_id}: {timestamp}\n' + code

    @staticmethod
    def _get_csrf_token(text):
        return re.findall(r'csrf=\'(.+?)\'', text)[0]
