import json

from similarity import compute_similarity

### TODO: delete this
awards = json.load(open("gg2013answers.json"))['award_data'].keys()

class Vote:
    def __init__(self, awards):
        self.awards = awards
        self.results = {
            award: {
                'winner': {},
                'nominees': {},
            } for award in awards
        }

    def choose_award_to_vote(self, awards: list, award_candidates: list):
        scores = {}
        for award in awards:
            scores[award] = compute_similarity(award, award_candidates)
        
        res = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        highest_score = res[0][1]

        ratio = [1, 2, 6]
        for i in range(len(res)):
            res[i] = (res[i][0], highest_score / ratio[i])
        return res
    
    def vote(self, res,  winner_candidates, nominee_candidates):
        for candidate in winner_candidates:
            for award, score in res:
                if candidate in self.results[award]['winner']:
                    self.results[award]['winner'][candidate] += score
                else:
                    self.results[award]['winner'][candidate] = score
        
        for candidate in nominee_candidates:
            for award, score in res:
                if candidate in self.results[award]['nominees']:
                    self.results[award]['nominees'][candidate] += score
                else:
                    self.results[award]['nominees'][candidate] = score
                

    def vote_for_awards(self, awards: list, tweets: list):
        for tweet in tweets:
            if 'award_candidates' in tweet:
                vote_res = self.choose_award_to_vote(awards, tweet['award_candidates'])
                self.vote(vote_res, tweet.get('winner_candidates', []), tweet.get('nominee_candidates', []))
                
    def get_results(self):
        for award in self.awards:
            self.results[award]['winner'] = sorted(self.results[award]['winner'].items(), key=lambda x: x[1], reverse=True)[:10]
            self.results[award]['nominees'] = sorted(self.results[award]['nominees'].items(), key=lambda x: x[1], reverse=True)[:20]
        return self.results

if __name__ == "__main__":
    tweets = json.load(open("nominees?.json"))
    
    v = Vote(awards)
    v.vote_for_awards(awards, tweets)
    res = v.get_results()
    
    with open("try_vote_nominees.json", "w") as f:
        json.dump(res, f, indent=4)
        