import json
import re
# import nltk
import collections

f = open("gg2013.json",encoding="utf-8", errors="ignore")
json_text=json.load(f)
line="best foreign language film"

for entry in json_text:
    if line in entry["text"].lower():
        print(entry["text"].encode())



