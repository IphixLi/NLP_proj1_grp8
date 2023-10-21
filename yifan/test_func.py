from data_preprocess import extract_retweets
import time

tweets = [
    {
        'new_text': "RT @goldenglobes: Best Director - Ben Affleck (@BenAffleck) - Argo - #GoldenGlobes",
    },
    {
        'new_text': "Congratz beautiful! RT @TVGuide: Best actress for comedy/musical goes to Jennifer Lawrence #GoldenGlobes",
    },
    {
        'new_text': "RT @AmazedByRobsten: RT @goldenglobes: From the pressroom: Jodie Foster says that she's not retiring from acting. She's looking forward to directing more.",
    },
    {
        'new_text': "RT @MsAmberPRiley: Truth RT @bernardx: you could hear a pin drop. Who else can command that kind of respect and admiration. Very few.#GoldenGlobes",
    }
]

if __name__ == '__main__':
    for tweet in tweets:
        extract_retweets(tweet)
        print(tweet)
        print()