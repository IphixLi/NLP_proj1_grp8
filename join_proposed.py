import spacy
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import pairwise_distances
from sklearn.feature_extraction.text import TfidfVectorizer
import re

# Load the spaCy English language model
nlp = spacy.load("en_core_web_sm")

files=["best","wins","clusters","goes","nominee","receives","winner"]

confident=open("proposed_awards/combined_confident.txt", "w")
no_confident=open("proposed_awards/combined_not_confident.txt", "w")
combined=open("proposed_awards/proposed_combined.txt", "w")
no_combined=open("proposed_awards/proposed_no_combined.txt", "w")


stage_confident=[]
stage_no_confident=[]

for file in files:
    with open(f'proposed_awards/proposed_from_{file}.txt',encoding="utf-8", errors="ignore") as f:
        data=f.readlines()
        for line in data:
            if line.strip()[-1]=='0':
                stage_no_confident.append(line)
            else:
                stage_confident.append(line)

name_map={"yes":stage_confident,"no":stage_no_confident}
for stage in name_map.keys():
    # Tokenize the texts using spaCy and convert them into a list of tokens
    tokenized_texts = [doc for doc in nlp.pipe(name_map[stage])]

    # Create a list of space-separated tokens
    tokenized_texts_str = [" ".join([token.text for token in doc]) for doc in tokenized_texts]

    # Create a TF-IDF vectorizer
    vectorizer = TfidfVectorizer()

    # Vectorize the texts and convert to a dense matrix
    X = vectorizer.fit_transform(tokenized_texts_str).toarray()


    # Calculate Jaccard similarity between all pairs of texts
    jaccard_similarities = pairwise_distances(X, metric="jaccard")

    # Apply hierarchical clustering based on Jaccard similarity
    clustering = AgglomerativeClustering(n_clusters=None, distance_threshold=0.4, linkage='average', affinity='precomputed').fit(jaccard_similarities)

    # Get the cluster labels
    cluster_labels = clustering.labels_

    # Group the texts based on the cluster labels
    grouped_texts = {}
    for label, text in zip(cluster_labels, name_map[stage]):
        if label in grouped_texts:
            grouped_texts[label].append(text)
        else:
            grouped_texts[label] = [text]

    for label, group in grouped_texts.items():
        if stage=='yes':
            confident.write(f"Cluster {label}:\n")
            cluster = []
            for text in group:
                cluster.append(re.split(r',(?![ ])', text))
                confident.write(f"    {text}")
            confident.write("\n")
            # for text in group:
            #     confident.write(f"{text}")
            max_count_item = max(cluster, key=lambda x: x[1])
            combined.write(",".join(max_count_item))
        else:
            no_confident.write(f"Cluster {label}:\n")
            cluster = []
            for text in group:
                cluster.append(re.split(r',(?![ ])', text))
                no_confident.write(f"    {text}")
            no_confident.write("\n")

            max_count_item = max(cluster, key=lambda x: int(x[1]))
            # if something had many iterations or was mentioned multiple times, it is more likely that it's a W
            if len(cluster) > 1 or int(max_count_item[1]) > 40:
                combined.write(",".join(max_count_item))
            else:
                no_combined.write(",".join(max_count_item))

confident.close()
no_confident.close()
combined.close()
no_combined.close()


