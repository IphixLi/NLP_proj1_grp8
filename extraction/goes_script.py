import json
import re
import pprint
import collections

f = open("../gg2013.json",encoding="utf-8", errors="ignore")
json_text=json.load(f)
track={}
def strip_non_alphabetical(input_string):
    # Remove non-alphabetical characters from the start
    start_stripped = input_string.lstrip('0123456789!@#$%^&*()_+-=[]{}|;:,.<>?/"\\\' ')

    # Remove non-alphabetical characters from the end
    end_stripped = start_stripped.rstrip('0123456789!@#$%^&*()_+-=[]{}|;:,.<>?/"\\\' ')

    return end_stripped
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
    if "goes to" in normalized_text:
        nominated_text=normalized_text.split("goes to")

        # Create a regex pattern to split at the specified punctuation marks
        pattern = '|'.join([re.escape(s) for s in stop_words])
        split_res = re.split(pattern, nominated_text[0])

        for i in range(len(split_res)):
            stop_pattern='|'.join([re.escape(s) for s in stop_words])
            if any(word in split_res[i] for word in ['picture', 'drama', 'film', 'movie','comedy','musical']):
                    val=split_res[i]
                    if i<len(split_res)-1 and 'television' in split_res[i+1]:
                         val=val.strip()+' for '+'television'
                    stripped=strip_non_alphabetical(val)
                    if stripped not in track:
                        track[stripped]=0
                    track[stripped]+=1
                         
                    print(stripped.encode('latin-1', errors='ignore').decode('unicode_escape').strip())

sorted_track=sorted(track.items(), key=lambda kv: kv[0], reverse=True)
filtered_data = {key.strip(): value for key, value in sorted_track if value > 2 and 'best' in key and len(key.split(" "))>3}
sorted_dict = collections.OrderedDict(filtered_data)

with open('../stage/goes_keyword.json', 'w', encoding='utf-8') as f:
    json.dump(sorted_dict, f, ensure_ascii=False, indent=4)
    
