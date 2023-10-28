import json
import spacy
import re
import time

from data_preprocess import TweetsPreprocessor


spacy_model = spacy.load("en_core_web_md")

guess_verbs = ["guess", "bet", "hope"]
active_award_verbs = ["win", "receive", "get", "take"]  # Y wins X
passive_award_verbs = ["awarded", "goes", "go"]         # X (is awarded to / goes to) Y
nominate_verbs = ["nominate"]                           # Y is nominated for X

punct_pattern = r'[!"#$%&\'()*+,-./:;<=>?@^_`{|}~]'
remove_punct_pattern = r'((?<= )' + punct_pattern + ' |^' + punct_pattern + ' | ' + punct_pattern + '$)'

def identify_pronoun_category(pronoun: str) -> str:
    pronoun = pronoun.lower()
    human_pronouns = ["he", "him", "his", "she", "her", "hers"]
    nonhuman_pronouns = ["it", "its"]

    if pronoun in human_pronouns:
        return "human"
    elif pronoun in nonhuman_pronouns:
        return "non-human"
    else:
        return "unknown"
    
def is_human_pronoun(pronoun: str) -> (bool, bool):
    res = identify_pronoun_category(pronoun)
    return res != "unknown", res == "human"

def find_root(spacy_output) -> list:
    return [token for token in spacy_output if token.dep_ == "ROOT"]

def find_persons(spacy_output) -> list:
    return [ent for ent in spacy_output.ents if ent.label_ == "PERSON"]

def find_work_of_art(spacy_output) -> list:
    return [ent for ent in spacy_output.ents if ent.label_ == "WORK_OF_ART"]

def find_verbs(spacy_output):
    return [token for token in spacy_output if token.pos_ == "VERB"]

def get_descendants_idx(token):
    return [d.i for d in token.subtree]

def remove_punct_with_space(text):
    return re.sub(remove_punct_pattern, '', text)

def remove_punct(text):
    return "".join([c for c in text if c.isalnum() or c.isspace()])

def get_descendants_fuzzy(token, idxs) -> str:
    return token.doc[idxs[0] : idxs[-1] + 1].text

def get_descendants_greedy(token, idxs, root) -> str:
    if max(idxs) + 1 < len(token.doc) and token.doc[max(idxs) + 1].head == root:
        idxs += get_descendants_idx(token.doc[max(idxs) + 1])
    return token.doc[min(idxs) : max(idxs) + 1].text

def generate_candidates(token, root) -> list:
    idxs = get_descendants_idx(token)
    precise = get_descendants_precise(token)
    fuzzy = get_descendants_fuzzy(token, idxs)
    greedy = get_descendants_greedy(token, idxs, root)
    
    candidates = [precise, fuzzy, greedy]
    candidates += get_descendants_split(fuzzy)
    return list(set(candidates))

def get_descendants_precise(token) -> str:
    return remove_punct_with_space(" ".join([d.text for d in token.subtree]))

def get_descendants_split(fuzzy_text: str) -> list:
    if " and " in fuzzy_text:
        return [remove_punct(x) for x in fuzzy_text.split(" and ")]
    elif ": " in fuzzy_text:
        return [remove_punct(x) for x in fuzzy_text.split(": ")]
    return []

def keyword_punct_match(sentence, root, winner, award):
    # X(may have "best") [some punctuations] Y(PERSON/WORK_OF_ART)
    persons = find_persons(sentence)
    works = find_work_of_art(sentence)
    min_entity_index = min([ent.start for ent in persons + works], default=-1)
    if len(persons) == 0 and len(works) == 0:
        return
    
    punctuations = [child for child in root.children if child.text in ["-", ":"] and child.i < min_entity_index]
    if len(punctuations) == 0:
        return
    
    last_punct = punctuations[-1]
    award.append(sentence[:last_punct.i].text.rstrip())
    winner.append(sentence[last_punct.i+1:].text.lstrip())
    winner += [ent.text for ent in persons + works]
    
    
