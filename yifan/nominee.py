import re
import time
import json
import spacy

from syntax_analysis import find_verbs, find_persons, find_work_of_art, generate_candidates, get_descendants_precise, get_descendants_idx, get_descendants_greedy
from data_preprocess import TweetsPreprocessor
from vote import Vote

spacy_model = spacy.load("en_core_web_md")

awards = json.load(open("gg2013answers.json"))['award_data'].keys()

def get_award_keywords(awards) -> dict:
    keyword_to_awards = {}

    for award in awards:
        spacy_output = spacy_model(award)
        for token in spacy_output:
            # Check if the token is a stopword, punctuation, or short word
            if token.is_stop or token.is_punct or len(token.text) < 3:
                continue
            
            # Check if the token's part-of-speech is one of the desired categories
            if token.pos_ in ["ADJ", "NOUN", "ADV", "VERB", "PROPN"]:
                keyword = token.text.lower()

                if keyword not in keyword_to_awards:
                    keyword_to_awards[keyword] = [award]
                else:
                    keyword_to_awards[keyword].append(award)
    
    return keyword_to_awards

keyword_to_awards = get_award_keywords(awards)
award_keywords = list(keyword_to_awards.keys())

def remove_words_after_for(text: str) -> str:
    if isinstance(text, str):
        text = text.lower()
        for_idx = text.find(" for ")
        if for_idx == -1:
            return text
        return text[:for_idx].strip()
    else:
        return text

def subtract_30_seconds(timestamp_ms: int) -> int:
    return timestamp_ms - 30000

timestamp_list = json.load(open("winner_result/timestamp_winner_verb.json"))
timestamp_to_award = {
    subtract_30_seconds(lst[1][1]): lst[0] for lst in timestamp_list
}
award_to_winner = {
    lst[0]: remove_words_after_for(lst[1][0]) for lst in timestamp_list
}

guess_verbs = [
    "guess", "bet", "hope", "think", "predict", "expect", "wish"
]
nominee_active_verbs = [
    "win", "receive", "get", "take", "rob"
]
nominee_passive_verbs = [
    "awarded", "go"
]

def nominee_verb_extract(tweet: dict, base_confidence=1.0):
    if match_nominee_verb_pattern(tweet['new_text']):
        nominee_verb_based_match(tweet, base_confidence)

def match_nominee_verb_pattern(text: str) -> bool:
    # List of verb-based patterns
    patterns = [
        r'\b(nominated for)\b',
        r'\b((should|would) have (won|received|got|taken home|gone to|been awarded to))\b',
        r'\b((should|will) (win|receive|get|take home|go to|be awarded to))\b',
        r'I (wish|hope|guess|think|bet|predict|expect) .*(wins|win|receives|receive|gets|get|goes to|go to|awarded to|take(s) home)\b',
        r'\b((was|is|got|get) robbed)\b',
    ]
    
    # Check each pattern against the text
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def match_nominee_keyword_pattern(text: str) -> bool:
    # List of verb-based patterns
    patterns = [
        r'\b(nominee|nominees|nominated|nomination)\b',
    ]
    
    # Check each pattern against the text
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def nominee_ts_based_award_predict(tweet: dict, spacy_output, base_confidence=1.0) -> (str, float):
    if "robbed" not in tweet['new_text'].lower():
        return None, None
    
    keyword_constraints = []
    for token in spacy_output:
        if token.text.lower() in award_keywords:
            keyword_constraints.append(token.text.lower())
    
    possible_awards = set(awards)
    if keyword_constraints:
        for keyword in keyword_constraints:
            possible_awards = possible_awards.intersection(keyword_to_awards[keyword])
    
    if not possible_awards:
        return None, None
    
    possible_timestamps = [t for t in timestamp_to_award.keys() if t < tweet['timestamp_ms'] and timestamp_to_award[t] in possible_awards]
    max_timestamp = max(possible_timestamps) if possible_timestamps else -1
    
    if max_timestamp == -1:
        return None, None
    else:
        return timestamp_to_award[max_timestamp], base_confidence

