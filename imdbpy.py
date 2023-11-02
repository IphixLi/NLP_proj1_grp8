import re
import time
from imdb import Cinemagoer, IMDbError
import json

from handle_names import clean_text, name_cleaning

class IMDBSearch:
    def __init__(self):
        self.ia = Cinemagoer()
        self.person_cache = {}
        self.movie_cache = {}
        self.logs = []
        self.count = {
            "total_time": 0,
        }
    
    def __del__(self):
        self.print_stats()
        
    def print_stats(self):
        print("---------------IMDBSearch stats:---------------")
        for k, v in self.count.items():
            print(f"{k}: {v}")
        
        # print("---------------IMDBSearch logs:---------------")
        # print("\n".join(self.logs))
        
    
    def get_person_name(self, name: str, need_confidence=False, need_name_cleaning=True):
        try:
            start = time.time()
            if need_name_cleaning:
                name = name_cleaning(name)
            person = self.ia.search_person(name, results=1)
            self.count["total_time"] += time.time() - start
            if not person:
                if need_confidence:
                    return "", 0
                return name
            
            if need_confidence:
                return clean_text(str(person[0])), 1
            return clean_text(str(person[0]))  
        except IMDbError as e:
            self.logs.append(f"IMDBError: {e}")
            if need_confidence:
                return name, 0.5
            return name

    def get_movie_name(self, name: str, year: int) -> (str, float):
        """ Returns the movie name from the given string and the given year should be within the produced year range """
        try:
            start = time.time()
            confidence_ratio_list = [4,3,2,1]
            attempts = 0
            
            if name.lower() in self.movie_cache:
                movies = self.movie_cache[name.lower()]
            else:
                movies = self.ia.search_movie(name, results=3)
                self.movie_cache[name.lower()] = movies
            self.count["total_time"] += time.time() - start
            
            for movie in movies:
                if year in self.extract_years_from_movie(movie):
                    return clean_text(str(movie)), confidence_ratio_list[attempts]
                attempts += 1
            
            start = time.time()
            
            search_name = f"{name} {year}"
            if search_name.lower() in self.movie_cache:
                movies = self.movie_cache[search_name.lower()]
            else:
                movies = self.ia.search_movie(f"{name} {year}", results=1)
                self.movie_cache[search_name.lower()] = movies
            self.count["total_time"] += time.time() - start
                
            if not movies:
                return "", 0
            movie = movies[0]
            if year in self.extract_years_from_movie(movie):
                return clean_text(str(movie)), confidence_ratio_list[attempts]
            return "", 0
        except IMDbError as e:
            self.logs.append(f"IMDBError: {e}")
            return name, 0.5

    def extract_years_from_movie(self, movie) -> list:
        movie_repr = repr(movie)
        
        # Locate the "title:_" part
        title_index = movie_repr.find("title:_")
        if title_index != -1:
            title_onwards = movie_repr[title_index:]
            year_pattern = r'\((\d{4})\)'
            years = [int(match.group(1)) for match in re.finditer(year_pattern, title_onwards)]
            if len(years) == 1:
                return years
            elif len(years) == 2:
                return list(range(min(years), max(years) + 1))
        return []
    
    def find_directors_main_works(self, director_name: str, year: int) -> list:
        """ returns the main works of the given director in that year (in cleaned str)
        
        requires: director_name is a valid director name
        """
        try:
            start = time.time()
            # Search for the director
            if director_name.lower() in self.person_cache:
                self.logs.append(f"get cache for {director_name.lower()}")
                people = self.person_cache[director_name.lower()]
            else:
                people = self.ia.search_person(director_name, results=1)
                self.person_cache[director_name.lower()] = people
                
            if not people:
                return []

            # Assuming the first search result is the correct director
            director = people[0]
            if 'filmography' not in director:
                self.logs.append(f"updating filmography for {str(director)}")
                self.ia.update(director, info=['filmography'])
            else:
                self.logs.append(f"get filmography from cache for {str(director)}")
            self.count["total_time"] += time.time() - start

            # Filter for directorial works
            main_works = []
            if 'director' in director.get('filmography'):
                directed_movies = director.get('filmography').get('director')
                main_works = [
                    clean_text(str(movie)) for movie in directed_movies if year in self.extract_years_from_movie(movie)
                ]

            return main_works
        except IMDbError as e:
            self.logs.append(f"IMDBError: {e}")
            return []


if __name__ == "__main__":
    start = time.time()
    imdb = IMDBSearch()
    movie_searches = ["django", "unchained", "zero dark", "modern family", "silver linings", "linc", "les mis", "les", "amore australia"]
    for movie_search in movie_searches:
        print(f"{movie_search} -> {imdb.get_movie_name(movie_search, 2012)}")
    end = time.time()
    print(f"Time taken: {end - start}")
    