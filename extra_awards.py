import json
import spacy
import re
from textblob import TextBlob

spacy_model = spacy.load("en_core_web_md")

def find_persons(spacy_output) -> list:
    return [ent for ent in spacy_output.ents if ent.label_ == "PERSON"]

def propose_welldressed(tweets):
    results={}
    for tweet in tweets:
        if re.search(r'dress',tweet['new_text'], flags=re.IGNORECASE) :
            blob = TextBlob(tweet['new_text'])
            # Get the sentiment polarity score
            sentiment_score = blob.sentiment.polarity
            if sentiment_score>0.5:
                print(tweet['new_text'], sentiment_score)
                spacy_output = spacy_model(tweet['new_text'])
                proposed_people = [person.text for person in find_persons(spacy_output) if not re.search(r'golden', person.text, flags=re.IGNORECASE)]
                results[tweet["user"]["screen_name"]]=proposed_people
    return results

def score_welldressed(proposed):
    dressed={}
    for entry in proposed:
        for name in proposed[entry]:
            if name not in dressed:
                dressed[name]=0
            dressed[name]+=1

    max_count = max(dressed.values())

    # Create a list of names with counts equal to the maximum count
    best_dressed_names = [name for name, count in dressed.items() if count == max_count]

    return best_dressed_names


if __name__ == "__main__":
    tweets = json.load(open("yifan/pattern_match.json"))
    time_sorted_tweets=sorted(tweets, key=lambda x: x["timestamp_ms"], reverse=True)
    results=dict(propose_welldressed(time_sorted_tweets))
    ranked=score_welldressed(results)
    print(ranked)

    with open("stage/best_dressed.json", "w") as f:
        json.dump(results, f, indent=4)
    