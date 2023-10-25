import wikipedia

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


if __name__ == "__main__":
    f = open("proposed_awards/proposed_combined.txt",encoding="utf-8", errors="ignore")
    with open(f"proposed_awards/filter_combined.txt", "w") as d:
        values=f.readlines()
        for line in values:
            try:
                content = wikipedia.page(line.strip()).content
                d.write(f"check: {line} \n")
                d.write(f"{content} \n")
                    
                
                # if not check_validity(name, content):
                #     print("invalid")
                #     return []

                # return most_frequent_term(content, terms)
            except wikipedia.exceptions.DisambiguationError as e:
                d.write(f"check: {line} \n")
                d.write(f"wikipedia: Ambiguous. Possible matches include: {e.options} \n")
            except wikipedia.exceptions.PageError:
                d.write(f"check: {line} \n")
                d.write(f"wikipedia: The page does not exist \n")
            except Exception as e:
                d.write(f"check: {line} \n")
                d.write(f"wikipedia: {e} \n")