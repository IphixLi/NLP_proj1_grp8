import string
import json
import re

from wiki import WikiSearch
from imdbpy import IMDBSearch
from handle_names import get_job, about_human, calc_sim, split_text, about_music, name_cleaning

wiki = WikiSearch()
imdb = IMDBSearch()

unwanted_candidates = [
    "golden globe", "golden globes", "the golden globe", "the golden globes", "oscar", "oscars", "academy"
]

no_nominees_wards = [
    "cecil b. demille award"
]


def may_have_multiple_candidates(candidate: str) -> bool:
    return "and" in candidate or "or" in candidate or "but" in candidate or "for" in candidate

def split_multiple_candidates_str(candidate: str) -> list:
    return [
        s.strip() for s in re.split(r'\b(and|or|but|for)\b', candidate)
        if s.strip() != "" and s.strip() != "and" and s.strip() != "or" and s.strip() != "but" and s.strip() != "for"
    ]

def split_multiple_candidates(candidate: tuple) -> list:
    candidates = split_multiple_candidates_str(candidate[0])
    confidence = candidate[1] / len(candidates)
    return [(candidate, confidence) for candidate in candidates]

def if_one_include_the_other(str1: str, str2: str) -> bool:
    """ if A includes B:
    1. B should be at least 3 characters long
    2. A should not have multiple candidates (at least no clear structure)
    3. B should be in A
    """
    if len(str1) < len(str2) and len(str1) >= 3:
        return not may_have_multiple_candidates(str2) and str1_in_str2(str1=str1, str2=str2)
    if len(str2) < len(str1) and len(str2) >= 3:
        return not may_have_multiple_candidates(str1) and str1_in_str2(str1=str2, str2=str1)
    return False

def str1_in_str2(str1: str, str2: str) -> bool:
    if len(str1) < len(str2):
        str1_words = split_text(str1)
        for word in str1_words:
            if word not in str2:
                return False
        return True
    return False

def space_preference_score(candidate: str, is_human: bool) -> int:
    space_count = candidate.count(" ")
    
    max_prefer_space = 2 if is_human else 4
    if space_count > 0 and space_count <= max_prefer_space and len(candidate) > 5:
        return 8
    else:
        return 1

def cluster_candidates(candidates: list, award: str, all_awards: list, winner_dict=None, host_list=None) -> list:
    is_human = about_human(award)
    # make sure candidates are sorted by confidence score
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    # check if there are multiple candidates in the possible_multiple_candidates
    possible_multiple_candidates = []
    for candidate in candidates:
        current_string = candidate[0]
        if may_have_multiple_candidates(current_string):
            possible_multiple_candidates.append(candidate)
            candidate[1] /= 2
    
    # split the possible_multiple_candidates
    for possible_multiple_candidate in possible_multiple_candidates:
        multiple_candidates = split_multiple_candidates(possible_multiple_candidate)
        for candidate in multiple_candidates:
            candidates.append(candidate)
    
    # cluster candidates by similarity
    num_candidates = len(candidates)
    to_remove = []
    to_remove_strs = []
    to_append = []

    for i in range(num_candidates):
        current_string = candidates[i][0]
        if current_string in to_remove_strs:
            continue
        
        current_clustering = [candidates[i]]
        for j in range(i+1, num_candidates):
            # if the string is similar enough
            for candidate in current_clustering:
                if if_one_include_the_other(candidate[0], candidates[j][0]):
                    current_clustering.append(candidates[j])
                    break
                score = calc_sim(candidate[0], candidates[j][0])
                # if the score is too low, break
                if score > 85:
                    current_clustering.append(candidates[j])
                    break

        # if there is more than one candidate in the current clustering
        if len(current_clustering) > 1:
            # sort by confidence score, pick the highest one as the representative
            current_clustering.sort(key=lambda x: x[1] * space_preference_score(x[0], is_human), reverse=True)
            representative = current_clustering[0][0]
            other_candidates = [candidate[0] for candidate in current_clustering[1:]]
            # sum up the confidence score
            confience_score = sum([candidate[1] for candidate in current_clustering])
            # remove the current clustering from the candidate list
            for candidate in current_clustering:
                to_remove.append(candidate)
                to_remove_strs.append(candidate[0])
            # append the representative to the candidate list
            to_append.append((representative, confience_score, other_candidates))

    # remove and append candidates
    for candidate in to_remove:
        if candidate in candidates:
            candidates.remove(candidate)
    for candidate in to_append:
        candidates.append(candidate)
        
    candidates_dict = {
        candidate[0]: candidate[1] for candidate in candidates if candidate not in possible_multiple_candidates
    }
                  
    candidates = [(k, v) for k, v in candidates_dict.items()]
    
    # remove unwanted candidates
    to_remove = []
    for candidate in candidates:
        # remove candidates that is award ceremony or is empty
        if candidate[0] in unwanted_candidates or candidate[0] == "":
            to_remove.append(candidate)
        # remove candidates that is similar to the winner of the award (for nominees and presenters)
        elif winner_dict and calc_sim(candidate[0], winner_dict[award]) > 85:
            to_remove.append(candidate)
        else:
            if host_list:
                remove = False
                # remove candidates that is similar to the host of the award (for presenters)
                for host in host_list:
                    if calc_sim(candidate[0], host) > 85:
                        to_remove.append(candidate)
                        remove = True
                        break
                if remove:
                    continue
            # remove candidates that is part name of some award
            for a in all_awards:
                if str1_in_str2(str1=candidate[0], str2=a):
                    to_remove.append(candidate)
                    break
    for candidate in to_remove:
        candidates.remove(candidate)
    
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates

