import json
import re
# import nltk
import collections
from extraction import *

f = open("gg2013.json",encoding="utf-8", errors="ignore")
json_text=json.load(f)
track={}


