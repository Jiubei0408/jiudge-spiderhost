import json
import re
import time

from app.spiders.base_spider import BaseSpider
from app.config.accounts import cf_accounts


class CodeforcesSpider(BaseSpider):
    oj_name = 'codeforces'
    accounts = cf_accounts
    base_url = 'https://codeforces.com'

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
            time.sleep(1)
        print(self.oj_name + ' login failed: ' + self.username)
        raise Exception(json.dumps({
            'type': 'login error',
            'req_text': res.text,
            'login_req_text': login_res
        }))

    def get_contest_meta(self, contest_id):
        pass

    def submit_problem(self, problem_id, code, lang, submission_id):
        code = self._add_submission_id_to_code(code, lang, submission_id)
        self.check_login()
        problem_type = 'contest'
        if problem_id.startswith('gym-'):
            problem_type = 'gym'
            problem_id = problem_id[4:]
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
        time.sleep(1)
        resp = self.http.post(url=url, data=data)
        if len(resp.history) == 0:
            raise Exception('submit failed')
        while True:
            time.sleep(1)
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
        url = self.base_url + f'/api/user.status?handle={self.username}&count=1'
        resp = self.http.get(url=url).json()
        submission = resp['result'][0]
        submission_id = submission['id']
        if 'verdict' not in submission or submission['verdict'] == 'TESTING':
            return False, data
        verdict = submission['verdict']
        data['result'] = self.change_judge_result(verdict)
        data['remote_result'] = verdict
        if data['result'] != 'AC':
            data['remote_result'] = f'''{verdict} on test {submission['passedTestCount'] + 1}'''
        compile_info = self.get_compiler_info(submission_id)
        data['time_used'] = submission['timeConsumedMillis']
        data['memory_used'] = submission['memoryConsumedBytes'] / 1024
        if compile_info != '':
            data['compile_info'] = compile_info
        return True, data

    def get_compiler_info(self, submission_id):
        self.check_login()
        url = self.base_url + '/data/judgeProtocol'
        resp = self.http.get(url=self.base_url + '/problemset/status?my=on')
        csrf = self._get_csrf_token(resp.text)
        data = {
            'submissionId': submission_id,
            'csrf_token': csrf
        }
        return self.http.post(url=url, data=data).text.strip('"')

    def change_judge_result(self, result: str):
        result = result.upper()
        dic = {
            'OK': 'AC',
            'COMPILATION_ERROR': 'CE',
            'TIME_LIMIT_EXCEEDED': 'TLE',
            'MEMORY_LIMIT_EXCEEDED': 'MLE',
            'RUNTIME_ERROR': 'RE',
            'WRONG_ANSWER': 'WA'
        }
        if result in dic:
            return dic[result]
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
    def _add_submission_id_to_code(code, lang, submission_id):
        if lang in ['GNU G++14 6.4.0', 'GNU G++17 7.3.0', 'GNU G++17 9.2.0 (64 bit)']:
            return f'//jiudge: {submission_id}\n' + code
        elif lang == 'Python 3.8.10':
            return f'# jiudge: {submission_id}\n' + code
        elif lang == 'java 11.0.6':
            return f'//jiudge: {submission_id}\n' + code

    @staticmethod
    def _get_csrf_token(text):
        return re.findall(r'csrf=\'(.+?)\'', text)[0]
