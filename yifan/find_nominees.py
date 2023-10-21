import json
import string
import spacy
import time

# TODO: case problems for persons and work of art

data = json.load(open('gg2013answers.json'))
spacy_model = spacy.load('en_core_web_md')

def find_persons(spacy_output) -> list:
    persons = []
    for ent in spacy_output.ents:
        if ent.label_ == "PERSON":
            if ent.text.endswith('\'s'):
                persons.append(ent.text[:-2].lower())
            else:
                persons.append(ent.text.lower())
    return persons
            

def find_work_of_art(spacy_output) -> list:
    return [ent.text.lower() for ent in spacy_output.ents if ent.label_ == "WORK_OF_ART"]

def find_nominees(tweet: dict, winner: str, award: str):
    doc = spacy_model(tweet['new_text'])
    persons = find_persons(doc)
    work_of_art = find_work_of_art(doc)
    
    winner = winner.lower()
    
    is_person = winner in persons
    is_work_of_art = winner in work_of_art
    
    if not is_person and not is_work_of_art:
        print('Winner not found in tweet?')
        print(f"Winner: {winner}, text: {tweet['new_text']}")
        return False
    if is_person and is_work_of_art:
        print('Winner is both person and work of art?')
        print(f"Winner: {winner}, text: {tweet['new_text']}")
        return False
    
    if is_person:
        persons.remove(winner)
        tweet['winner_candidates'] = [winner]
        tweet['nominee_candidates'] = persons      
        tweet['award_candidates'] = [award]
    if is_work_of_art:
        work_of_art.remove(winner)
        tweet['winner_candidates'] = [winner]
        tweet['nominee_candidates'] = work_of_art
        tweet['award_candidates'] = [award]
        
    return is_person or is_work_of_art

# suppose if I have already vote the winner for all awards
# then I can check if some nominees and that winner are in the same sentence
def check_winner_and_nominee_in_sentence(tweet: dict):
    sentence = remove_punctuation(tweet['new_text'])
    sentence = sentence.lower()
    for award, details in data['award_data'].items():
        winner = details['winner']
        if winner.lower() in sentence:
            find_nominees(tweet, winner, award)

def remove_punctuation(sentence):
    return ''.join([ch for ch in sentence if ch not in string.punctuation])

if __name__ == '__main__':
    tweets = json.load(open("tweets/normal_tweets.json"))
    start_time = time.time()
    for i, tweet in enumerate(tweets):
        if i % 10000 == 0:
            print(f"Processing tweet {i}, elapsed time: {time.time() - start_time}")
        check_winner_and_nominee_in_sentence(tweet)
    
    with open("nominees?.json", "w") as f:
        json.dump(tweets, f, indent=4)