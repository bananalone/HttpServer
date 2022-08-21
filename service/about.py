from pathlib import Path
import sys


if __name__ == '__main__':
    text = Path(sys.argv[1]).read_text()
    lines = text.splitlines()
    for line in lines:
        print('<p style="white-space:pre">' + line + '</p>')