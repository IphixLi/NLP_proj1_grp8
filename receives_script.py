import json
import re
import pprint
import collections

f = open("gg2013.json",encoding="utf-8", errors="ignore")
json_text=json.load(f)
track={}
hint_words=["drama","television","music","movie","film","award","comedy","picture","musical","song","video"]

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
    hash_text = re.sub(hash_pattern, '', cleaned_text)
    
    tag_pattern=r'@\w+'
    tag_text = re.sub(tag_pattern, '', hash_text)

    tag_text=tag_text.replace("–","-")

    # non_english_pattern = r'[^a-zA-Z0-9\s-:]'
    # cleaned_text = re.sub(non_english_pattern, '', tag_text)
    pattern = r'\b(tv)\b'

    # Use re.IGNORECASE flag to make the replacement case-insensitive
    text = re.sub(pattern, 'television', tag_text, flags=re.IGNORECASE)

    return text.lower().strip()

stop_words=["for"," at", " the",  " and"]

punctuation=["?","!",".",","]


for entry in json_text:
    #print(entry['text'].encode('utf-8'))
    #print(normalize(entry['text']).encode('utf-8'))

    normalized_text=normalize(entry['text'])
    if "receives" in normalized_text:
        nominated_text=normalized_text.split("receives")
        pattern = r'[?!,|]'
        split_text = re.split(pattern, nominated_text[1])
        nominated_corpus=split_text[0]

        # Create a regex pattern to split at the specified punctuation marks
        pattern = '|'.join([re.escape(s) for s in stop_words])
        split_res = re.split(pattern, nominated_corpus)

        for i in range(len(split_res)):
            if any(word in split_res[i] for word in hint_words):
                    val=split_res[i]
                    if i<len(split_res)-1 and 'television' in split_res[i+1]:
                         val=val.strip()+' for '+'television'
                    stripped=strip_non_alphabetical(val)

                    if not any(stripped.lower().strip().endswith(word) for word in hint_words):
                        continue

                    if stripped not in track:
                        track[stripped]=0
                    track[stripped]+=1
                         
                    print(stripped.encode('latin-1', errors='ignore').decode('unicode_escape').strip())

sorted_track=sorted(track.items(), key=lambda kv: kv[0], reverse=True)
filtered_data = {key.strip(): value for key, value in sorted_track if len(key.split(" "))>3}
sorted_dict = collections.OrderedDict(filtered_data)

with open('stage/receives_keyword.json', 'w', encoding='utf-8') as f:
    json.dump(sorted_dict, f, ensure_ascii=False, indent=4)