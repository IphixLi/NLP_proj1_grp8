import os
import re
import spacy
import json
import time
import datetime

from syntax_analysis import find_persons, find_work_of_art, generate_candidates, get_descendants_precise, get_descendants_idx, get_descendants_greedy
from nominee import match_nominee_verb_pattern
from data_preprocess import TweetsPreprocessor
from vote import Vote

spacy_model = spacy.load("en_core_web_md")

# awards = json.load(open("gg2013answers.json"))['award_data'].keys()

# def get_award_keywords(awards) -> dict:
#     keyword_to_awards = {}

#     for award in awards:
#         spacy_output = spacy_model(award)
#         for token in spacy_output:
#             # Check if the token is a stopword, punctuation, or short word
#             if token.is_stop or token.is_punct or len(token.text) < 3:
#                 continue
            
#             # Check if the token's part-of-speech is one of the desired categories
#             if token.pos_ in ["ADJ", "NOUN", "ADV", "VERB", "PROPN"]:
#                 keyword = token.text.lower()

#                 if keyword not in keyword_to_awards:
#                     keyword_to_awards[keyword] = [award]
#                 else:
#                     keyword_to_awards[keyword].append(award)
#     return keyword_to_awards

# keyword_to_awards = get_award_keywords(awards)
# award_keywords = list(keyword_to_awards.keys())

class Winner:
    def __init__(self, tweets: list, awards: list, base_confidence=1.0):
        self.folder = "winner_result"
        self.filename = "winner_verb.json"
        self.base_confidence = base_confidence
        self.modify_tweet = True
        self.timestamp_on = True
        self.winner_active_verbs = [
            "win", "receive", "get", "take"
        ]
        self.winner_passive_verbs = [
            "awarded", "go"
        ]
        self.tweets = tweets
        
        self.awards = awards
        self.keyword_to_awards = self.get_award_keywords(awards)
        self.award_keywords = list(self.keyword_to_awards.keys())
    
    def get_award_keywords(self, awards) -> dict:
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
    
    def save_extracted_tweets(self):
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
        with open(f"{self.folder}/{self.filename}", 'w') as f:
            json.dump(self.tweets, f, indent=4)
    
    def load_extracted_tweets(self) -> list:
        self.tweets = json.load(open(f"{self.folder}/{self.filename}"))
        return self.tweets
    
    def extract_tweets(self):
        start_time = time.time()
        for i, tweet in enumerate(self.tweets):
            if i % 10000 == 0:
                print(f"Processing tweet {i}, elapsed time: {time.time() - start_time}")
            self.winner_verb_extract(tweet)
    
    def extract_or_load(self, debug=False):
        if debug and os.path.exists(f"{self.folder}/{self.filename}"):
            self.load_extracted_tweets()
        else:
            self.extract_tweets()
            self.save_extracted_tweets()
    
    def do_vote(self):
        v = Vote(self.awards, self.timestamp_on)
        v.vote_for_awards(self.awards, self.tweets, modify_tweet=self.modify_tweet)
        self.results = v.get_results()
        self.make_timestamp_list()
        self.save_vote_results()
        
    def load_timestamp_list(self) -> list:
        self.timestamp_list = json.load(open(f"{self.folder}/timestamp_{self.filename}"))
        return self.timestamp_list
        
    def save_vote_results(self):
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
        with open(f"{self.folder}/voteres_{self.filename}", "w") as f:
            json.dump(self.tweets, f, indent=4)
        
        with open(f"{self.folder}/vote_{self.filename}", "w") as f:
            json.dump(self.results, f, indent=4)
            
        with open(f"{self.folder}/timestamp_{self.filename}", "w") as f:
            json.dump(self.timestamp_list, f, indent=4)
        
    def load_winner(self) -> dict:
        tmp = json.load(open(f"{self.folder}/vote_{self.filename}"))
        results = {
            award: award_data['winner'][0][0] for award, award_data in tmp.items()
        }
        return results
        
    def make_timestamp_list(self):
        timestamp_list = {
            award: (
                award_data["winner"][0][0],
                award_data["timestamp"],
                datetime.datetime.fromtimestamp(award_data["timestamp"]/1000.0).strftime('%Y-%m-%d %H:%M:%S'),
            ) for award, award_data in self.results.items()
        }
        self.timestamp_list = sorted(timestamp_list.items(), key=lambda x: x[1][1])
        
    def winner_verb_extract(self, tweet: dict):
        if self.match_winner_verb_pattern(tweet['new_text']) and not match_nominee_verb_pattern(tweet['new_text']):
            self.winner_verb_based_match(tweet)

    def match_winner_verb_pattern(self, text: str) -> bool:
        # List of verb-based patterns
        patterns = [
            r'\b(wins|won|win|receives|received|receive|gets|got|get)\b',
            r'\b(goes|went) to\b',
            r'\bawarded to\b',
            r'\b(takes|took) home\b'
        ]
        
        # Check each pattern against the text
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def winner_verb_based_match(self, tweet: dict):
        """
        Given a tweet, find the winner and award
        
        Requires: tweet['new_text'] includes winner_verb_pattern
        Modifies: tweet['candidates']
        """
        try:
            spacy_output = spacy_model(tweet['new_text'])
            
            award = []
            winner = []
        
            for sentence in spacy_output.sents:
                root = sentence.root
                if root is None:
                    continue
                
                prev_winner_size, prev_award_size = len(winner), len(award)
                if root.lemma_ in self.winner_active_verbs:
                    for child in root.children:
                        if child.dep_ == "dobj":
                            award += generate_candidates(child, root)
                        elif child.dep_ == "nsubj" or child.dep_ == "nsubjpass":
                            if child.pos_ == "PRON":
                                winner += [p.text for p in find_persons(spacy_output)]
                                winner += [w.text for w in find_work_of_art(spacy_output)]
                            else:
                                winner.append(get_descendants_precise(child))
                # X (is awarded to / goes to) Y
                elif root.lemma_ in self.winner_passive_verbs and sentence[root.i + 1].text == "to":                 
                    for chunk in sentence.noun_chunks:
                        if chunk.root.head == root and (chunk.root.dep_ == "nsubj" or chunk.root.dep_ == "nsubjpass"):
                            award.append(get_descendants_precise(chunk.root))
                        elif chunk.root.dep_ == "pobj" and (chunk.root.head == root or chunk.root.head.text == "to"):
                            if chunk.root.pos_ == "PRON":
                                winner += [p.text for p in find_persons(spacy_output)]
                                winner += [w.text for w in find_work_of_art(spacy_output)]
                            else:
                                idxs = get_descendants_idx(chunk.root)
                                precise = get_descendants_precise(chunk.root)
                                greedy = get_descendants_greedy(chunk.root, idxs, root)
                                winner += list(set([precise, greedy]))
                
                # Add award keywords if syntax check fails
                if len(winner) > prev_winner_size or len(award) > prev_award_size:
                    for token in sentence:
                        if token.text.lower() in self.award_keywords:
                            award.append(token.text.lower())
            
            if winner or award:
                candidates = {
                    "winner_candidates": winner,
                    "award_candidates": award,
                    "base_confidence": self.base_confidence,
                }
            tweet["candidates"] = tweet.get("candidates", []) + [candidates]
        except:
            return

