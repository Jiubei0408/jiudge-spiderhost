from app.libs.http import Http


class BaseSpider:
    accounts = []
    oj_name = ''

    def __init__(self, username, password):
        self.http = Http()
        self.username = username
        self.password = password
        self.login()

    def login(self):
        pass

    def check_login(self):
        pass

    def get_contest_meta(self, contest_id):
        """
        'problem_list': {
            'problem_name': '123', # 题目名
            'remote_problem_id': '1', # 题目id
            'remote_problem_url': 'http://balabala', # 题目链接（可为空）
            'problem_text': '题面文本', # 题面文本（可为空）
            'problem_text_url': 'http://balabala', # 题面链接（可为空）
            'problem_text_file': '', #题面文件base64（可为空）
            'time_limit': 1.5, # 时间限制，单位秒（可为空）
            'space_limit': 1024, # 空间限制，单位KB（可为空）,
            'allowed_lang': [] # 允许提交的语言
        }
        """
        pass

    def get_contest_problem_info(self, contest_id, problem_id):
        pass

    def get_problem_info(self, problem_id):
        pass

    def submit_contest_problem(self, contest_id, problem_id, code, lang):
        pass

    def submit_problem(self, problem_id, code, lang):
        pass

    def change_judge_result(self, result):
        pass
