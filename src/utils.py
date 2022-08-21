import time
from typing import Union
from pathlib import Path
import logging

import yaml


# log
def set_logging(
    name: str = None,
    format: str = None,
    stream: bool = True,
    stream_level: int = logging.DEBUG,
    file: Union[str, Path] = None,
    file_level: int = logging.INFO
    ):
    assert stream or file, 'Select at least one output mode'
    logger = logging.getLogger(name)
    logger.setLevel(logging.NOTSET) # 取消logger等级，按照handle等级记录日志
    formatter = logging.Formatter(format)
    # stream handler
    if stream:
        streamHandler = logging.StreamHandler()
        streamHandler.setFormatter(formatter)
        streamHandler.setLevel(stream_level)
        logger.addHandler(streamHandler)
    # file handler
    if file:
        file = Path(file)
        if file.is_file():
            if file.exists():
                raise Exception(f'{str(file)} already exists')
            elif not file.parent.exists():
                raise Exception(f'{str(file.parent)} do not exists')
        if file.is_dir():
            if not file.exists():
                raise Exception(f'{str(file)} do not exists')
            file = file / (time.asctime() + '.log')
        fileHandler = logging.FileHandler(str(file), encoding='utf-8')
        fileHandler.setLevel(file_level)
        fileHandler.setFormatter(formatter)
        logger.addHandler(fileHandler)


# config
def parse_config(config: Union[str, Path]):
    with open(str(config), encoding='utf-8') as f:
        conf = yaml.load(f, yaml.Loader)
    return conf

