import json
import random
import time
import requests
from bs4 import BeautifulSoup


#read timestamp and find year -1    
year = "2012"

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


def is_work_or_person(name):
    try:
        url = f"https://www.imdb.com/find?q={name.replace(' ', '+')}"
        header = {'User-Agent':get_ua()}

        response = requests.get(url=url,headers=header)
        soup = BeautifulSoup(response.text, "html.parser")
        # Check if the result is a film or actor
        result = soup.find("h3", class_="ipc-title__text")
        if result:
            result_text = result.text.lower()
            if "titles"in result_text:
                resultInfo = soup.find_all("li", class_="ipc-metadata-list-summary-item ipc-metadata-list-summary-item--click find-result-item find-title-result")
                for i in range(0,len(resultInfo)):
                    if year in resultInfo[i].text:
                        fullname = resultInfo[i].text[:resultInfo[i].text.index(year)].lower()
                        herf = resultInfo[i].find("a")["href"]
                        return [fullname, "work", herf]
                return[name, "work", "notfound"]
            elif "people" in result_text:
                resultIdent = soup.find_all("span", class_="ipc-metadata-list-summary-item__li")
                
                fullname_tag = soup.find("a", class_="ipc-metadata-list-summary-item__t")
                if fullname_tag:
                    fullname = fullname_tag.text.lower()
                else:
                    fullname = name
                resultIdent_text = resultIdent[0].text.lower()
                if "actor" in resultIdent_text:
                    identity = "actor"
                elif "actress" in resultIdent_text:
                    identity = "actress"
                elif "singer" in resultIdent_text:
                    identity = "singer"
                else:
                    identity = "director"

                return [fullname,"person", identity]
        
    except:
        return None
        
if __name__ == "__main__":
    names = ["Lee Ang", "ah Lee Ang", "Ang Lee", "Booo Ang Lee", "Lee Ang", "Ang Lee", "Boooooooo Ang Lee", "Boooooooo Ang Lee", "Ang LEE", "jennifer lawrence"]
    start = time.time()
    for name in names:
        result = is_work_or_person(name)
        print(f"'{name}' is likely an actor/actress or director: {result}")
    print(f"Total time: {time.time() - start}")