if __name__ == '__main__':
    tp = TweetsPreprocessor()
    tp.load_all_tweets(debug=True)
    normal_tweets = tp.load_tweets(key='normal_tweets')
    
    awards = json.load(open("gg2013answers.json"))['award_data'].keys()
    
    win_extractor = Winner(normal_tweets, awards)
    win_extractor.extract_or_load(debug=True) # TODO: True is for debugging
    
    win_extractor.do_vote()
    
    # print(json.dumps(keyword_to_awards, indent=4))
    
    
    # if not os.path.exists(folder):
        
    #     start_time = time.time()
    #     for i, tweet in enumerate(normal_tweets):
    #         if i % 10000 == 0:
    #             print(f"Processing tweet {i}, elapsed time: {time.time() - start_time}")
    #         winner_verb_extract(tweet)
        
    
    #     all_tweets = normal_tweets
        
    #     with open(f"{folder}/{filename}", 'w') as f:
    #         json.dump(all_tweets, f, indent=4)
    # else:
    #     all_tweets = json.load(open(f"{folder}/{filename}"))
    
    # modify_tweet = True
    # timestamp_on = True
    # v = Vote(awards, timestamp_on)
    # v.vote_for_awards(awards, all_tweets, modify_tweet=modify_tweet)
    # res = v.get_results()
    
    # timestamp_list = {
    #     award: (
    #         award_data["winner"][0][0],
    #         award_data["timestamp"],
    #         datetime.datetime.fromtimestamp(award_data["timestamp"]/1000.0).strftime('%Y-%m-%d %H:%M:%S'),
    #     ) for award, award_data in res.items()
    # }
    # timestamp_list = sorted(timestamp_list.items(), key=lambda x: x[1][1])
    
    # with open(f"{folder}/voteres_{filename}", "w") as f:
    #     json.dump(all_tweets, f, indent=4)
    
    # with open(f"{folder}/vote_{filename}", "w") as f:
    #     json.dump(res, f, indent=4)
        
    # with open(f"{folder}/timestamp_{filename}", "w") as f:
    #     json.dump(timestamp_list, f, indent=4)
    