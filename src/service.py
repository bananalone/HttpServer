from pathlib import Path
from string import Template
from typing import List, Union
import os
import uuid
import tempfile

from flask import Flask, request, Response, make_response, send_file


class Command:
    def __init__(self, cmd: str) -> None:
        self.raw_cmd = cmd

    def __call__(self, args: dict) -> str:
        t = Template(self.raw_cmd)
        cmd = t.substitute(args)
        with os.popen(cmd) as p:
            result = p.read().strip()
        return result


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
    def __init__(self, result: str) -> None:
        self.result = result
        self._NO_RESULT = 'No Result'
        self.map = dict()
        self.map['text'] = self.text
        self.map['json'] = self.json
        self.map['file'] = self.file

    def to(self, format: str) -> Response:
        return self.map[format]()

    def text(self) -> Response:
        if not self._success():
            raise Exception(self._NO_RESULT)
        return make_response(self.result, 200)

    def json(self) -> Response:
        if not self._success():
            raise Exception(self._NO_RESULT)
        response = make_response(self.result, 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    def file(self) -> Response:
        if not self._success():
            raise Exception(self._NO_RESULT)
        file_path = Path(self.result).absolute()
        if not file_path.exists() or not file_path.is_file():
            raise Exception(self._NO_RESULT)
        response = make_response(send_file(str(file_path)), 200)
        return response

    def _success(self) -> bool:
        return True if self.result != '' else False


class Service:
    def __init__(self, app: Flask, temp_root: Union[str, Path] = None) -> None:
        self.flask_app = app
        self.requestParser = RequestParser(temp_root)

    def run(self, port: int):
        self.flask_app.run(port = port)

    def add_rule(self, rule: str, cmd: str, args: Union[str, List[str], None], ret: str):
        view_func = self._process_request(cmd, args, ret)
        self.flask_app.add_url_rule('/' + rule, endpoint=rule, view_func=view_func, methods=['GET', 'POST'])

    def add_rules(self, rules: dict):
        for rule in rules:
            self.add_rule(rule, rules[rule]['cmd'], rules[rule]['args'], rules[rule]['return'])

    def _process_request(self, cmd: str, args: Union[str, List[str], None], ret: str):
        if args is None:
            args = []
        elif isinstance(args, str):
            args = [args]
        command = Command(cmd)
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
            result = command(parsed_params)
            self.requestParser.clear()
            result = ResultParser(result)
            return result.to(ret)
        return view_func


if __name__ == '__main__':
    app = Flask(__name__)
    service = Service(app)
    from utils import parse_config
    rules = parse_config('./configs/rules_demo.yaml')
    service.add_rules(rules)
    service.run(8080)
