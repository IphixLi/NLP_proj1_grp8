import os
import re
import spacy
import json
import time

from syntax_analysis import find_persons
from data_preprocess import TweetsPreprocessor
from handle_names import name_cleaning

spacy_model = spacy.load("en_core_web_sm")

class Host:
    def __init__(self, tweets: list, base_confidence=1.0, year=2013):
        self.tweets = tweets
        self.base_confidence = base_confidence
        self.folder = f"host_result_{year}"
        self.filename = "host_keyword.json"
        self.results = {} # for voting
    
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
            self.host_keyword_extract(tweet)
    
    def extract_or_load(self, debug=False):
        print(f"---------- Extracting tweets for hosts ----------")
        if debug and os.path.exists(f"{self.folder}/{self.filename}"):
            print("- Loading extracted tweets...")
            self.load_extracted_tweets()
        else:
            print("- Extracting tweets...")
            self.extract_tweets()
            self.save_extracted_tweets()
        print(f"---------- Extracting tweets for hosts finished ----------\n")
    
    def do_vote(self):
        print(f"---------- Voting for hosts ----------")
        for tweet in self.tweets:
            if 'candidates' not in tweet:
                continue
            for candidate in tweet['candidates']:
                confidence = candidate['confidence']
                if confidence < 0:
                    continue
                for name in candidate['name']:
                    if name not in self.results:
                        self.results[name] = confidence
                    else:
                        self.results[name] += confidence
        
        self.results = sorted(self.results.items(), key=lambda x: x[1], reverse=True)[:10]
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
    
    def host_keyword_extract(self, tweet: dict):
        if self.match_host_keyword_pattern(tweet['new_text']):
            self.host_keyword_based_match(tweet)
        
    def match_host_keyword_pattern(self, text: str) -> bool:
        patterns = [
            r'\b(host|hosting|hosted|hosts)\b',
        ]
        
        # Check each pattern against the text
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def host_keyword_based_match(self, tweet: dict):
        spacy_output = spacy_model(tweet['new_text'])
        
        host_index = []
        for token in spacy_output:
            if "host" in token.text.lower():
                host_index.append(token.i)
                
        if not host_index:
            return
        
        person_name_and_dist = [(
            name_cleaning(p.text).lower(), 
            min([abs(p.root.i - i) for i in host_index]),
        ) for p in find_persons(spacy_output)]
        
        if not person_name_and_dist:
            return
        
        for name, distance in person_name_and_dist:
            candidate = {
                "name": [name],
                "confidence": self.base_confidence * (1 - distance / len(spacy_output)),
            }
            tweet["candidates"] = tweet.get("candidates", []) + [candidate]
            
if __name__ == '__main__':
    tp = TweetsPreprocessor()
    tp.load_all_tweets(debug=True)
    normal_tweets = tp.load_tweets(key='normal_tweets')
    
    host_extractor = Host(normal_tweets)
    host_extractor.extract_or_load(debug=False)
    host_extractor.do_vote()
    
    