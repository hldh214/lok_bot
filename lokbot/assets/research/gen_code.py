import collections
import json

code_start = 30103001

b = json.load(open('advanced.json'), object_pairs_hook=collections.OrderedDict)
result = collections.OrderedDict()
for key, value in b.items():
    print(f"'{key}': {code_start},")
    code_start += 1
