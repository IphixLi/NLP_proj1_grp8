import json

def tokenize(text) -> set:
    """Tokenize the text."""
    tokens = text.lower().split()
    # Remove punctuation from each token
    tokens = set([''.join(e for e in token if e.isalnum()) for token in tokens])
    return tokens

def jaccard_similarity(set1, set2):
    """Compute the Jaccard Similarity between two set of strings."""
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union

def compute_similarity_for_one_candidate(award, candidate):
    award_tokens = tokenize(award)
    return jaccard_similarity(award_tokens, tokenize(candidate))

def compute_similarity(award, candidates):
    """Compute a single similarity score for a list of candidates against a given award."""
    if len(candidates) == 0:
        return 0
    
    award_tokens = tokenize(award)
    similarities = [jaccard_similarity(award_tokens, tokenize(candidate)) for candidate in candidates]
    return max(similarities)


if __name__ == '__main__':
    award = "best screenplay - motion picture"
    tweets = json.load(open("pattern_match.txt"))
    print(len(tweets))
    for tweet in tweets:
        if 'award_candidates' in tweet:
            award_candidates = tweet['award_candidates']
            tweet["score"] = compute_similarity(award, award_candidates)
            if tweet["score"] > 0.5:
                print(tweet['new_text'])
                print(tweet["score"])
                print()

    print(json.dumps(tweets, indent=4))
