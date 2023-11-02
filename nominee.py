import re
import time
import json
import spacy
import os

from syntax_analysis import find_verbs, find_persons, find_work_of_art, generate_candidates, get_descendants_precise, get_descendants_idx, get_descendants_greedy, is_human_pronoun
from data_preprocess import TweetsPreprocessor
from vote import Vote
from wiki import WikiSearch
from timestamp_cluster import TimestampCluster
from handle_names import WinnerNameMatcher, about_human, get_job, name_cleaning

from gather_result import gather_all

spacy_model = spacy.load("en_core_web_md")


class Nominee:
    def __init__(self, tweets: list, awards: list, year=2013, base_confidence=1.0):
        self.folder = f"nominee_result_{year}"
        self.filename = "nominee_verb.json"
        self.year = year
        self.base_confidence = base_confidence
        self.tweets = tweets
        
        self.modify_tweet = True
        
        self.wiki = WikiSearch()
        self.winner_to_award = self.load_winner_results()
        if self.winner_to_award is None:
            print("Error: winner results not found")
            return
        
        self.winner_matcher = WinnerNameMatcher(self.winner_to_award)
        self.timestamp_cluster = TimestampCluster(load_saved=True)

        self.guess_verbs = [
            "guess", "bet", "hope", "think", "predict", "expect", "wish"
        ]
        self.nominee_active_verbs = [
            "win", "receive", "get", "take", "rob"
        ]
        self.nominee_passive_verbs = [
            "awarded", "go"
        ]
        self.nominee_ts_verbs = [
            "win", "receive", "get", "take", "rob", "be"
        ]

        self.awards = awards
        self.keyword_to_awards = self.get_award_keywords(self.awards)
        self.award_keywords = list(self.keyword_to_awards.keys())
    
    def load_winner_results(self) -> dict:
        winner_result_folder = f"winner_result_{self.year}"
        winner_vote_file = "winner_result.json"
        winner_file = f"{winner_result_folder}/{winner_vote_file}"
        try:
            return {winner: award.lower() for award, winner in json.load(open(winner_file)).items()}
        except:
            print(f"Error: {winner_file} not found")

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
        del keyword_to_awards['award']
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
            self.nominee_extract(tweet)
        
    
    def extract_or_load(self, debug=False):
        print(f"---------- Extracting tweets for nominees ----------")
        if debug and os.path.exists(f"{self.folder}/{self.filename}"):
            print("- Loading extracted tweets...")
            self.load_extracted_tweets()
        else:
            print("- Extracting tweets...")
            self.extract_tweets()
            self.save_extracted_tweets()
        print(f"---------- Extracting tweets for nominees finished ----------\n")
    
    def do_vote(self):
        print(f"---------- Voting for nominees ----------")
        v = Vote(self.awards)
        v.vote_for_awards(self.awards, self.tweets, modify_tweet=self.modify_tweet)
        self.results = v.get_results()
        self.save_vote_results()
        print(f"---------- Voting for nominees finished ----------\n")
    
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

    def nominee_extract(self, tweet: dict):
        if self.match_nominee_verb_pattern(tweet['new_text']):
            self.nominee_verb_based_match(tweet, self.base_confidence)
        if self.match_nominee_ts_pattern(tweet['new_text']):
            self.nominee_ts_based_match(tweet, self.base_confidence)
        self.nominee_winner_based_match(tweet, self.base_confidence)

    def match_nominee_verb_pattern(self, text: str) -> bool:
        # List of verb-based patterns
        patterns = [
            r'\b(nominated for)\b',
            r'\b((should|shld|would) have|should\'ve|shld\'ve|would\'ve) (won|received|got|taken home|gone to|been awarded to|been\b(?!.*\bnominated\b))\b',
            r'\b(should|shld|will) (win|receive|get|take home|go to|be awarded to)\b',
            r'I (wish|hope|guess|think|bet|predict|expect) .*(wins|win|receives|receive|gets|get|goes to|go to|awarded to|take(s) home)\b',
            r'(want|wanted) .* to (win|receive|get|go to|be awarded to|take home|be\b(?!.*\bnominated\b))\b',
            r'(would like|hoping) .* (wins|win|receives|receive|gets|get|goes to|go to|awarded to|take(|s) home)\b',
            r'\b((was|is|got|get) robbed)\b',
        ]
        
        # Check each pattern against the text
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def match_nominee_ts_pattern(self, text: str) -> bool:
        patterns = [
            r'\b((was|is|got|get) (just|)robbed)\b',
            r'(want|wanted) .* to (win|receive|get|go to|be awarded to|take home|be\b(?!.*\bnominated\b))\b',
            r'\b((should|shld) have|should\'ve|shld\'ve) .*(won|gotten|taken|been\b(?!.*\bnominated\b))\b',
            r'\bwould win\b',
        ]
        
        # Check each pattern against the text
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
        

    def nominee_winner_based_match(self, tweet: dict, base_confidence=1.0):
        winner_match_list = self.winner_matcher.get_winner_from_text(tweet['new_text'])
        if not winner_match_list:
            return
        
        # match all patterns about comparison
        patterns = [
            r'\b(steal|stole|stolen)\b',
            r'\b(beat|beats|beat out|beats out|beating|beating out)\b',
            r'\b(defeat|defeats|defeated|defeating)\b',
            r'\bbetter than\b',
            r'\b(but congrats to)\b',
            r'\blost .*to\b',
            r'\bvs.\b',
            r'\bor\b',
            r'\bbut\b',
        ]
        worse_pattern_idx_list = [-1, -2]
        all_matches = []
        for index, pattern in enumerate(patterns):
            for match in re.finditer(pattern, tweet["new_text"], flags=re.IGNORECASE):
                all_matches.append((index, match))
        if not all_matches:
            return
        
        # use spacy to find person's names and work of art's names
        spacy_output = tweet.get('spacy_output', spacy_model(tweet['new_text']))
        persons = find_persons(spacy_output)
        works = find_work_of_art(spacy_output)
        
        # iterate through all winner name matches
        for winner_match in winner_match_list:
            cur_confidence = base_confidence * winner_match['confidence']
            winner = winner_match['winner']
            winner_idx = winner_match['start_idx']
            
            award = self.winner_to_award[winner]
            is_human = about_human(award)
            
            award_keyword_in_tweet = []
            for token in spacy_output:
                if token.text.lower() in self.award_keywords and not token.text.lower() in award_keyword_in_tweet:
                    award_keyword_in_tweet.append(token.text.lower())
            num_common_keyword = sum([1 for keyword in award_keyword_in_tweet if keyword in award.lower()])
            ratio = num_common_keyword / len(award_keyword_in_tweet) if len(award_keyword_in_tweet) > 0 else 0
            if ratio < 1 and ratio != 0:
                cur_confidence *= ratio
            elif ratio == 1:
                cur_confidence *= 1.5
                
            # is the winner a human?
            if is_human:
                # check if person's names appear on both sides of the pattern (just choose one pattern that matches, earlier is better)
                is_valid = False
                name_list = []
                pattern_location_idx = (-1, -1) # start, end
                use_worse_pattern = False
                for pattern_idx, match in all_matches:
                    start, end = match.span()
                    pre_names = [name.text for name in persons if tweet["new_text"].find(name.text) < start]
                    post_names = [name.text for name in persons if tweet["new_text"].find(name.text) > end]
                    
                    # winner is in the pattern?
                    if winner_idx >= start and winner_idx <= end:
                        continue
                    # winner is before the pattern, use post_names
                    elif winner_idx < start:
                        name_list = post_names
                    # winner is after the pattern, use pre_names
                    else:
                        name_list = pre_names
                    if name_list:
                        pattern_location_idx = (start, end)
                        is_valid = True
                        if pattern_idx in worse_pattern_idx_list:
                            use_worse_pattern = True
                        break
                
                # if not valid, skip this winner
                if not is_valid:
                    continue
                
                # add candidates
                for name in name_list:
                    name_idx = tweet["new_text"].find(name)
                    dist_to_pattern = min(abs(name_idx - pattern_location_idx[0]), abs(name_idx - pattern_location_idx[1]))
                    name = name_cleaning(name)
                    if name.lower() == winner:
                        continue
                    
                    candidates = {
                        "nominee_candidates": [name],
                        "award_candidates": [award],
                        "base_confidence": cur_confidence / (dist_to_pattern / 3) if use_worse_pattern else cur_confidence / 3,
                    }
                    tweet["candidates"] = tweet.get("candidates", []) + [candidates]
            
            # is the winner a work of art?
            else:
                # check if work's names appear on both sides of the pattern (just choose one pattern that matches, earlier is better)
                is_valid = False
                name_list = []
                pattern_location_idx = (-1, -1) # start, end
                use_worse_pattern = False
                for pattern_idx, match in all_matches:
                    start, end = match.span()
                    pre_names = [name.text for name in works if tweet["new_text"].find(name.text) < start]
                    post_names = [name.text for name in works if tweet["new_text"].find(name.text) > end]
                    
                    # winner is in the pattern?
                    if winner_idx >= start and winner_idx <= end:
                        continue
                    # winner is before the pattern, use post_names
                    elif winner_idx < start:
                        name_list = post_names
                    # winner is after the pattern, use pre_names
                    else:
                        name_list = pre_names
                    if name_list:
                        pattern_location_idx = (start, end)
                        is_valid = True
                        if pattern_idx in worse_pattern_idx_list:
                            use_worse_pattern = True
                        break
                
                # if not valid, skip this winner
                if not is_valid:
                    continue
                
                # add candidates
                for name in name_list:
                    # TODO: check the category of the work
                    name_idx = tweet["new_text"].find(name)
                    dist_to_pattern = min(abs(name_idx - pattern_location_idx[0]), abs(name_idx - pattern_location_idx[1]))
                    candidates = {
                        "nominee_candidates": [name.lower()],
                        "award_candidates": [award],
                        "base_confidence": cur_confidence / (dist_to_pattern / 3) if use_worse_pattern else cur_confidence / 3,
                    }
                    tweet["candidates"] = tweet.get("candidates", []) + [candidates]
    

            
    def nominee_ts_based_match(self, tweet: dict, base_confidence=1.0):
        spacy_output = tweet.get('spacy_output', spacy_model(tweet['new_text']))
        
        possible_nominees = {}
        # find nominee candidates based on entities
        for ent in spacy_output.ents:
            satisfied = False
            if (ent.root.dep_ == "nsubjpass" or ent.root.dep_ == "nsubj") and ent.root.head.lemma_ in self.nominee_ts_verbs:
                satisfied = True
            else:
                for i in range(max(ent.start - 3, 0), min(len(spacy_output), ent.end + 6)):
                    if spacy_output[i].lemma_ in self.nominee_ts_verbs:
                        satisfied = True
                        break
            if not satisfied:
                continue
            possible_nominees[ent.text] = ent.label_ if ent.label_ == "PERSON" or ent.label_ == "WORK_OF_ART" else ""
        
        # find nominee candidates based on the verb
        target_verb = [token for token in find_verbs(spacy_output) if token.lemma_ in self.nominee_ts_verbs]
        for verb in target_verb:
            for child in verb.children:
                if (child.dep_ == "nsubjpass" or child.dep_ == "nsubj") and not child.pos_ == "PRON":
                    # possible_nominees += [(cand, True) for cand in generate_candidates(child, verb)]
                    child_descendants = get_descendants_precise(child)
                    if possible_nominees.get(child_descendants, "") == "":
                        possible_nominees[child_descendants] = ""

        possible_nominees = list(possible_nominees.items())
        tweet['possible_nominees'] = tweet.get('possible_nominees', []) + possible_nominees
        tweet['possible_roles'] = tweet.get('possible_roles', {})
        tweet['keyword_constraints'] = tweet.get('keyword_constraints', {})
        tweet['possible_awards'] = tweet.get('possible_awards', {})
        # tweet['possible_timestamps'] = tweet.get('possible_timestamps', {})
        tweet['possible_candidates'] = tweet.get('possible_candidates', {})
        
        
        for possible_n, label in possible_nominees:
            cur_confidence = base_confidence
            award = ""
            nominee = ""
            
            # not PERSON or WORK_OF_ART by spacy -> reduce confidence
            if not label:
                cur_confidence *= 0.8
            nominee = possible_n

            # TODO: add case for WORK_OF_ART
            # get possible roles for nominee
            possible_roles = []
            if label == 'PERSON':
                name = name_cleaning(nominee)
                space_count = name.count(" ")
                if space_count > 0 and space_count <= 2:
                    possible_roles, legal_name = self.wiki.possible_job_list(name, need_name_cleaning=False)
                    if possible_roles:
                        nominee = legal_name
                # else:
                if space_count == 0 or space_count > 2:
                    cur_confidence /= (space_count + 2)
                nominee = name.lower()
            tweet['possible_roles'][nominee] = possible_roles
            
            # wikipedia can find this name + get the role -> increase confidence
            possible_roles = self.wiki.get_movie_jobs(possible_roles)
            if len(possible_roles) == 1:
                cur_confidence *= 1.2
            elif len(possible_roles) == 0:
                cur_confidence *= 0.8
        
            # constraints = possible_roles + award_keywords in tweets
            keyword_constraints = []
            if len(possible_roles) == 1:
                keyword_constraints = possible_roles
            for token in spacy_output:
                if token.text.lower() in self.award_keywords and not token.text.lower() in keyword_constraints:
                    keyword_constraints.append(token.text.lower())
            tweet['keyword_constraints'][nominee] = keyword_constraints
        
            # find possible awards based on the keywords
            possible_awards = set(self.awards)
            if keyword_constraints:
                for keyword in keyword_constraints:
                    possible_awards = possible_awards.intersection(self.keyword_to_awards[keyword])
            tweet['possible_awards'][nominee] = list(possible_awards)
            if not possible_awards:
                continue
        
            # guess the possible award based on the timestamp
            award, confidence = self.timestamp_cluster.categorize_timestamp(tweet['timestamp_ms'], possible_awards)
            tweet['possible_candidates'][nominee] = (award, confidence)
            if not award:
                continue
            
            cur_confidence *= confidence
            
            candidates = {
                "nominee_candidates": [nominee],
                "award_candidates": [award],
                "base_confidence": cur_confidence,
            }
            tweet["candidates"] = tweet.get("candidates", []) + [candidates]


    def nominee_verb_based_match(self, tweet: dict, base_confidence=1.0):
        """
        Given a tweet, find the nominee and award
        
        Requires: tweet['new_text'] includes nominee_verb_pattern
        Modifies: tweet['candidates']
        """
        try:
            spacy_output = tweet.get('spacy_output', spacy_model(tweet['new_text']))
            
            for sentence in spacy_output.sents:
                # Y (should / will) win X / Y is nominated for X / Y gets robbed
                verb_list = find_verbs(sentence)
                for verb in verb_list:
                    root = verb
                    award = []
                    nominee = []
                    cur_confidence = base_confidence
                    
                    if root.lemma_ in self.nominee_active_verbs:
                        for child in root.children:
                            if child.dep_ == "dobj":
                                award += generate_candidates(child, root)
                            elif child.dep_ == "nsubj" or child.dep_ == "nsubjpass":
                                if child.pos_ == "PRON":
                                    cur_confidence *= 0.8
                                    known, is_human = is_human_pronoun(child.text)
                                    if known:
                                        if is_human:
                                            nominee += [p.text for p in find_persons(spacy_output) if p.root.i <= child.i]
                                        else:
                                            nominee += [w.text for w in find_work_of_art(spacy_output) if w.root.i < child.i]
                                    else:
                                        nominee += [p.text for p in find_persons(spacy_output) if p.root.i <= child.i]
                                        nominee += [w.text for w in find_work_of_art(spacy_output) if w.root.i < child.i]
                                        nominee = list(set(nominee))
                                        cur_confidence *= 0.8
                                else:
                                    nominee.append(get_descendants_precise(child))                    
                    # X (is awarded to / goes to) Y
                    elif root.lemma_ in self.nominee_passive_verbs and root.i + 1 < len(sentence) and sentence[root.i + 1].text == "to":                 
                        for chunk in sentence.noun_chunks:
                            if chunk.root.head == root and (chunk.root.dep_ == "nsubj" or chunk.root.dep_ == "nsubjpass"):
                                award.append(get_descendants_precise(chunk.root))
                            elif chunk.root.dep_ == "pobj" and (chunk.root.head == root or chunk.root.head.text == "to"):
                                if chunk.root.pos_ == "PRON":
                                    cur_confidence *= 0.8
                                    known, is_human = is_human_pronoun(chunk.root.text)
                                    if known:
                                        if is_human:
                                            nominee += [p.text for p in find_persons(spacy_output) if p.root.i <= child.i]
                                        else:
                                            nominee += [w.text for w in find_work_of_art(spacy_output) if w.root.i < child.i]
                                    else:
                                        nominee += [p.text for p in find_persons(spacy_output) if p.root.i <= child.i]
                                        nominee += [w.text for w in find_work_of_art(spacy_output) if w.root.i < child.i]
                                        nominee = list(set(nominee))
                                        cur_confidence *= 0.8
                                else:
                                    idxs = get_descendants_idx(chunk.root)
                                    precise = get_descendants_precise(chunk.root)
                                    greedy = get_descendants_greedy(chunk.root, idxs, root)
                                    nominee += list(set([precise, greedy]))

                    if nominee:
                        if not award:
                            cur_confidence *= 0.5
                            # do some inference based on keywords
                            keyword_constraints = []
                            for token in sentence:
                                if token.text.lower() in self.award_keywords and not token.text.lower() in keyword_constraints:
                                    keyword_constraints.append(token.text.lower())
                            
                            # only move forward if there is at least one keyword
                            if keyword_constraints:
                                possible_awards = set(self.awards)
                                for keyword in keyword_constraints:
                                    possible_awards = possible_awards.intersection(self.keyword_to_awards[keyword])

                                if possible_awards:
                                    award = list(possible_awards)
                                    cur_confidence /= len(award)
                        else:
                            for token in sentence:
                                if token.text.lower() in self.award_keywords:
                                    award.append(token.text.lower())
            
                    if nominee or award:
                        candidates = {
                            "nominee_candidates": [name_cleaning(n) for n in list(set(nominee))],
                            "award_candidates": list(set(award)),
                            "base_confidence": cur_confidence,
                        }
                        tweet["candidates"] = tweet.get("candidates", []) + [candidates]
            
        except:
            return

if __name__ == '__main__':
    tp = TweetsPreprocessor()
    tp.load_all_tweets(debug=True)
    
    normal_tweets = tp.load_tweets(key='should_tweets') + tp.load_tweets(key='normal_tweets') + tp.load_tweets(key='guess_tweets') + tp.load_tweets(key='I_tweets')
    awards = json.load(open("gg2013answers.json"))['award_data'].keys()
    
    nominee_extractor = Nominee(normal_tweets, awards)
    nominee_extractor.extract_or_load(debug=False) # TODO: True is for debugging
    
    nominee_extractor.do_vote()     
    
    gather_all(2013, nominee_on=True, winner_on=False, host_on=False, presenter_on=False) 