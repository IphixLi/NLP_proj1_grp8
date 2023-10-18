import json
import re
import pprint
import collections

f = open("gg2013.json",encoding="utf-8", errors="ignore")
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
            if any(word in split_res[i] for word in ['picture', 'drama', 'film', 'award','movie','comedy','musical']):
                    val=split_res[i]
                    if i<len(split_res)-1 and 'television' in split_res[i+1]:
                         val=val.strip()+' for '+'television'
                    stripped=strip_non_alphabetical(val)

                    words_to_check=['picture', 'drama','award','film', 'movie','comedy','musical']
                    if not any(stripped.lower().strip().endswith(word) for word in words_to_check):
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
    
