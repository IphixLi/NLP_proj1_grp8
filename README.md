# Github address
```
https://github.com/IphixLi/NLP_proj1_grp8.git
```

# Package install

Please run the following command to get libraries and model files
```
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m spacy download en_core_web_md
```

# Getting awards

- awards names are given as list by invoking main_awards.py file with file which contain tweets.
for example:

```python main_awards.py gg2013.json```

1. We identified patterns through which the awards are mentioned in the tweets. we then created scripts that would allow us to extract probable award names. to inspect the patterns per given awards, see files marked by award names in ***inspect_files*** folder.

for some awards, we some official names of the awards were not used in the tweets such as awards related to individual performances. for example:

```Best performance in motion picture by an actor```
had tweets with:
```Best actor in motion picture```
hence we had to manipulate awards to handle these cases.

we also normalized all award names to be lowercase.



2. we then combined all probable award names and put them in clusters of similarities such that we are able to capture the most likely true name of the award. We used Spacy library which allowed us to vectorize text into tokens and cluster award names based on Jaccard similarity.
to inspect cluster patterns per proposed awards, see clusters.txt file in ***inspect_files*** folder.

3. from the clusters we got the awards name which had high count from tweets. we followed the heuristic that is the award name was mentioned many times in the tweets it is likely that it was mentioned differently by users such as minor pronounciation. We also looked at awards that had no clusters but was hightly mentioned in the tweets.
