import wikipedia
import time
import re
import string

from handle_names import name_cleaning, calc_sim, clean_text, remove_parathesis, count_whole_word_occurrences

class WikiSearch: 
    def __init__(self) -> None:
        self.movie_jobs = ["actor", "actress", "director"]
        self.music_jobs = ["singer", "composer"]
        self.works = ["book", "novel", "album", "series", 'show', 'song']
        self.terms = ['actor', 'actress', 'director', 'filmmaker', 'host', 'singer', 'composer', 'songwriter', 'band', 'musical duo'] + self.works
        self.terms_to_jobs = {
            'actor': 'actor',
            'actress': 'actress',
            'director': 'director',
            'filmmaker': 'director',
            'host': 'host',
            'singer': 'singer',
            'composer': 'composer',
            'songwriter': 'composer',
            'musical duo': 'singer',
            'band': 'singer',
        }
        for work in self.works:
            self.terms_to_jobs[work] = 'work'
        self.logs = []
        self.job_list_cache = {
            'archie punjabi': (['actress'], 'archie panjabi'),
        }
        self.summary_cache = {}
        self.content_cache = {}
        self.count = {
            "cache_hit": 0,
            "cache_miss": 0,
            "total_time": 0, # for cache_miss
        }
    
    def __del__(self):
        self.print_stats()
    
    def print_stats(self):
        print("---------------WikiSearch stats:---------------")
        for k, v in self.count.items():
            print(f"{k}: {v}")
        
        # print("---------------WikiSearch logs:---------------")
        # print("\n".join(self.logs))

    def check_validity(self, name, content):
        pattern = r'[\s' + re.escape(string.punctuation) + r']+'
        words = re.split(pattern, name)
        for n in words:
            if n and content.lower().find(n.lower()) == -1:
                return False
        return True
    
    def collect_job_counts(self, content, terms) -> dict:
        job_counts = {}
        for term in terms:
            job = self.terms_to_jobs[term]
            job_counts[job] = job_counts.get(job, 0) + count_whole_word_occurrences(content.lower(), term)
        return job_counts

    def most_frequent_term(self, content, terms) -> list:
        count_map = self.collect_job_counts(content, terms)
        self.logs.append(str(count_map))
        counts = sorted(count_map.items(), key=lambda x: x[1], reverse=True)
        max_count = counts[0][1]
        
        if max_count > 0:
            most_frequent = [term for term, count in counts if count == max_count]
        else:
            most_frequent = []
        return most_frequent
    
    def quick_search(self, name: str) -> list:
        try:
            search_results, suggestion = wikipedia.search(name, results=3, suggestion=True)
            if suggestion:
                suggestion = suggestion.title()
                search_results.insert(0, suggestion)
                search_results = search_results[:3]
            self.logs.append(f"- search_results: {search_results} for '{name}'")
            return search_results
        except Exception as e:
            self.logs.append(f"- wikipedia [quick_search]: {e} for '{name}'")
            return []
    
    def recheck_content(self, search_name: str) -> (list, bool):
        self.logs.append(f"recheck_content: {search_name}")
        if search_name.lower() in self.content_cache:
            content = self.content_cache[search_name.lower()]
            res = self.most_frequent_term(content, self.terms)
            self.summary_cache[(search_name.lower(), search_name.lower())] = (res, True)
            return res, True
        else:
            return self.quick_summary(search_name, search_name, need_validity=False, check_space=False)
    
    def quick_summary(self, name: str, search_name: str, need_validity=True, check_space=True) -> (list, bool):
        self.logs.append(f"quick_summary: {name}, {search_name}")
        if check_space and search_name.count(" ") == 0:
            self.logs.append(f"- wikipedia: No space in search name: '{search_name}'")
            return [], False
        
        content = ""
        if (name.lower(), search_name.lower()) in self.summary_cache:
            return self.summary_cache[(name.lower(), search_name.lower())]
        try:
            if search_name.lower() in self.content_cache:
                content = self.content_cache[search_name.lower()]
            else:
                content = wikipedia.summary(search_name, chars=150, auto_suggest=False)
                self.content_cache[search_name.lower()] = content
            self.logs.append(f"- wikipedia: Found content for '{search_name}': '{content}'")
            if not content or (need_validity and not self.check_validity(name, content)):
                if not content:
                    self.logs.append(f"- wikipedia: No content found for '{name}'")
                else:
                    self.logs.append(f"- wikipedia: Invalid content found for '{search_name}', name: '{name}', need_validity: '{need_validity}'")
                self.summary_cache[(name.lower(), search_name.lower())] = [], self.check_validity(name, content) if need_validity else True
                return [], self.check_validity(name, content) if need_validity else True
        
            res = self.most_frequent_term(content, self.terms)
            self.summary_cache[(name.lower(), search_name.lower())] = (res, True)
            return res, True
        except wikipedia.exceptions.DisambiguationError as e:
            self.logs.append(f"- wikipedia: Ambiguous. Possible matches include: {e.options} for '{name}'")
            self.summary_cache[(name.lower(), search_name.lower())] = ([], False)
            return [], False
        except wikipedia.exceptions.PageError:
            self.logs.append(f"- wikipedia: The page does not exist: '{name}'")
            self.summary_cache[(name.lower(), search_name.lower())] = ([], False)
            return [], False
        except Exception as e:
            self.logs.append(f"- wikipedia: {e} for '{name}'")
            self.summary_cache[(name.lower(), search_name.lower())] = ([], False)
            return [], False
        
    def possible_job_list(self, name, need_name_cleaning=True) -> (list, str):
        start = time.time()
        if need_name_cleaning:
            name = name_cleaning(name)
        if name.lower() in self.job_list_cache:
            self.count["cache_hit"] += 1
            return self.job_list_cache[name.lower()]
        
        self.count["cache_miss"] += 1
        summary_results, is_valid = self.quick_summary(name, name)
        if is_valid:
            name = clean_text(name)
            name = remove_parathesis(name)
            
            self.job_list_cache[name.lower()] = (summary_results, name)
            self.count["total_time"] += time.time() - start
            return summary_results, name
        
        search_results = self.quick_search(name)
        for search_name in search_results[:3]:
            # this means the search result is the same as the name, meaning the name is a valid name (so we should recheck it)
            if search_name.lower() == name.lower():
                summary_results, is_valid = self.recheck_content(search_name)
            else:
                summary_results, is_valid = self.quick_summary(name, search_name, need_validity=calc_sim(name, remove_parathesis(search_name)) < 85)
            if is_valid:
                search_name = clean_text(search_name)
                search_name = remove_parathesis(search_name)
                
                self.job_list_cache[name.lower()] = (summary_results, search_name)
                self.count["total_time"] += time.time() - start
                return summary_results, search_name
            
        self.job_list_cache[name.lower()] = ([], "")
        self.count["total_time"] += time.time() - start
        return [], ""

    def get_movie_jobs(self, job_list: list) -> list:
        return [job for job in job_list if job in self.movie_jobs]

    def get_music_jobs(self, job_list: list) -> list:
        return [job for job in job_list if job in self.music_jobs]
    
    def get_works(self, job_list: list) -> list:
        return [job for job in job_list if job == 'work']
    
    def write_logs(self):
        if self.logs:
            with open("wiki_search_logs.txt", "w") as f:
                f.write("\n".join(self.logs))
    
if __name__ == "__main__":
    # names = ["Lee Ang", "ah Lee Ang", "Ang Lee", "Booo Ang Lee", "Lee Ang", "Ang Lee", "Boooooooo Ang Lee", "Boooooooo Ang Lee", "Ang LEE", "jennifer lawrence", "django", "j. lo.", "j-lo", "maggie smith"]
    # names = ["adele", "bon jovi", "the civil wars", "safe sound", "taylor", "taylor swift", "john williams"]
    # names = ['the girl', 'hatfields mccoys', 'game change', 'political animals', 'the hour']
    names = ['jimmy fallon']
    wiki = WikiSearch()
    for name in names:
        result, legal_name = wiki.possible_job_list(name)
        print(f"'{name}' is likely an actor/actress or director: {result}, legal name: {legal_name}")
    wiki.print_stats()
    