def filter_candidates_for_presenters(candidates: list, award: str, stop_at: int, winner_dict: dict, host_list: list) -> list:
    new_candidates = {}

    for candidate in candidates:
        confidence = candidate[1]
        candidate_name = candidate[2][0] if len(candidate) == 3 and candidate[0] in candidate[2][0] else candidate[0]
     
        possible_jobs, legal_name = wiki.possible_job_list(candidate_name)
        if possible_jobs and (wiki.get_movie_jobs(possible_jobs) or wiki.get_music_jobs(possible_jobs) or 'host' in possible_jobs):
            legal_name = legal_name.lower()
            if legal_name not in new_candidates:
                new_candidates[legal_name] = confidence
            else:
                new_candidates[legal_name] += confidence
        
        if winner_dict[award] in new_candidates:
            new_candidates.pop(winner_dict[award])
        for host in host_list:
            if host in new_candidates:
                new_candidates.pop(host)
        if len(new_candidates) >= stop_at:
            break
    
    return sorted(new_candidates.items(), key=lambda x: x[1], reverse=True)
    

def filter_candidates(candidates: list, award: str, year: int, stop_at: int, winner_dict: dict = None) -> list:
    new_candidates = {}

    for candidate in candidates:
        confidence = candidate[1]
        candidate_name = candidate[2][0] if len(candidate) == 3 and candidate[0] in candidate[2][0] else candidate[0]
        
        possible_jobs, legal_name = wiki.possible_job_list(candidate_name)
        if about_human(award):
            job = get_job(award)
            if job in possible_jobs or job == "":
                legal_name = legal_name.lower()
                if legal_name not in new_candidates:
                    new_candidates[legal_name] = confidence
                else:
                    new_candidates[legal_name] += confidence
        elif about_music(award):
            if possible_jobs and not wiki.get_works(possible_jobs):
                continue
            else:
                search_name = candidate_name
                movie, confidence_ratio = imdb.get_movie_name(search_name, year)
                confidence *= confidence_ratio
                if movie:
                    movie = movie.lower()
                    if movie not in new_candidates:
                        new_candidates[movie] = confidence
                    else:
                        new_candidates[movie] += confidence
        else:
            # if candidate is a person
            if possible_jobs and "director" in possible_jobs:
                movie_list = imdb.find_directors_main_works(legal_name, year)
                if movie_list:
                    confidence /= len(movie_list)
                for movie in movie_list:
                    movie = movie.lower()
                    if movie not in new_candidates:
                        new_candidates[movie] = confidence
                    else:
                        new_candidates[movie] += confidence
            # if candidate is not a person
            else:
                if wiki.get_works(possible_jobs):
                    search_name = legal_name
                else:
                    search_name = name_cleaning(candidate_name)
                movie, confidence_ratio = imdb.get_movie_name(search_name, year)
                confidence *= confidence_ratio
                if movie:
                    movie = movie.lower()
                    if movie not in new_candidates:
                        new_candidates[movie] = confidence
                    else:
                        new_candidates[movie] += confidence
        if winner_dict and winner_dict[award] in new_candidates:
            new_candidates.pop(winner_dict[award])
        if len(new_candidates) >= int(stop_at * 1.25):
            break
    
    return sorted(new_candidates.items(), key=lambda x: x[1], reverse=True)[:stop_at]

