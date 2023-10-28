import wikipedia
import time

from handle_names import remove_triple_letters

class WikiSearch:
    def __init__(self) -> None:
        self.terms = ['actor', 'actress', 'director']
        self.logs = []
        self.job_list_cache = {}
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
        
        print("---------------WikiSearch logs:---------------")
        print("\n".join(self.logs))

    def check_validity(self, name, content):
        for n in name.lower().split():
            if content.lower().find(n) != -1:
                return True
        return False

    def most_frequent_term(self, content, terms) -> list:
        count_map = {term: content.lower().count(term) for term in terms}
        counts = sorted(count_map.items(), key=lambda x: x[1], reverse=True)
        max_count = counts[0][1]
        
        if max_count > 0:
            most_frequent = [term for term, count in counts if count == max_count]
        else:
            most_frequent = []
        return most_frequent
    
    def quick_search(self, name: str) -> list:
        try:
            search_results = wikipedia.search(name, results=3)
            self.logs.append(f"- search_results: {search_results} for '{name}'")
            return search_results
        except Exception as e:
            self.logs.append(f"- wikipedia [quick_search]: {e} for '{name}'")
            return []
    
    def quick_summary(self, name: str, search_name: str) -> list:
        content = ""
        if (name.lower(), search_name.lower()) in self.summary_cache:
            return self.summary_cache[(name.lower(), search_name.lower())]
        try:
            if search_name.lower() in self.content_cache:
                content = self.content_cache[search_name.lower()]
            else:
                content = wikipedia.summary(search_name, sentences=5, auto_suggest=False)
                self.content_cache[search_name.lower()] = content
            if not content or not self.check_validity(name, content):
                self.summary_cache[(name.lower(), search_name.lower())] = []
                return []
        
            res = self.most_frequent_term(content, self.terms)
            self.summary_cache[(name.lower(), search_name.lower())] = res
            return res
        except wikipedia.exceptions.DisambiguationError as e:
            self.logs.append(f"- wikipedia: Ambiguous. Possible matches include: {e.options} for '{name}'")
            self.summary_cache[(name.lower(), search_name.lower())] = []
            return []
        except wikipedia.exceptions.PageError:
            self.logs.append(f"- wikipedia: The page does not exist: '{name}'")
            self.summary_cache[(name.lower(), search_name.lower())] = []
            return []
        except Exception as e:
            self.logs.append(f"- wikipedia: {e} for '{name}'")
            self.summary_cache[(name.lower(), search_name.lower())] = []
            return []
        

    def possible_job_list(self, name) -> list:
        start = time.time()
        if name.lower() in self.job_list_cache:
            self.count["cache_hit"] += 1
            return self.job_list_cache[name.lower()]
        
        self.count["cache_miss"] += 1
        summary_results = self.quick_summary(name, name)
        if summary_results:
            self.job_list_cache[name.lower()] = summary_results
            self.count["total_time"] += time.time() - start
            return summary_results
        
        search_results = self.quick_search(name)
        for search_name in search_results[:3]:
            summary_results = self.quick_summary(name, search_name)
            if summary_results:
                self.job_list_cache[name.lower()] = summary_results
                self.count["total_time"] += time.time() - start
                return summary_results
            
        self.job_list_cache[name.lower()] = []
        self.count["total_time"] += time.time() - start
        return []
    
    def write_logs(self):
        if self.logs:
            with open("wiki_search_logs.txt", "w") as f:
                f.write("\n".join(self.logs))
    
if __name__ == "__main__":
    names = ["Lee Ang", "ah Lee Ang", "Ang Lee", "Booo Ang Lee", "Lee Ang", "Ang Lee", "Boooooooo Ang Lee", "Boooooooo Ang Lee", "Ang LEE", "jennifer lawrence"]
    wiki = WikiSearch()
    for name in names:
        result = wiki.possible_job_list(name)
        print(f"'{name}' is likely an actor/actress or director: {result}")
    wiki.print_stats()
    