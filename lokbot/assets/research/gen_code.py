import collections
import json

b = json.load(open('advanced.json'), object_pairs_hook=collections.OrderedDict)
result = collections.OrderedDict()
for key, value in b.items():
    current_required_level_json = value[0]
    requirements = [each for each in current_required_level_json['requirements'] if each['type'] != 'academy']
    for each in requirements:
        if each['type'] not in result:
            result[each['type']] = int(each['level'])

print(json.dumps(result))
