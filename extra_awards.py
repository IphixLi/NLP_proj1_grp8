import json
import spacy
import re
from textblob import TextBlob
import requests
from bs4 import BeautifulSoup
import random

spacy_model = spacy.load("en_core_web_md")
# for request website
def get_ua():
    first_num = random.randint(55, 76)
    third_num = random.randint(0, 3800)
    fourth_num = random.randint(0, 140)
    os_type = [
        '(Windows NT 6.1; WOW64)', '(Windows NT 10.0; WOW64)', '(X11; Linux x86_64)',
        '(Macintosh; Intel Mac OS X 10_14_5)'
    ]
    chrome_version = 'Chrome/{}.0.{}.{}'.format(first_num, third_num, fourth_num)

    ua = ' '.join(['Mozilla/5.0', random.choice(os_type), 'AppleWebKit/537.36',
                   '(KHTML, like Gecko)', chrome_version, 'Safari/537.36']
                  )
    return ua

def is_work_or_person(name, year):
    year1 = str(year - 1)
    year2 = str(year - 2)
    year3 = str(year - 3)
    url = f"https://www.imdb.com/find?q={name.replace(' ', '+')}"
    header = {'User-Agent': get_ua()}

    response = requests.get(url=url, headers=header)
    soup = BeautifulSoup(response.text, "html.parser")
    # Check if the result is a film or actor
    result = soup.find("h3", class_="ipc-title__text")
    if result:
        result_text = result.text.lower()
        if "titles" in result_text:
            resultInfo = soup.find_all("li",
                                       class_="ipc-metadata-list-summary-item ipc-metadata-list-summary-item--click find-result-item find-title-result")
            for i in range(0, len(resultInfo)):
                if year1 in resultInfo[i].text:
                    fullname = resultInfo[i].text[:resultInfo[i].text.index(year1)].lower()
                    herf = resultInfo[i].find("a")["href"]
                    return [fullname, "work", herf]
                elif year2 in resultInfo[i].text:
                    fullname = resultInfo[i].text[:resultInfo[i].text.index(year2)].lower()
                    herf = resultInfo[i].find("a")["href"]
                    return [fullname, "work", herf]
                elif year3 in resultInfo[i].text:
                    fullname = resultInfo[i].text[:resultInfo[i].text.index(year3)].lower()
                    herf = resultInfo[i].find("a")["href"]
                    return [fullname, "work", herf]
            return [name, "work", "notfound"]
        elif "people" in result_text or "person" in result_text:
            resultInfo = soup.find("a", class_="ipc-metadata-list-summary-item__t")
            if resultInfo:
                url = resultInfo["href"]
                fullname = resultInfo.text
                return ["found", fullname, "person", url]
            return ["notfound",name, "person", url]
        

def find_persons(spacy_output) -> list:
    return [ent for ent in spacy_output.ents if ent.label_ == "PERSON"]

def remove_s(text: str) -> str:
    return text.replace("'s", "")

def propose_welldressed(tweets):
    results={}
    for tweet in tweets:
        if re.search(r'dress',tweet['new_text'], flags=re.IGNORECASE) :
            blob = TextBlob(tweet['new_text'])
            # Get the sentiment polarity score
            sentiment_score = blob.sentiment.polarity
            if sentiment_score>0.5:
                spacy_output = spacy_model(tweet['new_text'])
                proposed_people = [remove_s(person.text) for person in find_persons(spacy_output) if not re.search(r'golden', person.text, flags=re.IGNORECASE)]
                results[tweet["user"]["screen_name"]]=proposed_people
    return results

def score_welldressed(proposed):
    dressed={}
    for entry in proposed:
        for name in proposed[entry]:
            og=is_work_or_person(name,2013)
            if og[0]!='found':
                splitted=name.split(" ")
                new=[is_work_or_person(i, 2013) for i in splitted]
                for val in new:
                    if val[0]=='found' and val[1] not in dressed:
                        dressed[val[1]]=1
                    elif val[0]=='found':
                        dressed[val[1]]+=1
            else:
                if og[1] not in dressed:
                    dressed[og[1]]=0
                dressed[og[1]]+=1

    with open("stage/best_dressed.json", "w") as f:
        json.dump(dressed, f, indent=4)


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


    