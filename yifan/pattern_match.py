import re
import json

from data_preprocess import TweetsPreprocessor



# # X: awards
# # Y: person
# schemes_dict_list = [
#     {
#         "scheme": "Y (wins|won|win|receives|received|receive|gets|got|get) X",
#         "is_nominee": False,
#     },
#     {
#         "scheme": "X goes to Y",
#         "is_nominee": False,
#     },
#     {
#         "scheme": "Y takes home X",
#         "is_nominee": False,
#     },
#     {
#         "scheme": "Y (is|was) nominated for X",
#         "is_nominee": True,
#     },
#     {
#         "scheme": "I (bet|guess|hope) X goes to Y",
#         "is_nominee": True,
#     },
#     {
#         "scheme": "I (bet|guess|hope) Y (wins|won|win|receives|received|receive|gets|got|get) X",
#         "is_nominee": True,
#     },
#     {
#         "scheme": "X should have gone to Y",
#         "is_nominee": True,
#     },
#     {
#         "scheme": "Y should have (won|received|got) X",
#         "is_nominee": True,
#     }
# ]

# # matching_pattern = "[^,.:!?]"
# matching_pattern = "."

# def scheme_to_pattern(scheme: str) -> str:
#     """Convert a scheme to a regex pattern"""
#     is_left_x, is_left_y = scheme_to_left(scheme)
#     x_pattern = r"(?P<X>" + matching_pattern + r"+?)" if is_left_x else r"(?P<X>" + matching_pattern + r"+)"
#     y_pattern = r"(?P<Y>" + matching_pattern + r"+?)" if is_left_y else r"(?P<Y>" + matching_pattern + r"+)"
    
#     # Replace X and Y placeholders with appropriate regex patterns
#     pattern = scheme.replace("X", x_pattern).replace("Y", y_pattern) 
#     return pattern

# def scheme_to_left(scheme: str) -> tuple:
#     """Convert a scheme to two booleans, indicating whether X and Y are on the left (if left, gather the candiate from the end of match)"""
#     X_index = scheme.index("X")
#     Y_index = scheme.index("Y")
#     is_left_x = X_index < Y_index
#     return is_left_x, not is_left_x

# def make_schemes_dict_list(schemes_dict_list: list):
#     for scheme_dict in schemes_dict_list:
#         scheme = scheme_dict['scheme']
#         scheme_dict['pattern'] = scheme_to_pattern(scheme)
#         scheme_dict['is_left_x'], scheme_dict['is_left_y'] = scheme_to_left(scheme)

# def pattern_match_from_tweets(tweets: list, schemes_dict_list: list):
#     """Add pattern_matches field to each tweet"""
#     make_schemes_dict_list(schemes_dict_list)

#     for tweet in tweets:
#         del tweet['text']
        
#         text = tweet['new_text'].lower()
#         for scheme_dict in schemes_dict_list:
#             pattern = scheme_dict['pattern']
#             is_left_x, is_left_y = scheme_dict['is_left_x'], scheme_dict['is_left_y']
            
#             match = re.search(pattern, text)
#             if match:
#                 award_text = match.group("X")
#                 award_tokens = award_text.split()
#                 award_candidates = tweet.get('award_candidates', [])
#                 for i in range(len(award_tokens)):
#                     if is_left_x:
#                         award_candidates.append(" ".join(award_tokens[i:]))
#                     else:
#                         award_candidates.append(" ".join(award_tokens[:i+1]))
#                 tweet['award_candidates'] = award_candidates
                
#                 person_text = match.group("Y")
#                 person_tokens = person_text.split()
#                 person_key = "nominee_candidates" if scheme_dict['is_nominee'] else "winner_candidates"
#                 person_candidates = tweet.get(person_key, [])
#                 for i in range(len(person_tokens)):
#                     if is_left_y:
#                         person_candidates.append(" ".join(person_tokens[i:]))
#                     else:
#                         person_candidates.append(" ".join(person_tokens[:i+1]))
#                 tweet[person_key] = person_candidates


def match_verb_pattern(text: str) -> bool:
    # List of patterns
    patterns = [
        r'\b(wins|won|win|receives|received|receive|gets|got|get)\b',
        r'\b(goes|went) to\b',
        r'\bawarded to\b',
        r'\bnominated for\b',
        r'\b(takes|took) home\b'
    ]
    
    # Check each pattern against the text
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def new_pattern_match_from_tweets(tweets: list) -> list:
    match_list = []
    for tweet in tweets:
        if match_verb_pattern(tweet['new_text']):
            match_list.append(tweet)
    print(len(match_list))
    return match_list

if __name__ == '__main__':
    tp = TweetsPreprocessor()
    tweets = tp.load_tweets()
    res_list = new_pattern_match_from_tweets(tweets)
    
    with open('pattern_match.json', 'w') as f:
        f.write(json.dumps(res_list, indent=4))
    