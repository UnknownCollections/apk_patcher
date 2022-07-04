# -*- coding: utf-8 -*-
import re, json
import sys, os

script_name = os.path.basename(__file__)
file_name = sys.argv[-1]
json_mode = False
mode = ""
json_file = {}
vars = []
values = []

def matcher(strings_file: str):
    for line in strings_file:
        line = line.strip()
        matches = re.match(r'^"(.*?)"\s*=\s*"(.*?)";?$', line)

        if matches:
            vars.append(matches.group(1))
            values.append(matches.group(2))
        else:
            pass
    return vars, values

def to_json(vars, values):
    data = {}

    for idx, var in enumerate(vars):

        new_key = {vars[idx]:values[idx]}
        data.update(new_key)

    try:
        with open('Localizable.json', 'w+', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error while writing to JSON: {e}")

def to_strings(json_file):
    try:
        with open('Localizable_converted.strings', 'w+', encoding="utf-8") as f:
            for key, value in json_file.items():
                f.write(f'"{key}" = "{value}";\n')
    except Exception as e:
        print(f"Error while converting JSON to strings file: {e}")


if script_name == file_name:
    while True:
        file_name = input("Enter a filename for your strings/json file: ")

        try:
            if str(file_name).endswith(".strings"):
                strings_file = open(file_name, 'r+', encoding="utf-8").readlines()
                break
            elif str(file_name).endswith(".json"):
                json_mode = True
                json_file = json.loads(open(file_name, 'r+', encoding="utf-8").read())
                break
            else:
                print("Your file is neither a strings/JSON file.")
                pass
        except Exception as e:
            print(f"Error while opening strings file: {e}")
            continue
else:
    try:
        if str(file_name).endswith(".strings"):
            strings_file = open(file_name, 'r+', encoding="utf-8").readlines()
        elif str(file_name).endswith(".json"):
            json_mode = True
            json_file = json.loads(open(file_name, 'r+', encoding="utf-8").read())
        else:
            print("Your file is neither a strings/JSON file.")
            sys.exit(0)
    except Exception as e:
        print(f"Error while opening strings file: {e}")

if json_mode:
    to_strings(json_file)
else:
    matcher(strings_file)
    to_json(vars, values)