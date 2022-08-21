import argparse
import logging
import json

from flask import Flask

from utils import set_logging, parse_config
from service import Service


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cfg', type=str, required=True, help='path to cfg')
    parser.add_argument('-p', '--port', type=int, default=None, help='port of the http server')
    ### more arguments
    return parser.parse_args()


def main(args):
    cfg = parse_config(args.cfg)
    log: dict = cfg['log']
    server: dict = cfg['server']
    set_logging(
        format=log['format'],
        stream=log['stream'],
        stream_level=log['stream_level'],
        file=log['file'],
        file_level=log['file_level']
    )
    logger = logging.getLogger()
    logger.info(f'Arguments:\n{json.dumps(vars(args), indent=4)}')
    logger.info(f'Config:\n{json.dumps(cfg, indent=4)}')
    app = Flask(__name__)
    app.logger = logger
    serv = Service(app, server.get('temp_root', None))
    rules = parse_config(server['rules'])
    serv.add_rules(rules)
    if args.port:
        serv.run(args.port)
    else:
        serv.run(server['port'])


if __name__ == '__main__':
    args = get_args()
    main(args)
