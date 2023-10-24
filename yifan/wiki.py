import wikipedia

terms = ['actor', 'actress', 'director']

def check_validity(name, content):
    for n in name.lower().split():
        if content.lower().find(n) == -1:
            return False
    return True

def most_frequent_term(content, terms) -> list:
    count_map = {term: content.lower().count(term) for term in terms}
    counts = sorted(count_map.items(), key=lambda x: x[1], reverse=True)
    max_count = counts[0][1]
    
    if max_count > 0:
        most_frequent = [term for term, count in counts if count == max_count]
    else:
        most_frequent = []
    return most_frequent

def possible_job_list(name) -> list:
    try:
        content = wikipedia.page(name).content
        
        if not check_validity(name, content):
            print("invalid")
            return []

        return most_frequent_term(content, terms)
    except wikipedia.exceptions.DisambiguationError as e:
        print(f"wikipedia: Ambiguous. Possible matches include: {e.options}")
        return []
    except wikipedia.exceptions.PageError:
        print("wikipedia: The page does not exist")
        return []
    except Exception as e:
        print(f"wikipedia: {e}")
        return []
    
if __name__ == "__main__":
    name = "Lee Ang"
    result = possible_job_list(name)
    print(f"'{name}' is likely an actor/actress or director: {result}")