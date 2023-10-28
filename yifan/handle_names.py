import json
import re
from nicknames import NickNamer
import time

def remove_punctuation(text: str) -> str:
        return re.sub(r"[^\w\s]", ' ', text)

def split_text(text: str) -> list:
    return remove_punctuation(text).lower().split()

def about_human(award: str) -> bool:
    return "actor" in award or "actress" in award or "director" in award

def get_job(award: str) -> str:
    if "actor" in award:
        return "actor"
    elif "actress" in award:
        return "actress"
    elif "director" in award:
        return "director"
    
def remove_triple_letters(text: str) -> str:
    pattern = r'\b\w*([a-zA-Z])\1\1\w*\b'
    return re.sub(pattern, '', text)

def remove_s(text: str) -> str:
    return text.replace("'s", "")

def keep_alpha_and_hyphen(text: str) -> str:
    return re.sub(r'[^a-zA-Z-. ]', '', text)

def remove_selected_words(text: str) -> str:
    pattern = r'\byay\w*|\byah\w*|\bohh\w*|\bcongrat\w*|\brt\b'
    
    return re.sub(pattern, '', text, flags=re.IGNORECASE)

def remove_space(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

def name_cleaning(text: str) -> str:
    text = remove_triple_letters(text)
    text = remove_s(text)
    text = keep_alpha_and_hyphen(text)
    text = remove_selected_words(text)
    text = remove_space(text)
    if text.istitle():
        return text
    return text.title()

class WinnerNameMatcher:
    def __init__(self, winner_to_awards_dict):
        self.winner_to_awards_dict = {winner: award.lower() for winner, award in winner_to_awards_dict.items()}
        self.winner_to_keywords_dict = {winner: split_text(winner) for winner in winner_to_awards_dict.keys()} # Map winners' name to keywords
        self.nn = NickNamer()
        self.count = {
            "success": 0,
            "failure": 0,
            "total_time": 0,
        }
    
    def __del__(self):
        self.print_stats()
    
    def print_stats(self):
        print("---------------WinnerNameMatcher stats:---------------")
        for k, v in self.count.items():
            print(f"{k}: {v}")
    
    def get_nickname_set(self, name: str, is_human: bool) -> set:
        if is_human:
            return self.nn.nicknames_of(name).union({name})
        else:
            return {name}
        
    def get_winner_from_text(self, text: str) -> list:
        """ return a list of dict with keys "confidence", "winner" and "start_idx" """
        start = time.time()
        plain_word_list = split_text(text)
        plain_word_set = set(plain_word_list)
        
        # check if the text contains the keywords or nicknames of the winner
        results = []
        for w, award in self.winner_to_awards_dict.items():
            is_human = about_human(award)
            word_idx_list = []
            for keyword in self.winner_to_keywords_dict[w]:
                common_word_set = self.get_nickname_set(keyword, is_human).intersection(plain_word_set)
                if not common_word_set:
                    break
                cur_word_idx = plain_word_list.index(list(common_word_set)[0])
                word_idx_list.append(cur_word_idx)

            if len(word_idx_list) != len(self.winner_to_keywords_dict[w]):
                continue
            avg_dist = 0
            for i in range(1, len(word_idx_list)):
                avg_dist += abs(word_idx_list[i] - word_idx_list[i - 1])
            if len(word_idx_list) > 1:
                avg_dist /= len(word_idx_list) - 1
            confidence = 1 / avg_dist if avg_dist > 0 else 0.5
            
            cur_best = {
                "confidence": confidence,
                "winner": w,
                "start_idx": text.lower().find(plain_word_list[word_idx_list[0]]),
            }
            results.append(cur_best)
        
        if len(results) > 0:
            self.count["success"] += 1
            self.count["total_time"] += time.time() - start
            return results
        
        plain_text = remove_punctuation(text).lower()
        # check if every exact word of the winner is in the text
        for w in self.winner_to_awards_dict:
            word_idx_list = []
            for word in self.winner_to_keywords_dict[w]:
                if word not in plain_text:
                    break
                word_idx_list.append(plain_text.find(word))
            if len(word_idx_list) != len(self.winner_to_keywords_dict[w]):
                continue
            
            avg_dist = 0
            for i in range(1, len(word_idx_list)):
                avg_dist += abs(word_idx_list[i] - word_idx_list[i - 1])
            if len(word_idx_list) > 1:
                avg_dist /= len(word_idx_list) - 1
            confidence = 1 / (avg_dist / 5) if avg_dist > 0 else 0.5  # 5 for average word length
            cur_best = {
                "confidence": confidence,
                "winner": w,
                "start_idx": word_idx_list[0],
            }
            results.append(cur_best)
            
        if len(results) > 0:
            self.count["success"] += 1
            self.count["total_time"] += time.time() - start
            return results
        # TODO: match les mis with les miserables?
        # TODO: match mis spelling?
        self.count["failure"] += 1
        self.count["total_time"] += time.time() - start
        return None

if __name__ == '__main__':
    winner_to_awards_dict = {data['winner']: award for award, data in json.load(open("gg2013answers.json"))['award_data'].items()}
    winner_name_matcher = WinnerNameMatcher(winner_to_awards_dict)
    print(winner_name_matcher.get_winner_from_text("Anne Hathaway for the Golden Globe! Loved her in Les miserables and loved her white Chanel ensemble!"))