def verb_based_match(spacy_output, sentence, root, winner, nominee, award, always_nominee=False):
    try:
        # Y wins X / Y is nominated for X
        if root.lemma_ in active_award_verbs or root.lemma_ in nominate_verbs:
            is_nominee = root.lemma_ in nominate_verbs or always_nominee
            for child in root.children:
                if child.dep_ == "dobj":
                    award += generate_candidates(child, root)
                elif child.dep_ == "nsubj" or child.dep_ == "nsubjpass":
                    object_name = ""
                    if child.pos_ == "PRON":
                        if find_persons(spacy_output):
                            object_name = find_persons(spacy_output)[0].text
                    else:
                        object_name = get_descendants_precise(child)
                    if len(object_name) > 0:
                        if is_nominee:
                            nominee.append(object_name)
                        else:
                            winner.append(object_name)
        # X (is awarded to / goes to) Y
        elif root.text in passive_award_verbs and sentence[root.i + 1].text == "to":                 
            for chunk in sentence.noun_chunks:
                if chunk.root.head == root and (chunk.root.dep_ == "nsubj" or chunk.root.dep_ == "nsubjpass"):
                    award.append(get_descendants_precise(chunk.root))
                elif chunk.root.dep_ == "pobj" and (chunk.root.head == root or chunk.root.head.text == "to"):
                    idxs = get_descendants_idx(chunk.root)
                    precise = get_descendants_precise(chunk.root)
                    greedy = get_descendants_greedy(chunk.root, idxs, root)
                    winner += list(set([precise, greedy]))
        # (guess / bet / hope) + (Y wins X  / X (is awarded to / goes to) Y)
        elif root.lemma_ in guess_verbs:
            for v in find_verbs(sentence):
                if v.dep_ == "ROOT" or v.head != root:
                    continue
                cur_root = v
                if cur_root.lemma_ in active_award_verbs:
                    for child in cur_root.children:
                        if child.dep_ == "dobj":
                            award += generate_candidates(child, cur_root)
                        elif child.dep_ == "nsubj" or child.dep_ == "nsubjpass":
                            object_name = get_descendants_precise(child)
                            nominee.append(object_name)
                elif cur_root.text in passive_award_verbs and sentence[cur_root.i + 1].text == "to": 
                    for chunk in sentence.noun_chunks:
                        if chunk.root.head == cur_root and (chunk.root.dep_ == "nsubj" or chunk.root.dep_ == "nsubjpass"):
                            award.append(get_descendants_precise(chunk.root))
                        elif chunk.root.dep_ == "pobj" and (chunk.root.head == cur_root or chunk.root.head.i == cur_root.i + 1):
                            idxs = get_descendants_idx(chunk.root)
                            precise = get_descendants_precise(chunk.root)
                            greedy = get_descendants_greedy(chunk.root, idxs, cur_root)
                            nominee += list(set([precise, greedy]))
    except:
        return
    

def syntax_based_match(tweet: dict, always_nominee=False):
    text = tweet['new_text']
    spacy_output = spacy_model(text)
    winner = []
    nominee = []
    award = []
    
    for sentence in spacy_output.sents:
        root = sentence.root
        if root is None:
            continue
        if root.pos_ == "VERB":
            verb_based_match(spacy_output, sentence, root, winner, nominee, award, always_nominee)
        elif "best" in sentence.text.lower():
            keyword_punct_match(sentence, root, winner, award)

    if winner:
        tweet['winner_candidates'] = tweet.get('winner_candidates', []) + winner
    if nominee:
        tweet['nominee_candidates'] = tweet.get('nominee_candidates', []) + nominee
    if award:
        tweet['award_candidates'] = tweet.get('award_candidates', []) + award


def match_nominee_verb_pattern(text: str) -> bool:
    # List of verb-based patterns
    patterns = [
        r'\b(nominated for)\b',
        r'\b((should|would) have (won|received|got|taken home|gone to|been awarded to))\b',
        r'\b((should|will) (win|receive|get|take home|go to|be awarded to))\b',
        r'I (wish|hope|guess|think|bet|predict|expect) .*(wins|win|receives|receive|gets|get|goes to|go to|awarded to|take(s) home)\b',
        r'\b((was|is|got|get) robbed)\b',
    ]
    
    # Check each pattern against the text
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def match_nominee_keyword_pattern(text: str) -> bool:
    # List of verb-based patterns
    patterns = [
        r'\b(nominee|nominees|nominated|nomination)\b',
    ]
    
    # Check each pattern against the text
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def match_winner_verb_pattern(text: str) -> bool:
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

def syntax_based_match_from_tweets(tweets: list):
    start_time = time.time()
    for i, tweet in enumerate(tweets):
        if i % 1000 == 0:
            print(f"Processing tweet {i}, elapsed time: {time.time() - start_time}")
        syntax_based_match(tweet)


if __name__ == "__main__":
    tweets = json.load(open("pattern_match.json"))
    syntax_based_match_from_tweets(tweets)
    with open("syntax_match1.json", "w") as f:
        json.dump(tweets, f, indent=4)
    