import json
import re
import collections


hint_words=["drama","television","music","movie","film","award","comedy","picture","musical","song","video"]
stop_words=["for "," at", " and"]
punctuation=["?","!",".",","]

def strip_non_alphabetical(input_string):
    pattern = r'^[a-zA-Z-\s].*[a-zA-Z-\s]$'

    # Use re.search() to find the matching pattern in the input text
    match = re.search(pattern, input_string)
    
    if match:
        return match.group()
    else:
        return ""

def replace_hint_words(text, hint_words):
    for word in hint_words:
        pattern = r'\b({}|{}s)\b'.format(word, word)
        # Replace the matched word with a more specific phrase
        text = re.sub(pattern, f'{word}', text, flags=re.IGNORECASE)
    return text

def normalize(text):
    pattern = r'^RT @\w+: '
    cleaned_text = re.sub(pattern, '', text)
    
    #remove hashtag
    hash_pattern = r'#\w+'
    hash_text = re.sub(hash_pattern, '', cleaned_text)
    
    tag_pattern=r'@\w+'
    tag_text = re.sub(tag_pattern, '', hash_text)

    tag_text=tag_text.replace("–","-")

    # non_english_pattern = r'[^a-zA-Z0-9\s-:]'
    # cleaned_text = re.sub(non_english_pattern, '', tag_text)
    pattern = r'\b(tv)\b'

    # Use re.IGNORECASE flag to make the replacement case-insensitive
    text = re.sub(pattern, 'television', tag_text, flags=re.IGNORECASE)

    text=replace_hint_words(text, hint_words)
    return text.lower().strip()

