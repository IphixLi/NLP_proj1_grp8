import re
import json
from ftfy import fix_text
from unidecode import unidecode
from inflection import humanize, underscore
from os import path
import cld3

filename = 'gg2013.json'
    
class TweetsPreprocessor:
    def __init__(self, tweets_data_file=filename):
        self.tweets_data_file = tweets_data_file
        self.output_dir = 'preprocessed_tweets'
        self.filenames = {
            'retweets': f'{self.output_dir}/retweets.json',
            'empty_tweets': f'{self.output_dir}/empty_tweets.json',
            'foreign_tweets': f'{self.output_dir}/foreign_tweets.json',
            'guess_tweets': f'{self.output_dir}/guess_tweets.json',
            'I_tweets': f'{self.output_dir}/I_tweets.json',
            'should_tweets': f'{self.output_dir}/should_tweets.json',
            'normal_tweets': f'{self.output_dir}/normal_tweets.json',
            'retweet_count': f'{self.output_dir}/retweet_count.json',
        }
        self.tweets_classification = {
            'retweets': [],             # tweets that include retweets
            'empty_tweets': [],         # tweets that are empty after preprocessing
            'foreign_tweets': [],       # tweets that are not in English
            'guess_tweets': [],         # tweets that start with "I (hope|guess|think|bet|predict)"
            'I_tweets': [],             # tweets that start with "I "
            'should_tweets': [],        # tweets that contain "should"  
            'normal_tweets': [],        # tweets that don't fall into any of the above categories
            'retweet_count': {},        # retweets and their counts
        }
        self.tweets = self.load_data(tweets_data_file)
    
    def load_data(self, tweets_data_file: str):
        with open(tweets_data_file) as f:
            return json.load(f)
    
    def save_all_tweets(self):
        for key, filename in self.filenames.items():
            with open(filename, 'w') as f:
                json.dump(self.tweets_classification[key], f, indent=4)
    
    def load_all_tweets(self):
        if not path.exists(self.filenames['foreign_tweets']):
            self.preprocess_tweets()
            self.split_tweets()
            self.split_result_stats()
            self.save_all_tweets()
        for key, filename in self.filenames.items():
            with open(filename) as f:
                self.tweets_classification[key] = json.load(f)
    
    def load_tweets(self, key='normal_tweets') -> list or dict:
        if not path.exists(self.filenames[key]):
            self.preprocess_tweets()
            self.save_all_tweets()
        with open(self.filenames[key]) as f:
            return json.load(f)
    
    def split_tweets(self):
        for tweet in self.tweets:
            text = tweet['new_text']
            if 'retweets' in tweet:
                self.tweets_classification['retweets'].append(tweet)
            elif len(text) == 0:
                self.tweets_classification['empty_tweets'].append(tweet)
            elif self.check_foreign(tweet):
                self.tweets_classification['foreign_tweets'].append(tweet)
            elif self.check_I(text):
                if self.check_guess(text):
                    self.tweets_classification['guess_tweets'].append(tweet)
                else:
                    self.tweets_classification['I_tweets'].append(tweet)
            elif self.check_should(text):
                self.tweets_classification['should_tweets'].append(tweet)
            else:
                self.tweets_classification['normal_tweets'].append(tweet)
        

    def split_result_stats(self):
        for key, value in self.tweets_classification.items():
            if key == 'retweet_count':
                continue
            print(f"{key}: {len(value)} tweets")
    
    def check_foreign(self, tweet: dict) -> bool:
        try:
            tweet_lang = cld3.get_language(tweet['new_text'])
            if tweet_lang.language != 'en' and tweet_lang.probability > 0.95:
                tweet['language'] = (tweet_lang.language, tweet_lang.probability)
                return True
            return False
        except Exception as e:
            print(e)
            print(tweet['new_text'])
            return False
    
    def check_guess(self, text: str) -> bool:
        pattern = r"^I (hope|guess|think|bet|predict)"
        return re.search(pattern, text) is not None
    
    def check_I(self, text: str) -> bool:
        return text.startswith("I ")
    
    def check_should(self, text: str) -> bool:
        return "should" in text
    
    def preprocess_tweet(self, tweet: dict):
        original_text = tweet['text']
        new_text = self.fix_symbols(original_text)
        new_text = self.delete_non_ascii(new_text)
        new_text = self.fix_whitespace(new_text)
        new_text = self.delete_url(new_text)
        tweet['new_text'] = new_text
        self.fix_tweet_features(tweet)
    
    def preprocess_tweets(self):
        """Preprocess tweets, add new_text field to each tweet"""
        for tweet in self.tweets:
            self.preprocess_tweet(tweet)
        
        self.tweets_classification['retweet_count'] = dict(sorted(self.tweets_classification['retweet_count'].items(), key=lambda x: x[1]['count'], reverse=True))
    
    def process_retweet(self, retweet: str) -> str:
        new_text = self.fix_symbols(retweet)
        new_text = self.delete_non_ascii(new_text)
        new_text = self.fix_whitespace(new_text)
        new_text = self.delete_url(new_text)
        # chop the first occurrence of "RT @{account}: / @{account}: " from the retweet
        new_text = new_text[new_text.find(":")+1:].strip()
        new_text = self.remove_trailing_hashtags_and_usernames(new_text)
        new_text = self.fix_username(new_text)
        new_text = self.fix_hashtag(new_text)
        return new_text
        
    
    def fix_symbols(self, text: str) -> str:
       return fix_text(text)

    def delete_non_ascii(self, text: str) -> str:
        return unidecode(text)

    def fix_whitespace(self, text: str) -> str:
        return " ".join(text.split())

    def delete_url(self, text: str) -> str:
        return re.sub(r"http(s)?://\S+", "", text)

    def capitalize_all_words(self, s):
        return ' '.join(word.capitalize() for word in s.split())

    def process_part(self, part: str) -> str:
        """Process a part of a tweet (e.g. username, hashtag)"""
        snake_name = part[:] if "_" in part else underscore(part)
        return self.capitalize_all_words(humanize(snake_name))

    def fix_username(self, text: str) -> str:
        usernames = re.findall(r"@(\w+)", text)
        # Sort by length (from longest to shortest) (avoid nesting cases)
        usernames = sorted(usernames, key=len, reverse=True)
        # Process usernames
        for username in usernames:
            processed_username = self.process_part(username)
            text = text.replace(f"@{username}", f"{processed_username}")
        return text

    def fix_hashtag(self, text: str) -> str:
        hashtags = re.findall(r"#(\w+)", text)
        hashtags = sorted(hashtags, key=len, reverse=True)
        # Process hashtags
        for hashtag in hashtags:
            processed_hashtag = self.process_part(hashtag)
            text = text.replace(f"#{hashtag}", f"{processed_hashtag}")
        return text

    def remove_trailing_hashtags_and_usernames(self, text: str) -> str:
        # The regex looks for:
        # 1. A non-hashtag punctuation followed by word characters or digits
        # 2. A trailing hashtag at the end of the string
        # 3. A trailing username at the end of the string
        pattern = r'([!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~])[\w\d]+|#[\w\d]+$|@[\w\d]+$'
        
        while True:
            match = re.search(pattern, text)
            if match:
                if text[match.start()] == "#" or text[match.start()] == "@":
                    text = text[:match.start()].rstrip()
                else:
                    break
            else:
                break
                
        return text
        
    def extract_retweets(self, tweet: dict) -> dict:
        retweets = []
        patterns = ["RT @", "@"]
        first_pattern_idx = min((tweet['new_text'].find(p) for p in patterns if tweet['new_text'].find(p) != -1), default=-1)
        
        if first_pattern_idx == -1:
            return tweet

        check_text = tweet['new_text'][first_pattern_idx:]

        while True:
            # Determine the current pattern
            cur_pattern = next((pattern for pattern in patterns if pattern in check_text), None)
            if not cur_pattern:
                break

            pattern_idx = check_text.find(cur_pattern)
            colon_idx = check_text.find(":", pattern_idx)
            
            # check if the account name is invalid
            if colon_idx == -1 or ' ' in check_text[pattern_idx + len(cur_pattern):colon_idx]:
                break
            
            cur_retweet = check_text[pattern_idx:].strip()
            if cur_retweet in self.tweets_classification['retweet_count']:
                self.tweets_classification['retweet_count'][cur_retweet]['count'] += 1
            else:
                self.tweets_classification['retweet_count'][cur_retweet] = {
                    'count': 1,
                    'new_text': self.process_retweet(cur_retweet),
                }
                
            retweets.append(cur_retweet)
            check_text = check_text[colon_idx + 1:]

        if retweets:
            tweet['retweets'] = retweets
            tweet['new_text'] = tweet['new_text'][:first_pattern_idx].strip()
            if len(tweet['new_text']) > 0 and tweet['new_text'][-1] in ["\"", "'"]:
                tweet['new_text'] = tweet['new_text'][:-1].strip()

        return tweet
            

    def fix_tweet_features(self, tweet: dict):
        """Fix tweet features (e.g. username, hashtag)"""
        self.extract_retweets(tweet)
        
        new_text = self.remove_trailing_hashtags_and_usernames(tweet['new_text'])
        new_text = self.fix_username(new_text)
        tweet['new_text'] = self.fix_hashtag(new_text)
        

if __name__ == '__main__':
    tp = TweetsPreprocessor()
    tp.preprocess_tweets()
    tp.split_tweets()
    tp.split_result_stats()
    tp.save_all_tweets()
