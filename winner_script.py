import json
import re
import collections

f = open("gg2013.json",encoding="utf-8", errors="ignore")
json_text=json.load(f)
track={}
def strip_non_alphabetical(input_string):
    pattern = r'^[a-zA-Z-\s].*[a-zA-Z-\s]$'

    # Use re.search() to find the matching pattern in the input text
    match = re.search(pattern, input_string)
    
    if match:
        return match.group()
    else:
        return ""
    
def normalize(text):
    pattern = r'^RT @\w+: '
    cleaned_text = re.sub(pattern, '', text)
    
    #remove hashtag
    hash_pattern = r'#\w+'
    
    cleaned_text = re.sub(hash_pattern, '', cleaned_text)

    url_pattern = r'http[s]?://\S+'
    cleaned_text = re.sub(url_pattern, '', cleaned_text)

    at_pattern=r'@\w+'
    cleaned_text = re.sub(at_pattern, '', cleaned_text)
    return cleaned_text.strip().lower()


stop_words=["for"," at", " and"]

punctuation=["?","!",".",","]


for entry in json_text:
    #print(entry['text'].encode('utf-8'))
    #print(normalize(entry['text']).encode('utf-8'))

    normalized_text=normalize(entry['text'])
    if "winner for" in normalized_text:
        nominated_text=normalized_text.split("winner for")
        pattern = r'[?!.,|]'
        split_text = re.split(pattern, nominated_text[1])
        nominated_corpus=split_text[0]

        # Create a regex pattern to split at the specified punctuation marks
        pattern = '|'.join([re.escape(s) for s in stop_words])
        split_res = re.split(pattern, nominated_corpus)

        for i in range(len(split_res)):
            if any(word in split_res[i] for word in ['award']):
                    val=split_res[i]

        else:
            val=split_res[0]

        stripped=strip_non_alphabetical(val)
        if stripped not in track:
                track[stripped]=0
        track[stripped]+=1
                         
sorted_track=sorted(track.items(), key=lambda kv: kv[0], reverse=True)
filtered_data = {key.strip(): value for key, value in sorted_track if len(key.split(" "))>3}
sorted_dict = collections.OrderedDict(filtered_data)

with open('stage/winner_keyword.json', 'w', encoding='utf-8') as f:
    json.dump(sorted_dict, f, ensure_ascii=False, indent=4)
    
