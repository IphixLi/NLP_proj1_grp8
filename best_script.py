import json
import re
# import nltk
import collections

f = open("yifan/tweets/normal_tweets.json",encoding="utf-8", errors="ignore")
json_text=json.load(f)
track={}

d = open("gg2013answers.json",encoding="utf-8", errors="ignore")
award_text=json.load(d)
# for award in award_text["award_data"].keys():
#     print(award)

def normalize(text):
    pattern = r'^RT @\w+: '
    cleaned_text = re.sub(pattern, '', text)
    
    #remove hashtag
    hash_pattern = r'#\w+'
    hash_text = re.sub(hash_pattern, '', cleaned_text)
    
    tag_pattern=r'@\w+'
    tag_text = re.sub(tag_pattern, '', hash_text)

    non_english_pattern = r'[^a-zA-Z0-9\s-]'
    cleaned_text = re.sub(non_english_pattern, '', tag_text)
    
    return cleaned_text.strip().lower()

    
hint_words=["drama","television","movie","film","award"]

# store words in quotes"

for entry in json_text:
    #print(entry['text'].encode('utf-8'))
    #print(normalize(entry['text']).encode('utf-8'))

    normalized_text=normalize(entry['new_text'])
    stop_words=['and', ' to',' at', 'goes',' is', 'like', 'not', 'she', 'http', 
            'it','this', 'my', 'i ']
    
    if "best" in normalized_text:
        punctuation_pattern = r'[?!.:;|]'
        stop_pattern='|'.join([re.escape(s) for s in stop_words])
        
        split_text = re.split(punctuation_pattern, normalized_text)
        nominated_corpus=split_text[0].strip()
        # print(nominated_corpus.encode('utf-8'))
        matches = nominated_corpus.split('best')
        if len(matches)>1:
            stop_split=re.split(stop_pattern, matches[1])
            val='best '+stop_split[0].strip()
            # val='best'+matches[1]
            val.strip('"').strip()
            #print(val.encode('utf-8'))

            split_text=val.split(" ")
            if len(split_text)<4:
                continue
            # if ('actress' in val or 'actor' in val) and 'performance' not in val:
            #      continue
            
            # words_to_check=['picture', 'drama', 'film', 'movie','comedy','musical']
            # if not any(val.lower().strip().endswith(word) for word in words_to_check):
            #     continue

            dash_split=val.split("-")

            # if len(dash_split)>1:
            #     if any(word in dash_split[1] for word in ['picture', 'drama', 'film', 'movie','comedy']):
            #             val=dash_split[0].strip()+' - '+dash_split[1].strip()
            #     else:
            #          val=dash_split[0].strip()

            if len(dash_split)>1:
                part1=dash_split[0].strip()
                part2=dash_split[1].strip()

                if len(part1)>0 and len(part2)>0:
                    val=part1+' - '+part2
                elif len(part1)>0:
                    val=part1
                else:
                    val=part2

            for_split=val.split(" for")

                     
            # if len(for_split)>1:
            #     if  'television' in for_split[1]:
            #         val=for_split[0].strip()+' for '+for_split[1].strip()
            #     else:
            #         val=for_split[0].strip()

            val=for_split[0].strip()
            # tv_pattern = r'tv'
            # val=re.sub(tv_pattern, 'television', val)

            # if not any(word in val for word in ['picture','musical','video', 'drama', 'film', 'movie','comedy']):
            #     continue

            if val not in track:
                track[val]=0
            track[val]+=1
            #print(val.encode('utf-8'))
            
sorted_track=sorted(track.items(), key=lambda kv: kv[1], reverse=True)
filtered_data = {key: value for key, value in sorted_track if value > 2 and len(key.split(" "))>3}
sorted_dict = collections.OrderedDict(filtered_data)

with open('stage/best_keyword.json', 'w', encoding='utf-8') as f:
    json.dump(sorted_dict, f, ensure_ascii=False, indent=4)
        # if 'best' in nominated_corpus:
        #     print(nominated_corpus.encode('utf-8'))   
    