def nominee_verb_based_match(tweet: dict, base_confidence=1.0):
    """
    Given a tweet, find the nominee and award
    
    Requires: tweet['new_text'] includes nominee_verb_pattern
    Modifies: tweet['candidates']
    """
    try:
        spacy_output = spacy_model(tweet['new_text'])
        
        award = []
        nominee = []
        
        for sentence in spacy_output.sents:
            root = sentence.root
            if root is None:
                continue
            
            prev_nominee_size, prev_award_size = len(nominee), len(award)
            # Y (should / will) win X / Y is nominated for X / Y gets robbed
            verb_list = find_verbs(sentence)
            for verb in verb_list:
                root = verb
                if root.lemma_ in nominee_active_verbs:
                    for child in root.children:
                        if child.dep_ == "dobj":
                            award += generate_candidates(child, root)
                        elif child.dep_ == "nsubj" or child.dep_ == "nsubjpass":
                            if child.pos_ == "PRON":
                                nominee += [p.text for p in find_persons(spacy_output)]
                                nominee += [w.text for w in find_work_of_art(spacy_output)]
                            else:
                                nominee.append(get_descendants_precise(child))                    
                # X (is awarded to / goes to) Y
                elif root.lemma_ in nominee_passive_verbs and sentence[root.i + 1].text == "to":                 
                    for chunk in sentence.noun_chunks:
                        if chunk.root.head == root and (chunk.root.dep_ == "nsubj" or chunk.root.dep_ == "nsubjpass"):
                            award.append(get_descendants_precise(chunk.root))
                        elif chunk.root.dep_ == "pobj" and (chunk.root.head == root or chunk.root.head.text == "to"):
                            if chunk.root.pos_ == "PRON":
                                nominee += [p.text for p in find_persons(spacy_output)]
                                nominee += [w.text for w in find_work_of_art(spacy_output)]
                            else:
                                idxs = get_descendants_idx(chunk.root)
                                precise = get_descendants_precise(chunk.root)
                                greedy = get_descendants_greedy(chunk.root, idxs, root)
                                nominee += list(set([precise, greedy]))

                if len(nominee) > prev_nominee_size or len(award) > prev_award_size:
                    for token in sentence:
                        if token.text.lower() in award_keywords:
                            award.append(token.text.lower())
                if len(nominee) > prev_nominee_size or len(award) > prev_award_size:
                    nominee += [p.text for p in find_persons(spacy_output)]
                    nominee += [w.text for w in find_work_of_art(spacy_output)]
        
        if nominee:
            predict_award, confidence = nominee_ts_based_award_predict(tweet, spacy_output, base_confidence)
            if predict_award:
                award.append(predict_award)
                base_confidence = confidence
        if nominee or award:
            candidates = {
                "nominee_candidates": nominee,
                "award_candidates": award,
                "base_confidence": base_confidence,
            }
            tweet["candidates"] = tweet.get("candidates", []) + [candidates]
        
    except Exception as e:
        print(e)

if __name__ == '__main__':
    folder = "nominee_result"
    filename = "nominee_verb.json"
    
    tp = TweetsPreprocessor()
    tp.load_all_tweets()
    
    normal_tweets = tp.load_tweets(key='normal_tweets') + tp.load_tweets(key='guess_tweets') + tp.load_tweets(key='I_tweets')
    start_time = time.time()
    for i, tweet in enumerate(normal_tweets):
        if i % 10000 == 0:
            print(f"Processing tweet {i}, elapsed time: {time.time() - start_time}")
        nominee_verb_extract(tweet)
        
    
    all_tweets = normal_tweets
    
    with open(f"{folder}/{filename}", 'w') as f:
        json.dump(all_tweets, f, indent=4)
    
    modify_tweet = True
    v = Vote(awards)
    v.vote_for_awards(awards, all_tweets, modify_tweet=modify_tweet)
    res = v.get_results()
    
    with open(f"{folder}/voteres_{filename}", "w") as f:
        json.dump(all_tweets, f, indent=4)
    
    with open(f"{folder}/vote_{filename}", "w") as f:
        json.dump(res, f, indent=4)
        