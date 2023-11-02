'''Version 0.4'''
import json

from data_preprocess import TweetsPreprocessor
from winner import Winner
from nominee import Nominee
from presenter import Presenter
from host import Host
from gather_result import gather_all, gather_winner
import unicodedata

import main_awards

def clean_text(text: str) -> str:
    normalized = unicodedata.normalize('NFD', text)
    stripped = ''.join(c for c in normalized if not unicodedata.combining(c))
    return stripped


def get_hosts(year):
    '''Hosts is a list of one or more strings. Do NOT change the name
    of this function or what it returns.'''
    # Your code here
    hosts = json.load(open(f"host_result_{year}/host_result.json"))

    # with open(f"host_result_{year}/host_result.json", "w") as f:
    #     json.dump(hosts, f, indent=4)
    
    return hosts

def get_awards(year):
    '''Awards is a list of strings. Do NOT change the name
    of this function or what it returns.'''
    # Your code here
    filename=f'gg{year}.json'

    return main_awards.get_awards(filename)

def get_nominees(year):
    '''Nominees is a dictionary with the hard coded award
    names as keys, and each entry a list of strings. Do NOT change
    the name of this function or what it returns.'''
    # Your code here
    
    nominees = json.load(open(f"nominee_result_{year}/nominee_result.json"))
    
    return nominees

def get_winner(year):
    '''Winners is a dictionary with the hard coded award
    names as keys, and each entry containing a single string.
    Do NOT change the name of this function or what it returns.'''
    # Your code here
    winners = json.load(open(f"winner_result_{year}/winner_result.json"))

    
    return winners

def get_presenters(year):
    '''Presenters is a dictionary with the hard coded award
    names as keys, and each entry a list of strings. Do NOT change the
    name of this function or what it returns.'''
    # Your code here
    presenters = json.load(open(f"presenter_result_{year}/presenter_result.json"))
    
    return presenters

def pre_ceremony():
    '''This function loads/fetches/processes any data your program
    will use, and stores that data in your DB or in a json, csv, or
    plain text file. It is the first thing the TA will run when grading.
    Do NOT change the name of this function or what it returns.'''
    # Your code here
    print("Pre-ceremony processing complete.")
    return

def main():
    '''This function calls your program. Typing "python gg_api.py"
    will run this function. Or, in the interpreter, import gg_api
    and then run gg_api.main(). This is the second thing the TA will
    run when grading. Do NOT change the name of this function or
    what it returns.'''
    # Your code here
    year = 2013
    input_dataset_filename = "gg2013.json"
    answer_filename = "gg2013answers.json"
    debug = False
    
    # data preprocessing
    tp = TweetsPreprocessor(tweets_data_file=input_dataset_filename, year=year)
    tp.load_all_tweets(debug=debug)
    
    # awards list for winner, nominee, presenter
    awards = json.load(open(answer_filename))['award_data'].keys()
    
    winner_tweets = tp.load_tweets(key='normal_tweets')
    win_extractor = Winner(winner_tweets, awards=awards, year=year)
    win_extractor.extract_or_load(debug=debug)
    win_extractor.do_vote(debug=debug)

    gather_winner(year)
    
    nominee_tweets = tp.load_tweets(key='should_tweets') + tp.load_tweets(key='normal_tweets') + tp.load_tweets(key='guess_tweets')
    nominee_extractor = Nominee(nominee_tweets, awards, year=year)
    nominee_extractor.extract_or_load(debug=debug)
    nominee_extractor.do_vote()
    
    host_tweets = tp.load_tweets(key='normal_tweets')
    host_extractor = Host(host_tweets, year=year)
    host_extractor.extract_or_load(debug=debug)
    host_extractor.do_vote()
    
    presenter_tweets = tp.load_tweets(key='normal_tweets')
    presenter_extractor = Presenter(presenter_tweets, awards, year=year)
    presenter_extractor.extract_or_load(debug=debug)
    presenter_extractor.do_vote()
    
    gather_all(year, winner_on=False)
    return

if __name__ == '__main__':
    main()