def gather_winner(year: int):
    print(f"----------------- Gathering results of winner for {year} -----------------")
    
    winner_stop_at = 1
    with open(f'winner_result_{year}/vote_winner_verb.json', 'r') as f:
        winner_dict = json.load(f)
    label = "winner"
    
    for award in winner_dict:
        candidates = winner_dict[award][label]
        candidates = cluster_candidates(candidates, award, list(winner_dict.keys()))
        candidates = filter_candidates(candidates, award, year - 1, stop_at=winner_stop_at)
        winner_dict[award][label] = candidates
    
    winner_dict = {
        award: data[label][0][0] for award, data in winner_dict.items()
    }
    
    with open(f'winner_result_{year}/winner_result.json', 'w') as f:
        json.dump(winner_dict, f, indent=4)

def gather_all(year: int, winner_on=True, nominee_on=True, host_on=True, presenter_on=True):
    winner_stop_at = 1
    nominee_stop_at = 5
    presenter_stop_at = 2
    
    print(f"----------------- Gathering results of winner for {year} -----------------")
    
    if winner_on:
        gather_winner(year)
    else:
        with open(f'winner_result_{year}/winner_result.json') as f:
            winner_dict = json.load(f)
    
    print(f"----------------- Gathering results of nominees for {year} -----------------")
    
    if nominee_on:
        with open(f'nominee_result_{year}/vote_nominee_verb.json', 'r') as f:
            nominee_dict = json.load(f)
        label = "nominees"
        all_awards = nominee_dict.keys()
        
        for award in nominee_dict:
            if award in no_nominees_wards and label == "nominees":
                nominee_dict[award][label] = []
            candidates = nominee_dict[award][label]
            candidates = cluster_candidates(candidates, award, all_awards, winner_dict)
            candidates = filter_candidates(candidates, award, year - 1, stop_at=nominee_stop_at, winner_dict=winner_dict)
            nominee_dict[award][label] = candidates
        
        nominee_dict = {
            award: [n[0] for n in data[label][:5]] for award, data in nominee_dict.items()
        }
        
        with open(f"nominee_result_{year}/nominee_result.json", "w") as f:
            json.dump(nominee_dict, f, indent=4)
    else:
        with open(f"nominee_result_{year}/nominee_result.json") as f:
            nominee_dict = json.load(f)
    
    print(f"----------------- Gathering results of hosts for {year} -----------------")
    
    if host_on:
        with open(f'host_result_{year}/vote_host_keyword.json', 'r') as f:
            host_list = json.load(f)
            
        host_list = [host[0] for host in host_list[:2]]

        with open(f"host_result_{year}/host_result.json", "w") as f:
            json.dump(host_list, f, indent=4)
    else:
        with open(f'host_result_{year}/host_result.json', 'r') as f:
            host_list = json.load(f)
    
    print(f"----------------- Gathering results of presenters for {year} -----------------")
    
    if presenter_on:
        with open(f'presenter_result_{year}/vote_presenter_verb.json', 'r') as f:
            presenter_dict = json.load(f)
            
        presenter_dict = {
            award: {
                "presenter": presenter_list
            } for award, presenter_list in presenter_dict.items()
        }
        
        label = "presenter"
        all_awards = presenter_dict.keys()
        
        for award in presenter_dict:
            candidates = presenter_dict[award][label]
            candidates = cluster_candidates(candidates, award, all_awards, winner_dict, host_list)
            candidates = filter_candidates_for_presenters(candidates, award, presenter_stop_at, winner_dict, host_list)
            presenter_dict[award][label] = candidates
            
        presenter_dict = {
            award: [n[0] for n in data[label][:2]] for award, data in presenter_dict.items()
        }
        
        with open(f"presenter_result_{year}/presenter_result.json", "w") as f:
            json.dump(presenter_dict, f, indent=4)
    else:
        with open(f"presenter_result_{year}/presenter_result.json") as f:
            presenter_dict = json.load(f)
    
    final_result = {
        "hosts": host_list,
        "award_data": {
            award: {
                "nominees": nominee_dict[award],
                "presenters": presenter_dict[award],
                "winner": winner_dict[award],
            } for award in winner_dict.keys()
        }
    }
    with open(f"gg{year}result.json", "w") as f:
        json.dump(final_result, f, indent=4)
    
    

