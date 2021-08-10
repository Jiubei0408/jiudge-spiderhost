import base64
import json
import re
import time

from bs4 import BeautifulSoup

from app.spiders.base_spider import BaseSpider


class DomjudgeSpider(BaseSpider):
    accounts = []

    oj_name = 'domjudge'

    base_url = ''

    def login(self):
        url = self.base_url + '/login'
        res = self.http.get(url=url, noprint=True)
        if len(res.history) > 0:
            return
        soup = BeautifulSoup(res.text, 'lxml')
        csrf_token = soup.find('input', attrs={'name': '_csrf_token'})['value']
        data = {
            '_csrf_token': csrf_token,
            '_username': self.username,
            '_password': self.password
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
            url = self.base_url + '/team'
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
        self.check_login()
        self.switch_contest(contest_id)
        url = self.base_url + '/team/problems'
        res = self.http.get(url=url)
        soup = BeautifulSoup(res.text, 'lxml')
        problem_cards = soup.find_all('div', class_='card')
        problems = []
        main_page = self.http.get(url=self.base_url + '/team')
        main_soup = BeautifulSoup(main_page.text, 'lxml')
        for card in problem_cards:
            if card.text == '':
                continue
            problem_name = card.find('h4').text.strip()
            remote_problem_id = main_soup.find('th', title=f'problem {problem_name}').text.strip()
            problem_pdf_url = None
            links = card.find_all('a')
            for link in links:
                href = link['href']
                if '/problems/' in href:
                    p = re.findall('/problems/(.*)/text', href)[0]
                    problem_pdf_url = self.base_url + f'/team/problems/{p}/text'
            problem_pdf = ''
            if problem_pdf_url:
                problem_pdf = self.http.get(url=problem_pdf_url).content
                problem_pdf = base64.b64encode(problem_pdf).decode('utf-8')
            limits = card.find('h5').text
            limits = limits.replace('\n', '').replace(' ', '')
            try:
                timelimit = float(re.findall(r'(\d+\.?\d*)second', limits)[0])
            except:
                timelimit = -1
            try:
                spacelimit = float(re.findall(r'(\d+\.?\d*)MB', limits)[0]) * 1024
            except:
                spacelimit = -1
            problems.append({
                'problem_name': problem_name,
                'remote_problem_id': remote_problem_id,
                'remote_problem_url': '',
                'problem_text': '',
                'problem_text_url': '',
                'problem_text_file': problem_pdf,
                'time_limit': timelimit,
                'space_limit': spacelimit,
                'allowed_lang': ['c', 'cpp', 'java', 'py3']
            })
        return problems

    def submit_contest_problem(self, contest_id, problem_id, code, lang):
        self.check_login()
        self.switch_contest(contest_id)
        if lang not in ['c', 'cpp', 'java', 'py3']:
            raise Exception('language error')
        from urllib3 import encode_multipart_formdata
        url = self.base_url + '/team/submit'
        res = self.http.get(url=url)
        res = BeautifulSoup(res.text, 'lxml')
        try:
            token = res.find('input', attrs={'id': 'submit_problem__token'})['value']
        except TypeError:
            token = None
        problems = res.find('select', attrs={'id': 'submit_problem_problem'}).find_all('option')
        for i in problems:
            if i.text.startswith(f'{problem_id} -'):
                problem_id = i['value']
        headers = {'Content-Type': 'multipart/form-data'}
        data = {}
        ext = ''
        if lang == 'c':
            ext = 'c'
        if lang == 'cpp':
            ext = 'cpp'
        if lang == 'java':
            ext = 'java'
        if lang == 'py3':
            ext = 'py'
        data['submit_problem[code][]'] = (f'temp.{ext}', code.encode('utf-8'))
        data['submit_problem[language]'] = lang
        data['submit_problem[problem]'] = problem_id
        if token:
            data['submit_problem[_token]'] = token
        form_data = encode_multipart_formdata(data)
        data = form_data[0]
        headers['Content-Type'] = form_data[1]
        res = self.http.post(url=url, headers=headers, data=data)
        if len(res.history) == 0:
            raise Exception('submit failed')
        while True:
            time.sleep(5)
            finished, status = self.get_last_problem_status()
            if finished:
                return status

    def switch_contest(self, contest_cid):
        self.http.get(url=self.base_url + f'/team/change-contest/{contest_cid}')

    def get_last_problem_status(self):
        data = {
            'compile_info': 'There were no compiler errors or warnings.',
            'time_used': -1,
            'memory_used': -1
        }
        url = self.base_url + '/team'
        res = self.http.get(url=url)
        soup = BeautifulSoup(res.text, 'lxml')
        row = soup.find('div', class_='col').find('tbody').find('tr')
        result = row.find_all('a')[-1].text.strip()
        if result == 'pending':
            return False, data
        data['result'] = self.change_judge_result(result)
        data['remote_result'] = result
        if result == 'too-late':
            return True, data
        href = row.find('a')['href']
        sid = re.findall('/submission/(.*)', href)[0]
        url = self.base_url + '/team/submission/' + sid
        res = self.http.get(url=url)
        soup = BeautifulSoup(res.text, 'lxml')
        if soup.find('pre'):
            data['compile_info'] = soup.find('pre').text
        return True, data

    def change_judge_result(self, result: str):
        result = result.upper()
        dic = {
            'CORRECT': 'AC',
            'COMPILER-ERROR': 'CE',
            'TIMELIMIT': 'TLE',
            'RUN-ERROR': 'RE',
            'WRONG-ANSWER': 'WA'
        }
        if result in dic:
            return dic[result]
        return 'UNKNOWN'
