import json
import random
import requests
from bs4 import BeautifulSoup
import string

punctuation_string = string.punctuation + "-"

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

# private function used in findListForData
def updateCandidate(name, temp, candidate):
    for i in punctuation_string:
        name = name.replace(i, ' ')

    if name == "" or name == " ":
        return candidate
    if len(candidate) == 0:
        candidate.append([name, temp])
        return candidate

    namelist = name.split()
    for i in range(0, len(candidate)):
        target = candidate[i][0].split()
        count = 0
        for k in range(0, len(namelist)):
            for v in range(0, len(target)):
                if target[v] in namelist[k] or namelist[k] in target[v]:
                    count += 1
        if count / len(namelist) > 0.8 or count / len(target) >= 0.5:
            candidate[i][1] = candidate[i][1] + temp
            return candidate
    candidate.append([name, temp])
    return candidate


# private function used in findListForData
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
                fullname = resultInfo.text.lower()
                return [fullname, "person", url]
            return [name, "person", url]

# private Function used in find_detail
def find_person_ident(name, href):
    if href == "notfound":
        return [name, []]
    else:
        url = f"https://www.imdb.com" + href
        header = {'User-Agent': get_ua()}

        response = requests.get(url=url, headers=header)
        soup = BeautifulSoup(response.text, "html.parser")

        result1 = soup.find("ul", class_="ipc-inline-list ipc-inline-list--show-dividers sc-afe43def-4 kdXikI baseAlt")
        result2 = result1.find_all("li", class_="ipc-inline-list__item")

        identity = []
        for i in range(0, len(result2)):
            identity.append(result2[i].text.lower())

        return [name, identity]


# private Function used in find_detail
def find_person_in_film(name, href):
    if href == "notfound":
        return [name, []]
    else:
        url = f"https://www.imdb.com" + href
        header = {'User-Agent': get_ua()}

        response = requests.get(url=url, headers=header)
        soup = BeautifulSoup(response.text, "html.parser")

        result1 = soup.find("a",
                            class_="ipc-metadata-list-item__list-content-item ipc-metadata-list-item__list-content-item--link")
        result2 = soup.find_all("a", class_="sc-bfec09a1-1 fUguci")

        return [name, [result1.text.lower(), result2[0].text.lower(), result2[1].text.lower(), result2[2].text.lower(),
                       result2[3].text.lower()]]

# private function used in findListForData
def find_detail(name, Type, url):
    if Type == "work":
        name, result = find_person_in_film(name, url)
    else:
        name, result = find_person_ident(name, url)

    return [name, Type, result]

# public for get "winner" or "noms"(label) from dataset
def findListForData(data, label, year):
    # replace to your own function to get year
    if label == "presenter":
        return clusterPre(data,year)

    keyword = ["actor", "actress", "director", 'singer', "performance", "demille"]
    returnDic = {}

    for award in data.items():

        # judge award type
        for word in keyword:
            if word in award[0]:
                AwardType = "person"
                break
            AwardType = "work"

        candidate = []

        # find all winner
        for i in range(0, len(award[1][label])):
            temp = award[1][label][i][1]
            name = award[1][label][i][0]
            candidate = updateCandidate(name, temp, candidate)

        details = []
        for i in range(0, len(candidate)):
            check = is_work_or_person(candidate[i][0], year)
            if check[1] == AwardType:
                detail = find_detail(check[0],check[1],check[2])
                details.append(detail)
        returnDic[award[0]] = details

    return returnDic

def clusterPre(data,year):
    returnDic = {}

    for award in data.items():

        candidate = []

        # find all winner
        for i in range(0, len(award[1]["presenter"])):
            temp = award[1]["presenter"][i][1]
            name = award[1]["presenter"][i][0]
            candidate = updateCandidate(name, temp, candidate)

        details = []
        for i in range(0, len(candidate)):
            check = is_work_or_person(candidate[i][0], year)
            if check[1] == "person":
                detail = find_detail(check)
                details.append(detail)
        returnDic[award[0]] = details

    return returnDic