if __name__ == "__main__":
    gather_all(2013, winner_on=False, nominee_on=False, host_on=False, presenter_on=True)
    # with open('winner_result_2013/vote_winner_verb.json', 'r') as f:
    #     winner_dict = json.load(f)
    # label = "winner"
    
    # for award in winner_dict:
    #     candidates = winner_dict[award][label]
    #     candidates = cluster_candidates(candidates, award, list(winner_dict.keys()))
    #     candidates = filter_candidates(candidates, award, 2013 - 1, stop_at=1)
    #     winner_dict[award][label] = candidates
    
    # with open('try_gather_winner.json', 'w') as f:
    #     json.dump(winner_dict, f, indent=4)
    
    # winner_dict = {
    #     award: data[label][0][0] for award, data in winner_dict.items()
    # }
    
    # with open('winner_result_2013/winner_result1.json', 'w') as f:
    #     json.dump(winner_dict, f, indent=4)
    
    # -----------------------------
    
    # with open('winner_result_2013/winner_result1.json') as f:
    #     winner_dict = json.load(f)
        
    # -----------------------------------------------
    
    # with open('nominee_result_2013/vote_nominee_verb.json', 'r') as f:
    #     nominee_dict = json.load(f)
    # label = "nominees"
    # all_awards = nominee_dict.keys()
    
    # for award in nominee_dict:
    #     if award in no_nominees_wards and label == "nominees":
    #         nominee_dict[award][label] = []
    #     candidates = nominee_dict[award][label]
    #     candidates = cluster_candidates(candidates, award, all_awards, winner_dict)
    #     candidates = filter_candidates(candidates, award, 2013 - 1, stop_at=5, winner_dict=winner_dict)
    #     nominee_dict[award][label] = candidates
    
    # with open('try_gather.json', 'w') as f:
    #     json.dump(nominee_dict, f, indent=4)
    
    # nominee_dict = {
    #     award: [n[0] for n in data[label][:5]] for award, data in nominee_dict.items()
    # }
    
    # with open(f"nominee_result_2013/nominee_result1.json", "w") as f:
    #     json.dump(nominee_dict, f, indent=4)
        
    # -----------------------------
    
    # award = "best motion picture - drama"
    
    # candidates = nominee_dict[award][label]
    # candidates = cluster_candidates(candidates, award, all_awards, winner_dict)
    # print(json.dumps(candidates, indent=4))
    
    # candidates = filter_candidates(candidates, award, 2013 - 1, stop_at=6, winner_dict=winner_dict)
    # print(json.dumps(candidates, indent=4))
    
    # with open(f"nominee_result_2013/nominee_result1.json") as f:
    #     nominee_dict = json.load(f)
    
    # -----------------------------------------------
    
    # with open('host_result_2013/host_final.json', 'r') as f:
    #     host_list = json.load(f)
    
    # with open('presenter_result_2013/vote_presenter_verb.json', 'r') as f:
    #     presenter_dict = json.load(f)
        
    # presenter_dict = {
    #     award: {
    #         "presenter": presenter_list
    #     } for award, presenter_list in presenter_dict.items()
    # }
    
    # label = "presenter"
    # all_awards = presenter_dict.keys()
    
    # for award in presenter_dict:
    #     candidates = presenter_dict[award][label]
    #     candidates = cluster_candidates(candidates, award, all_awards, winner_dict, host_list)
    #     candidates = filter_candidates_for_presenters(candidates, award, 2, winner_dict, host_list)
    #     presenter_dict[award][label] = candidates
    
    # with open('try_gather_presenter.json', 'w') as f:
    #     json.dump(presenter_dict, f, indent=4)
        
    # presenter_dict = {
    #     award: [n[0] for n in data[label][:2]] for award, data in presenter_dict.items()
    # }
    
    # with open(f"presenter_result_2013/presenter_result1.json", "w") as f:
    #     json.dump(presenter_dict, f, indent=4)
        
    # -----------------------------

    
    # award = "best performance by an actor in a supporting role in a motion picture"
    
    # candidates = presenter_dict[award][label]
    # candidates = cluster_candidates(candidates, award, all_awards, winner_dict)
    # print(json.dumps(candidates, indent=4))
    
    # candidates = filter_candidates_for_presenters(candidates, award, 5, winner_dict)
    # print(json.dumps(candidates, indent=4))
    
    
