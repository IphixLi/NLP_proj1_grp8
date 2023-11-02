import os
import re
import spacy
import json
import time
import datetime

from syntax_analysis import find_persons, find_work_of_art, generate_candidates, get_descendants_precise, get_descendants_idx, get_descendants_greedy
from handle_names import name_cleaning
from data_preprocess import TweetsPreprocessor
from timestamp_cluster import TimestampCluster
from vote import Vote

from gather_result import gather_all

spacy_model = spacy.load("en_core_web_md")

class Presenter:
    def __init__(self, tweets: list, awards: list, base_confidence=1.0, year=2013):
        self.folder = f"presenter_result_{year}"
        self.filename = "presenter_verb.json"
        self.timestamp_cluster = TimestampCluster(load_saved=True)
        self.timestamp_to_award = self.timestamp_cluster.get_timestamp_to_award()
        self.base_confidence = base_confidence
        self.modify_tweet = True
        self.presenter_active_verbs = [
            "announce", "present", "speak"
        ]
        
        self.tweets = tweets
        self.results = {} # for voting
        
        self.awards = awards
        self.keyword_to_awards = self.get_award_keywords(awards)
        self.award_keywords = list(self.keyword_to_awards.keys())
    
    def get_award_keywords(self, awards) -> dict:
        keyword_to_awards = {}
        self.award_to_keywords = {}

        for award in awards:
            spacy_output = spacy_model(award)
            self.award_to_keywords[award] = []
            for token in spacy_output:
                # Check if the token is a stopword, punctuation, or short word
                if token.is_stop or token.is_punct or len(token.text) < 3:
                    continue
                
                # Check if the token's part-of-speech is one of the desired categories
                if token.pos_ in ["ADJ", "NOUN", "ADV", "VERB", "PROPN"] and token.text.lower() != "award":
                    keyword = token.text.lower()
                    self.award_to_keywords[award].append(keyword)
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
        print(f"- Saved extracted tweets in {self.folder}/{self.filename}")
    
    def load_extracted_tweets(self) -> list:
        self.tweets = json.load(open(f"{self.folder}/{self.filename}"))
        return self.tweets
    
    def extract_tweets(self):
        start_time = time.time()
        for i, tweet in enumerate(self.tweets):
            if i % 10000 == 0:
                print(f"Processing tweet {i}, elapsed time: {time.time() - start_time}")
            self.presenter_verb_extract(tweet)
    
    def extract_or_load(self, debug=False):
        print(f"---------- Extracting tweets for presenters ----------")
        if debug and os.path.exists(f"{self.folder}/{self.filename}"):
            print("- Loading extracted tweets...")
            self.load_extracted_tweets()
        else:
            print("- Extracting tweets...")
            self.extract_tweets()
            self.save_extracted_tweets()
        print(f"---------- Extracting tweets for presenters finished ----------\n")
    
    def do_vote(self):
        print(f"---------- Voting for presenters ----------")
        for tweet in self.tweets:
            if 'candidates' not in tweet:
                continue
            for candidate in tweet['candidates']:
                confidence = candidate['confidence']
                award = candidate['award']
                if confidence < 0:
                    continue
                if award not in self.results:
                    self.results[award] = {}
                for name in candidate['name']:
                    if name not in self.results[award]:
                        self.results[award][name] = confidence
                    else:
                        self.results[award][name] += confidence
        
        for award in self.results:
            self.results[award] = sorted(self.results[award].items(), key=lambda x: x[1], reverse=True)[:15]
        self.results = {award: self.results[award] for award in self.timestamp_to_award.values() if award in self.results}
        self.save_vote_results()
        print(f"---------- Voting for presenters finished ----------\n")
        
    def save_vote_results(self):
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
        with open(f"{self.folder}/voteres_{self.filename}", "w") as f:
            json.dump(self.tweets, f, indent=4)
        print(f"- Saved voting information for each tweet in voteres_{self.filename}")
        
        with open(f"{self.folder}/vote_{self.filename}", "w") as f:
            json.dump(self.results, f, indent=4)
        print(f"- Saved voting results in vote_{self.filename}")
    
    def load_vote_results(self) -> dict:
        # return self.results
        with open(f"{self.folder}/vote_{self.filename}") as f:
            return json.load(f)
                
    def presenter_verb_extract(self, tweet: dict):
        if self.match_presenter_verb_pattern(tweet['new_text']):
            self.presenter_verb_based_match(tweet)
        else:
            confidence_ratio = self.match_presenter_looks_pattern(tweet['new_text']) * self.base_confidence
            if confidence_ratio > 0:
                self.presenter_looks_based_match(tweet, confidence_ratio)
                

    def match_presenter_looks_pattern(self, text: str) -> float:
        patterns = [
            r"\b(look(|s|in|ing))\b", # must be sb looks sth
        ]
        
        unwanted_patterns = [
            r"\b(look(|s|in|ing) (like|crazy|amused|impressed|confused|at))\b",
        ]
        
        # Check each pattern against the text
        for pattern in unwanted_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return 0.0
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                look_index = text.lower().find("look")
                # this shouldn't happen
                if look_index == -1:
                    return 0.0
                else:
                    return 0.5
        return 0.0

    def match_presenter_verb_pattern(self, text: str) -> bool:
        # List of verb-based patterns
        patterns = [
            r"\b(anounce(|s)|(is|are|'re) announcing)\b",
            r"\b(present(|s)|presenter(|s)|presentation(|s)|presenting)\b",
            r'\b(is|are) speaking\b',
            r'\bon stage\b',
            r'\bfinishing .*speech\b',
            r'\bmicrophone\b',
            r'(are|is) (funny|hilarious)', # low confidence
        ]
        unwanted_patterns = [
            r"\b(not|am|is|are|isn't|aren't) present\b", # try to make sure present is a verb here
            r"\bpresent\."
            r"\bpresent\?"
        ]
        
        # Check each pattern against the text
        for pattern in unwanted_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
            
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def presenter_looks_based_match(self, tweet: dict, low_confidence_ratio: float):
        spacy_output = spacy_model(tweet['new_text'])
        
        persons = [
            name_cleaning(p.text).lower()
            for p in find_persons(spacy_output)
            if p.root.head.lemma_ == "look" and 
               p.root.i < p.root.head.i and 
               p.root.head.pos_ == "VERB"
        ]
        if not persons:
            return
        
        # constraints = award_keywords in tweets
        keyword_constraints = []
        for token in spacy_output:
            if token.text.lower() in self.award_keywords and not token.text.lower() in keyword_constraints:
                keyword_constraints.append(token.text.lower())
        tweet['keyword_constraints'] = keyword_constraints
        
        # find possible awards based on the keywords
        possible_awards = set(self.awards)
        if keyword_constraints:
            for keyword in keyword_constraints:
                possible_awards = possible_awards.intersection(self.keyword_to_awards[keyword])
        tweet['possible_awards'] = list(possible_awards)
        if not possible_awards:
            return
        
        # guess the possible award based on the timestamp
        award = ""
        if len(possible_awards) > 1:
            award, confidence = self.timestamp_cluster.categorize_timestamp_after(tweet['timestamp_ms'], possible_awards)
            tweet['possible_candidates'] = (award, confidence * low_confidence_ratio)
            if not award:
                return
        else:
            award = list(possible_awards)[0]
            confidence = low_confidence_ratio
        
        for name in persons:
            candidate = {
                "name": [name],
                "award": award,
                "confidence": self.base_confidence * confidence,
            }
            tweet["candidates"] = tweet.get("candidates", []) + [candidate]
        

    def presenter_verb_based_match(self, tweet: dict):
        """
        Given a tweet, find the presenter and award
        
        Requires: tweet['new_text'] includes presenter_verb_pattern
        Modifies: tweet['candidates']
        """
        spacy_output = spacy_model(tweet['new_text'])
            
        persons = [name_cleaning(p.text).lower() for p in find_persons(spacy_output)]
        
        if not persons:
            return
        
        if re.match(r"present.* together", tweet['new_text'], re.IGNORECASE):
            more_confidence = 3.0
        elif "funny" in tweet['new_text'].lower() or "hilarious" in tweet['new_text'].lower():
            more_confidence = 0.2
        else:
            more_confidence = 1.0
            
        # constraints = award_keywords in tweets
        keyword_constraints = []
        for token in spacy_output:
            if token.text.lower() in self.award_keywords and not token.text.lower() in keyword_constraints:
                keyword_constraints.append(token.text.lower())
        tweet['keyword_constraints'] = keyword_constraints
        
        # find possible awards based on the keywords
        possible_awards = set(self.awards)
        if keyword_constraints:
            for keyword in keyword_constraints:
                possible_awards = possible_awards.intersection(self.keyword_to_awards[keyword])
        tweet['possible_awards'] = list(possible_awards)
        if not possible_awards:
            return
        
        # guess the possible award based on the timestamp
        award = ""
        if len(possible_awards) > 1:
            award, confidence = self.timestamp_cluster.categorize_timestamp_after(tweet['timestamp_ms'], possible_awards)
            tweet['possible_candidates'] = (award, confidence)
            if not award:
                return
        else:
            award = list(possible_awards)[0]
            confidence = 1.0 # will be multiplied by base_confidence later
        
        # increase confidence if the tweet contains most keywords of that award
        award_keyword_set = set(self.award_to_keywords[award])
        ratio = len(set(keyword_constraints).intersection(award_keyword_set)) / len(award_keyword_set)
        if len(keyword_constraints) > 1:
            confidence *= max(6 * ratio, len(keyword_constraints))
            if len(possible_awards) == 1:
                confidence *= 3
        
        for name in persons:
            candidate = {
                "name": [name],
                "award": award,
                "confidence": self.base_confidence * confidence * more_confidence,
            }
            tweet["candidates"] = tweet.get("candidates", []) + [candidate]

if __name__ == '__main__':
    tp = TweetsPreprocessor()
    tp.load_all_tweets(debug=True)
    normal_tweets = tp.load_tweets(key='normal_tweets')
    
    awards = json.load(open("gg2013answers.json"))['award_data'].keys()
    
    win_extractor = Presenter(normal_tweets, awards)
    win_extractor.extract_or_load(debug=False) # TODO: True is for debugging
    
    win_extractor.do_vote()
    
    gather_all(2013, presenter_on=True, winner_on=False, nominee_on=False, host_on=False)
    
    # print(json.dumps(keyword_to_awards, indent=4))
    
    
    # if not os.path.exists(folder):
        
    #     start_time = time.time()
    #     for i, tweet in enumerate(normal_tweets):
    #         if i % 10000 == 0:
    #             print(f"Processing tweet {i}, elapsed time: {time.time() - start_time}")
    #         presenter_verb_extract(tweet)
        
    
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
    #         award_data["presenter"][0][0],
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
    