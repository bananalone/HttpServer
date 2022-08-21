import sys
from pathlib import Path


if __name__ == '__main__':
    file = Path.cwd() / 'assets' / sys.argv[1]
    print(str(file))
