import json
import nltk
import re
from nltk.corpus import stopwords

nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')


stop = stopwords.words('english')
namesdic={}
f = open("gg2013.json",encoding="utf-8", errors="ignore")
json_text=json.load(f)

def ie_preprocess(document):
	document = ' '.join([i for i in document.split() if i not in stop])
	sentences = nltk.sent_tokenize(document)
	sentences = [nltk.word_tokenize(sent) for sent in sentences]
	sentences = [nltk.pos_tag(sent) for sent in sentences]
	return sentences

for entry in json_text:
	res=ie_preprocess(entry["text"])
	print(res)
