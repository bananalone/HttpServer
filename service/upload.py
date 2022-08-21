import json
import shutil
import sys
from pathlib import Path


def save_file(file, save_to):
    try:
        path = Path(file)
        save_path = Path(save_to) / path.name
        if path.is_file():
            shutil.copy(file, str(save_path))
        else:
            save_path.mkdir()
            for file in path.iterdir():
                shutil.copy(file, save_path / file.name)
        res = {
            'status': 'success',
            'path': str(save_path)
        }
    except Exception as e:
        res = {
            'status': 'fail',
            'path': str(save_path)
        }
    return res


if __name__ == '__main__':
    file, files, save_to = sys.argv[1:]
    res = {
        "file": save_file(file, save_to),
        "files": save_file(files, save_to)
    }
    print(json.dumps(res))
