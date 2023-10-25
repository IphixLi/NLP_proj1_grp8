import json
import re
# import nltk
import collections

f = open("yifan/tweets/normal_tweets.json",encoding="utf-8", errors="ignore")
json_text=json.load(f)
line="cecil b. demille award"

for entry in json_text:
    if line in entry["new_text"].lower():
        print(entry["new_text"].encode())



