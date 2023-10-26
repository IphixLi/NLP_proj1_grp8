import json
import re
# import nltk
import collections
f = open("gg2013.json",encoding="utf-8", errors="ignore")
json_text=json.load(f)
track={}

d = open("gg2013answers.json",encoding="utf-8", errors="ignore")
award_text=json.load(d)
# for award in award_text["award_data"].keys():
#     print(award)
hint_words=["drama","television","movie","picture","film","award","comedy","musical","song","video"]

def replace_hint_words(text, hint_words):
    for word in hint_words:
        pattern = r'\b({}|{}s)\b'.format(word, word)
        # Replace the matched word with a more specific phrase
        text = re.sub(pattern, f'{word}', text, flags=re.IGNORECASE)
    return text

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

    text=replace_hint_words(text, hint_words)
    return text.lower().strip()

for entry in json_text:
    #print(entry['text'].encode('utf-8'))
    #print(normalize(entry['text']).encode('utf-8'))

    normalized_text=normalize(entry['text'])
    stop_words=['and ', ' to ',' at ', 'goes',' is ', 'like', 'not', 'she ', 'http', 
            'it ','this ', 'my', 'i ']
    
    if 'best' in normalized_text:
        punctuation_pattern = r'[?!.:;|]'
        stop_pattern='|'.join([re.escape(s) for s in stop_words])
        
        split_text = re.split(punctuation_pattern, normalized_text)
        nominated_corpus=split_text[0].strip()
        nominated_corpus=nominated_corpus.split(":")[0]
        
        #print(entry['text'].encode('utf-8'))
        #print()

        # print(nominated_corpus.encode('utf-8'))
        matches = re.split(r'best', nominated_corpus, flags=re.IGNORECASE)

        if len(matches)>1:
            stop_split=re.split(stop_pattern, matches[1])
            val='best '+stop_split[0].strip()
            # val='best'+matches[1]
            val.strip('"').strip()

            split_text=val.split(" ")
            if len(split_text)<4:
                continue

            dash_split=val.split(" -")
            if len(dash_split)>1:
                part1=dash_split[0].strip()
                part2=dash_split[1].strip()
                pattern = '|'.join(map(re.escape, hint_words))
                if len(part1)>0 and len(part2)>0 and re.search(pattern, part2):
                    val=part1+' - '+part2
                elif len(part1)>0:
                    val=part1
                else:
                    val=part2
            
            for_split=val.split("for ")
            val=for_split[0].strip()

            split_text=val.split(" ")
            if 'best' in val and split_text[0]!='best':
                continue
            
            regex = r"supporting (\w+)"
            match_val = re.search(regex, val)
            
            if match_val and 'performance' not in val:
                matched_noun = match_val.group(1)

                # Determine "a" or "an" based on the first letter of the matched noun
                article = "an" if matched_noun[0].lower() in "aeiou" else "a"
                
                val = re.sub(regex, f"performance by {article} {matched_noun} in a supporting role", val)

            regex = r"best (\w+)"
            match_val = re.search(regex, val)
            
            if match_val and any( i in val for i in ['actor','actress'])\
                and 'performance' not in val and 'supporting' not in val:
                
                matched_noun = match_val.group(1)

                # Determine "a" or "an" based on the first letter of the matched noun
                article = "an" if matched_noun[0].lower() in "aeiou" else "a"
                
                val = 'best '+re.sub(regex, f"performance by {article} {matched_noun}", val)
                # print(val)

            
            if 'foreign' in val:
                print(val)

            if any(i in split_text[-1] for i in hint_words):
                if val not in track:
                    track[val]=0
                track[val]+=1
        
            #print(val.encode('utf-8'))
            
sorted_track=sorted(track.items(), key=lambda kv: kv[0], reverse=True)
filtered_data = {key: value for key, value in sorted_track if  'best' in key and "," not in key and  len(key.split(" "))>3}
sorted_dict = collections.OrderedDict(filtered_data)

with open('stage/best_keyword.json', 'w', encoding='utf-8') as f:
    json.dump(sorted_dict, f, ensure_ascii=False, indent=4)
        # if 'best' in nominated_corpus:
        #     print(nominated_corpus.encode('utf-8'))   
    
