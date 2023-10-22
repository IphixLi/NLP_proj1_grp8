- Data Preprocess (data_preprocess.py)

    - basic preprocess

        - ```python
            modifies: tweet['new_text']
            ```

        - fix website symbols (like &amp; to &, &lt; to <)

        - delete non ascii characters

        - remove extra whitespaces ("       " / "\n" / "\t"... to " ")

        - delete urls (starting with http or https)

    - tweet-feature based preprocess

        - ```python
            modifies: tweet['retweets'], self.tweets_classification['retweet_count'] and tweet['new_text']
            ```

        - extract retweets or quotes

            - search quotes and retweets format until nothing to find (maybe a tweet can have two layers of retweets)
            - if find retweets
                - extract them ('new_text' truncated)
                - save retweet info in tweet['retweets'] (this is a list)
                - save those tweets that get retweeted in self.tweets_classification['retweet_count'] map for counting the retweeted times

        - remove trailing hashtag (those appear after the end of sentence)

        - fix username (see page 36 in proj1 tips and tricks slides)

            - @BestDirector → Best director
            - @best_director → Best director
            - @bestdirector → Bestdirector

        - fix hashtag (see page 36 in proj1 tips and tricks slides) (maybe remove all hashtags?)

            - #BestDirector → Best director
            - #best_director → Best director
            - #bestdirector → Bestdirector

    - split the tweets dataset (check from top to bottom) and save the results in tweets/

        - ```python
            modifies: self.tweets_classification
            ```

        - tweets that include retweets -> finally saved in tweets/retweets.json

        - tweets that are empty ->  finally saved in tweets/empty_tweets.json

        - tweets that may use foreign languages ->  finally saved in tweets/empty_tweets.json

        - tweets that start with "I (hope|guess|think|bet|predict)" ->  finally saved in tweets/guess_tweets.json

        - tweets that start with "I " ->  finally saved in tweets/I_tweets.json

        - tweets that contain "should" ->  finally saved in tweets/should_tweets.json

        - tweets that don't fall into any of the above categories ->  finally saved in tweets/normal_tweets.json

- Pattern Match (pattern_match.py, results save in pattern_match.json)

    - currently only use "new_pattern_match_from_tweets()"

    - check if it includes this tweet includes these keywords:

        ```python
        patterns = [
            r'\b(wins|won|win|receives|received|receive|gets|got|get)\b',
            r'\b(goes|went) to\b',
            r'\bawarded to\b',
            r'\bnominated for\b',
            r'\b(takes|took) home\b'
        ]
        ```

        - if yes, save those tweets in a list to syntax analysis (this is for avoiding sending all tweets to spacy, which is very slow)

- Syntax Analysis (syntax_analysis.py, results saved in syntax_match1.json)

    - basic idea (currently only use the first two cases checked in "verb_based_match()" )
        - find the root for a sentence (normally it should be VERB or AUX)
        - check if the root verb is listed in my pattern, if yes, go ahead
        - two cases (based on the position of award names and winner/nominee)
            - "Y wins X / Y is nominated for X": for this case, winner/nominee may appear before the verb, and the award name after
            - "X (is awarded to / goes to) Y": the opposite
        - For all children of the verb (which should be some word in X / Y or other unrelated words)
            - if I want it, use the sub-tree of that child
                - Hathaway -> "Anne Hathaway"
                - performance -> "best performance by an actress in a supporting role in a motion picture"
    
- Nominee (find_nominees.py, results saved in nominees?.json)

    - Thinking of finding PERSON and WORK_OF_ART names in sentences that already have mentioned winner's name (I should use my proposed (award, winner) list as an input)