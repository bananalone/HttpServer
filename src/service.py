from pathlib import Path
import shlex
from string import Template
from typing import List, Union
import subprocess
import uuid
import tempfile
import re

from flask import Flask, request, Response, make_response, send_file


class Command:
    def __init__(self, cmd: str) -> None:
        self.raw_cmd = cmd

    def __call__(self, args: dict, output=None) -> str:
        t = Template(self.raw_cmd)
        for arg in args:
            args[arg] = shlex.quote(args[arg])
        cmd = t.substitute(args)
        p = subprocess.run(cmd, capture_output=True, text=True, shell=True)   
        if output:
            msg = f'command: {cmd}\n' + \
                   'result: ' + (p.stdout.strip() if p.stdout is not None else '') + '\n' + \
                   'error: ' + p.stderr.strip() if p.stderr is not None else ''
            output(msg)
        return p.stdout, p.stderr, p.returncode


class RequestParser:
    def __init__(self, temp_root: Union[str, Path] = None) -> None:
        self.paths: List[Path] = []
        temp_root = temp_root if temp_root else tempfile.gettempdir()
        self.temp_root = Path(temp_root)

    def parse_get_args(self) -> dict:
        params = {}
        if request.method == 'GET':
            params = {**request.args}
        return params

    def parse_post_urlencoded(self) -> dict:
        params = {}
        if request.method == 'POST' and request.headers['Content-Type'] == 'application/x-www-form-urlencoded':
            params = {**request.form}
        return params

    def parse_post_json(self) -> dict:
        params = {}
        if request.method == 'POST' and request.headers['Content-Type'] == 'application/json':
            params = {**request.json}
        return params

    def parse_post_multipart(self) -> dict:
        params = dict()
        if request.method == 'POST' and request.headers['Content-Type'].startswith('multipart/form-data'):
            params = {**request.form}
            files = request.files
            for k in files:
                fs = files.getlist(k)
                if len(fs) == 1:
                    path = Path(self.temp_root) / (str(uuid.uuid1()) + Path(fs[0].filename).suffix)
                    fs[0].save(path)
                else:
                    path = Path(self.temp_root) / str(uuid.uuid1())
                    path.mkdir()
                    for f in fs:
                        f_path = path / (str(uuid.uuid1()) + Path(f.filename).suffix)
                        f.save(f_path)
                params[k] = str(path)
                self.paths.append(path)
        return params

    def clear(self):
        for path in self.paths:
            if path.is_dir():
                for file in path.iterdir():
                    file.unlink()
                path.rmdir()
            else:
                path.unlink()
        self.paths : List[Path] = []


class ResultParser:
    def __init__(self, pattern: Union[str, None]) -> None:
        self.pattern = re.compile(pattern) if pattern else None
        self.map = dict()
        self.map['text'] = self.text
        self.map['json'] = self.json
        self.map['file'] = self.file

    def _parse(self, stdout: str) -> str:
        return '\n'.join(self.pattern.findall(stdout)) if self.pattern else stdout

    def to(self, stdout: str, response: str) -> Response:
        return self.map[response](stdout)

    def text(self, stdout: str) -> Response:
        result = self._parse(stdout)
        return make_response(result)

    def json(self, stdout: str) -> Response:
        result = self._parse(stdout)
        response = make_response(result)
        response.headers['Content-Type'] = 'application/json'
        return response

    def file(self, stdout: str) -> Response:
        result = self._parse(stdout)
        file_path = Path(result).absolute()
        if not file_path.exists():
            raise Exception(f'{file_path} does not exists')
        if not file_path.is_file():
            raise Exception(f'{str(file_path)} is not a file')
        response = make_response(send_file(str(file_path)), 200)
        return response


class Service:
    def __init__(self, app: Flask, temp_root: Union[str, Path] = None) -> None:
        self.flask_app = app
        self.requestParser = RequestParser(temp_root)

    def run(self, port: int):
        self.flask_app.run(port = port)

    def add_rule(self, rule: str, cmd: str, args: Union[str, List[str], None], pattern: str, res: str):
        view_func = self._process_request(cmd, args, pattern, res)
        self.flask_app.add_url_rule('/' + rule, endpoint=rule, view_func=view_func, methods=['GET', 'POST'])

    def add_rules(self, rules: dict):
        for rule in rules:
            self.add_rule(rule, rules[rule]['cmd'], rules[rule]['args'], rules[rule]['pattern'], rules[rule]['response'])

    def _process_request(self, cmd: str, args: Union[str, List[str], None], pattern:str, res: str):
        if args is None:
            args = []
        elif isinstance(args, str):
            args = [args]
        command = Command(cmd)
        resultParser = ResultParser(pattern)
        def view_func():
            parsed_params = {
                **self.requestParser.parse_get_args(),
                **self.requestParser.parse_post_urlencoded(),
                **self.requestParser.parse_post_json(),
                **self.requestParser.parse_post_multipart()
            }
            for arg in args:
                arg_value = parsed_params.get(arg)
                if arg_value is None:
                    self.requestParser.clear()
                    raise Exception(f'{arg} not found')
                parsed_params[arg] = arg_value
            stdout, stderr, retcode = command(parsed_params, self.flask_app.logger.info)
            if retcode != 0:
                raise Exception(f'[subprocess error] {stderr}')
            self.requestParser.clear()
            result = resultParser.to(stdout + '\n\n' + stderr, res)
            return result
        return view_func


if __name__ == '__main__':
    app = Flask(__name__)
    service = Service(app)
    from utils import parse_config
    rules = parse_config('./configs/rules_demo.yaml')
    service.add_rules(rules)
    service.run(8080)
