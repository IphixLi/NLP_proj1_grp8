import spacy
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import pairwise_distances
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import json

# Load the spaCy English language model
nlp = spacy.load("en_core_web_sm")

f = open('stage/winner_keyword.json',encoding="utf-8", errors="ignore")
data=json.load(f)

# Extract the keys (text items) from the dictionary
texts = list(data.keys())

# Tokenize the texts using spaCy and convert them into a list of tokens
tokenized_texts = [doc for doc in nlp.pipe(texts)]

# Create a list of space-separated tokens
tokenized_texts_str = [" ".join([token.text for token in doc]) for doc in tokenized_texts]

# Create a TF-IDF vectorizer
vectorizer = TfidfVectorizer()

# Vectorize the texts and convert to a dense matrix
X = vectorizer.fit_transform(tokenized_texts_str).toarray()


# Calculate Jaccard similarity between all pairs of texts
jaccard_similarities = pairwise_distances(X, metric="jaccard")

# Apply hierarchical clustering based on Jaccard similarity
clustering = AgglomerativeClustering(n_clusters=None, distance_threshold=0.2, linkage='average', affinity='precomputed').fit(jaccard_similarities)

# Get the cluster labels
cluster_labels = clustering.labels_

# Group the texts based on the cluster labels
grouped_texts = {}
for label, text in zip(cluster_labels, texts):
    if label in grouped_texts:
        grouped_texts[label].append(text)
    else:
        grouped_texts[label] = [text]

with open("clusters/winner_clusters.txt", "w") as file:
    with open("proposed_awards/proposed_from_winner.txt", "w") as d:
        for label, group in grouped_texts.items():
            file.write(f"Cluster {label}:\n")
            cluster = []
            for text in group:
                cluster.append([text, data[text]])
                file.write(f"    {text} (Count: {data[text]})\n")
            file.write("\n")
            max_count_item = max(cluster, key=lambda x: x[1])

            # if something had many iterations or was mentioned multiple times, it is more likely that it's a W
            if len(cluster) > 1 or max_count_item[1] > 10:
                max_count_item.append('1')
            else:
                max_count_item.append('0')

            # proposed award, instances, confidence
            d.write(f'{max_count_item[0]},{str(max_count_item[1])},{max_count_item[2]}\n')