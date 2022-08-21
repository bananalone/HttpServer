import sys
import json


def sum(nums):
    total = 0
    for num in nums:
        total += float(num)
    result = {'total': total}
    print(json.dumps(result))


if __name__ == '__main__':
    sum(sys.argv[1:])
