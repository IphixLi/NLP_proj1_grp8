import json
import re
from . import common


def winner_script(json_text):
    track={}
    for entry in json_text:
        #print(entry['text'].encode('utf-8'))
        #print(normalize(entry['text']).encode('utf-8'))

        normalized_text=common.normalize(entry['text'])
        if "winner for" in normalized_text:
            nominated_text=normalized_text.split("winner for")
            pattern = r'[?!.|]'
            split_text = re.split(pattern, nominated_text[1])
            nominated_corpus=split_text[0]

            # Create a regex pattern to split at the specified punctuation marks
            pattern = '|'.join([re.escape(s) for s in common.stop_words])
            split_res = re.split(pattern, nominated_corpus)

            for i in range(len(split_res)):
                stop_pattern='|'.join([re.escape(s) for s in common.stop_words])

                if any(word in split_res[i] for word in common.hint_words):
                        val=split_res[i]
                        if i<len(split_res)-1 and 'television' in split_res[i+1]:
                            val=val.strip()+' for '+'television'
                        stripped=common.strip_non_alphabetical(val)
                        stripped=stripped.strip("-").strip()

                        if not any(stripped.lower().strip().endswith(word) for word in common.hint_words):
                            continue
                        

                        split_text=stripped.split(" ")
                        if 'best' in stripped and split_text[0]!='best':
                            continue

                        regex = r"supporting (\w+)"
                        match_val = re.search(regex, stripped)

                        if match_val and 'performance' not in stripped:
                            matched_noun = match_val.group(1)

                            # Determine "a" or "an" based on the first letter of the matched noun
                            article = "an" if matched_noun[0].lower() in "aeiou" else "a"
                            
                            stripped = re.sub(regex, f"performance by {article} {matched_noun} in a supporting role", val)

                        regex = r"best (\w+)"
                        match_val = re.search(regex, stripped)
                        if match_val and any( i in stripped for i in ['actor','actress'])\
                            and 'performance' not in stripped and 'supporting' not in stripped:
                            matched_noun = match_val.group(1)

                            # Determine "a" or "an" based on the first letter of the matched noun
                            article = "an" if matched_noun[0].lower() in "aeiou" else "a"
                            
                            stripped = 'best '+re.sub(regex, f"performance by {article} {matched_noun}", stripped)
                            # print(stripped)

                        pattern=["movie television","television movie"]

                        for i in pattern:
                            if i in stripped:
                                stripped=stripped.replace(i, 'motion picture made for television')

                        pattern = r'by\s(.*?)\s(?:actor|actress)'

                        # Find the match
                        match = re.search(pattern, stripped)

                        if match:
                            words_between_by_and_role = match.group(1)
                            
                            # Check if there are characters between "by" and the role
                            if words_between_by_and_role.strip() and words_between_by_and_role.strip()!='an' and words_between_by_and_role.strip()!='a':
                                # Replace the words between "by" and the role with "an {role} in"
                                stripped = re.sub(pattern, r'by an \1 in', stripped)

                               
                        stripped=stripped.replace("--","-")
                        if stripped not in track:
                            track[stripped]=0
                        track[stripped]+=1
    sorted_track=sorted(track.items(), key=lambda kv: kv[0], reverse=True)
    filtered_data = {key.strip(): value for key, value in sorted_track if 'best' in key and "," not in key and len(key.split(" "))>3}

    with open('stage/winner_keyword.json', 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=4)
    return filtered_data

if __name__ == '__main__':
    f = open("gg2013.json",encoding="utf-8", errors="ignore")
    json_text=json.load(f)
    res=winner_script(json_text)
    print(res)
    f.close()

        
        