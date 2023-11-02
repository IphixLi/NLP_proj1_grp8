import json
import spacy
import re
import string

spacy_model = spacy.load("en_core_web_md")

from similarity import compute_similarity
from timestamp_cluster import TimestampCluster
from handle_names import name_cleaning

awards = json.load(open("gg2013answers.json"))['award_data'].keys()

class Vote:
    def __init__(self, awards, timestamp_on=False):
        self.timestamp_on = timestamp_on
        self.awards = awards
        self.keyword_to_awards = self.get_award_keywords()
        self.award_keywords = list(self.keyword_to_awards.keys())
        self.strict_confidence_threshold = 2.0
        self.results = {
            award: {
                'winner': {},
                'nominees': {},
            } for award in awards
        }
        self.timestamp_list = {
            award: {} for award in awards   # candidate: [timestamp_list (in ms)]
        }
        self.score_update = {
            "strict": {
                "get_keyword": 2.0,
                "no_such_keyword": -0.01,
                "miss_keyword": -0.1,
                "other_keyword": -2.0,
            },
            "loose": {
                "get_keyword": 2.0,
                "no_such_keyword": 0.0,
                "miss_keyword": -0.2,
                "other_keyword": -1.0,
            },
        }
        self.inference = {
            "loose": {
                "max_score": 0.0,
                "min_score": -0.5,
                "confidence": 0.5,
            },
            "strict": {
                "max_score": 0.0,
                "min_score": -0.5,
                "confidence": 0.5,
            },
        }
    
    def get_award_keywords(self) -> dict:
        keyword_to_awards = {}

        for award in self.awards:
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
    
    def get_update_key(self, base_confidence=1.0) -> str:
        return "strict" if base_confidence > self.strict_confidence_threshold else "loose"
    
    def substitute_tv(self, text: str) -> str:
        return re.sub(r'\bTV\b', 'television', text, flags=re.IGNORECASE)
    
    def replace_miniseries(self, text: str) -> str:
        def repl(match):
            word = match.group()
            if word.islower():
                return "mini series"
            elif word.istitle():
                return "Mini series"
            elif word.isupper():
                return "MINI SERIES"
            return word

        return re.sub(r'\bminiseries\b', repl, text, flags=re.IGNORECASE)

    def get_candidate_keywords(self, candidate: str) -> list:
        candidate = self.substitute_tv(candidate)
        candidate = self.replace_miniseries(candidate)
        spacy_output = spacy_model(candidate)
        candidate_keywords = []
        for token in spacy_output:
            if not (token.is_stop or token.is_punct or len(token.text) < 3) and token.pos_ in ["ADJ", "NOUN", "ADV", "VERB", "PROPN"]:
                candidate_keywords.append(token.text.lower())
        return candidate_keywords
    
    def similarity_for_awards(self, candidate_keywords: list, base_confidence=1.0) -> dict:
        update_key = self.get_update_key(base_confidence)
        
        award_scores = {award: 0 for award in self.awards}
        for keyword in candidate_keywords:
            if keyword in self.keyword_to_awards:
                for award in self.awards:
                    # candidate keyword is in the award
                    if award in self.keyword_to_awards[keyword]:
                        award_scores[award] += self.score_update[update_key]["get_keyword"] / len(self.keyword_to_awards[keyword])
                    # candidate keyword is not in the award, but in other awards (huge penalty)
                    else:
                        award_scores[award] += self.score_update[update_key]["other_keyword"]                
            else:
                # candidate keyword is not in any award (tiny penalty)
                for award in self.awards:
                    award_scores[award] += self.score_update[update_key]["no_such_keyword"]
        
        for award_keyword in self.award_keywords:
            # award have a keyword not in the candidate keywords (small penalty)
            if award_keyword not in candidate_keywords:
                for award in self.keyword_to_awards[award_keyword]:
                    award_scores[award] += self.score_update[update_key]["miss_keyword"]

        return award_scores

    def award_inference(self, candidate_keywords: list, base_confidence=1.0) -> list:
        possible_awards_list = [self.keyword_to_awards[keyword] for keyword in candidate_keywords if keyword in self.keyword_to_awards]
        if not possible_awards_list:
            return []
        possible_award = set(possible_awards_list[0])
        for lst in possible_awards_list:
            possible_award = possible_award.intersection(lst)
            if not possible_award:
                return []

        if len(possible_award) == 1:
            possible_award = list(possible_award)
            return [(possible_award[0], self.inference[self.get_update_key(base_confidence)]['confidence'])]
        else:
            return []

    def update_score_with_base_confidence(self, res: list, base_confidence=1.0) -> list:
        return [(award, score * base_confidence) for award, score in res]

    def choose_award_to_vote(self, awards: list, award_candidates: list, base_confidence=1.0, tweet=None):
        if not award_candidates or base_confidence <= 0:
            return []
        scores = {}
        # for award in awards:
        #     scores[award] = compute_similarity(award, award_candidates)
        candidate_keywords = list(set([k for candidate in award_candidates for k in self.get_candidate_keywords(candidate)]))
        scores = self.similarity_for_awards(candidate_keywords, base_confidence)
        
        if tweet:
            tweet['similarity_res'] = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        res = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        if res[0][1] < self.inference[self.get_update_key(base_confidence)]['min_score'] or res[0][1] == res[1][1]:
            return []
        elif res[0][1] < self.inference[self.get_update_key(base_confidence)]['max_score']:
            res = self.award_inference(candidate_keywords, base_confidence)
            if tweet:
                tweet['inference_res'] = res
            return self.update_score_with_base_confidence(res, base_confidence)
        else:
            return self.update_score_with_base_confidence([res[0]], base_confidence)
    
    def vote(self, res,  winner_candidates, nominee_candidates, ts_ms=-1):
        # only collect timestamp for winner candidates
        for candidate in winner_candidates:
            candidate = self.base_cleaning(candidate)
            for award, score in res:
                if candidate in self.results[award]['winner']:
                    self.results[award]['winner'][candidate] += score
                else:
                    self.results[award]['winner'][candidate] = score
                if self.timestamp_on and ts_ms > 0:
                    if candidate not in self.timestamp_list[award]:
                        self.timestamp_list[award][candidate] = [ts_ms]
                    else:
                        self.timestamp_list[award][candidate].append(ts_ms)
        
        for candidate in nominee_candidates:
            candidate = self.base_cleaning(candidate)
            for award, score in res:
                if candidate in self.results[award]['nominees']:
                    self.results[award]['nominees'][candidate] += score
                else:
                    self.results[award]['nominees'][candidate] = score
    
    # TODO: delete this function after doing clustering
    def base_cleaning(self, text: str) -> str:
        for_idx = text.find(" for ")
        if for_idx != -1:
            text = text[:for_idx]
        text = name_cleaning(text)
        return text.lower()

    def vote_for_awards(self, awards: list, tweets: list, modify_tweet=False):
        for tweet in tweets:
            if 'candidates' in tweet:
                for candidates in tweet['candidates']:
                    vote_res = self.choose_award_to_vote(awards, candidates['award_candidates'], candidates['base_confidence'], tweet if modify_tweet else None)
                    self.vote(vote_res, candidates.get('winner_candidates', []), candidates.get('nominee_candidates', []), tweet.get('timestamp_ms', -1))
                
    def get_results(self):
        ts_clustuer_data = {}
        for award in self.awards:
            self.results[award]['winner'] = sorted(self.results[award]['winner'].items(), key=lambda x: x[1], reverse=True)[:10]
            self.results[award]['nominees'] = sorted(self.results[award]['nominees'].items(), key=lambda x: x[1], reverse=True)[:20]
            if self.timestamp_on:
                timestamps = self.timestamp_list[award][self.results[award]['winner'][0][0]]
                ts_clustuer_data[award] = timestamps
                # choose the top 4% - 10% of the timestamps, do the average
                timestamps = sorted(timestamps)[
                    max(0, len(timestamps) // 25) : max(2, len(timestamps) // 10)
                ]
                self.results[award]['timestamp'] = sum(timestamps) / len(timestamps)
        if self.timestamp_on:
            # save timestamp cluster data
            TimestampCluster(ts_clustuer_data)
        return self.results

if __name__ == "__main__":
    tweets = json.load(open("nominees.json"))
    
    v = Vote(awards)
    v.vote_for_awards(awards, tweets)
    res = v.get_results()
    
    with open("try_vote_nominees_mixed.json", "w") as f:
        json.dump(res, f, indent=4)
        