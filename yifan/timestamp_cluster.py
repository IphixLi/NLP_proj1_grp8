import json
import os
import math
import numpy as np
from sklearn.cluster import DBSCAN

# def modified_sigmoid(x, a=1, b=0.001):
#     """
#     :param x: the distance or difference value
#     :param a: controls the steepness of the curve (larger values make the curve steeper)
#     :param b: scales the x value to control at what point the decrease becomes sharper
#     :return: sigmoid value
#     """
#     return 1 / (1 + math.exp(a * (x * b - 1)))

class TimestampCluster:
    def __init__(self, data=None, load_saved=False, apply_filter=True):
        self.filename = "timestamp_data.json" if not apply_filter else "filtered_timestamp_data.json"
        self.folder = "timestamp_result"
        self.apply_filter = apply_filter
        self.unsure_ratio = 0.2
        self.fuzzy_ratio = 0.5
        if load_saved:
            self.load_data()
            self.timestamp_to_award = {self.calculate_top_avg(v): k for k, v in self.timestamp_list.items()}
        else:
            self.timestamp_list = data
            if apply_filter:
                self.save_data(filename="timestamp_data.json")
                self.filter_outliers()
                self.timestamp_list = {k: v for k, v in sorted(self.timestamp_list.items(), key=lambda x: x[1][0])}
            self.timestamp_to_award = {self.calculate_top_avg(v): k for k, v in self.timestamp_list.items()}
            self.save_data(filename=self.filename)

    def get_timestamp_to_award(self):
        return self.timestamp_to_award

    def save_data(self, filename):
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
            
        with open(f"{self.folder}/{filename}", 'w') as file:
            json.dump(self.timestamp_list, file, indent=4)
        print(f"Saved timestamp cluster data to {self.folder}/{filename}")

    def load_data(self):
        with open(f"{self.folder}/{self.filename}", 'r') as file:
            self.timestamp_list = json.load(file)
    
    # def calculate_confidence(self, min_distance, cluster_range, min_distance_threshold=90000):
    #     half_range = cluster_range / 2
    #     if min_distance > half_range and min_distance > min_distance_threshold:  # 90 seconds in ms
    #         return 0
    #     else:
    #         return 1 - modified_sigmoid(min_distance, b=1/max(min_distance_threshold, half_range))
    
    def filter_outliers(self):
        for award in self.timestamp_list:
            timestamps = sorted(self.timestamp_list[award])[:len(self.timestamp_list[award]) // 2]
            timestamps = np.array(timestamps)
            if timestamps.size > 0:
                q1, q3 = np.percentile(timestamps, [25, 75])
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                self.timestamp_list[award] = sorted(timestamps[(timestamps >= lower_bound) & (timestamps <= upper_bound)].tolist())
    
    def calculate_top_avg(self, timestamps: list):
        tmp = sorted(timestamps)[max(0, len(timestamps) // 25) : max(2, len(timestamps) // 10)]
        return sum(tmp) / len(tmp)
    
    def loose_categorize_timestamp(self, new_timestamp: float, possible_awards=None, ts_threshold=15000) -> (str, float):
        """ quick function using top 4-10% avg of list to calculate confidence for possible_awards_list """
        unsure_ratio = 1.0
        if not possible_awards:
            possible_awards = self.timestamp_list.keys()
            unsure_ratio = self.unsure_ratio
        
        possible_timestamps = [t for t in self.timestamp_to_award.keys() if t - ts_threshold < new_timestamp and self.timestamp_to_award[t] in possible_awards]
        
        max_timestamp = max(possible_timestamps) if possible_timestamps else -1    
        if max_timestamp == -1:
            return None, 0
        
        confidence = 1 - abs(new_timestamp - max_timestamp) / 240000
        return self.timestamp_to_award[max_timestamp], confidence * unsure_ratio
    
    # def clean_timestamps(self, epsilon=120000, min_samples=3):
    #     """
    #     Cleans the timestamps for each award by applying DBSCAN clustering
    #     and keeping only the largest cluster.

    #     :param epsilon: The maximum distance between two samples for one to be considered
    #                     as in the neighborhood of the other (default: 60000 milliseconds).
    #     :param min_samples: The number of samples in a neighborhood for a point to be considered
    #                         as a core point (default: 3).
    #     """
    #     for award, timestamps in self.timestamp_list.items():
    #         if len(timestamps) < min_samples:
    #             continue
            
    #         X = np.array(timestamps).reshape(-1, 1)

    #         # Apply DBSCAN clustering
    #         db = DBSCAN(eps=epsilon, min_samples=min_samples).fit(X)
    #         labels = db.labels_
            
    #         n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
            
    #         largest_cluster_size = 0
    #         largest_cluster_index = -1
    #         earliest_cluster_index = -1
    #         earliest_timestamp = float('inf')

    #         cluster_sizes = {}
    #         for cluster_idx in range(n_clusters_):
    #             cluster_member_indices = np.where(labels == cluster_idx)[0]
    #             cluster_size = len(cluster_member_indices)

    #             cluster_sizes[cluster_idx] = cluster_size
    #             if cluster_size > largest_cluster_size:
    #                 largest_cluster_size = cluster_size
    #                 largest_cluster_index = cluster_idx

    #             cluster_start_time = timestamps[cluster_member_indices[0]]
    #             if cluster_start_time < earliest_timestamp:
    #                 earliest_timestamp = cluster_start_time
    #                 earliest_cluster_index = cluster_idx

    #         if cluster_sizes.get(earliest_cluster_index, 0) >= largest_cluster_size / 2:
    #             earliest_cluster_members = np.array(timestamps)[labels == earliest_cluster_index]
    #             self.timestamp_list[award] = sorted(earliest_cluster_members.tolist())
    #             continue

    #         # Filter timestamps to keep only those in the largest cluster
    #         self.timestamp_list[award] = sorted(X[labels == largest_cluster_index].flatten().tolist())

    def strict_categorize_timestamp(self, new_timestamp, possible_awards=None) -> (str, float):
        min_distance = float('inf')
        best_award = None
        confidence = 0
        unsure_ratio = 1.0

        if not possible_awards:
            possible_awards = self.timestamp_list.keys()
        else:
            min_possible = min(self.timestamp_list[award][0] for award in possible_awards)
            max_possible = max(self.timestamp_list[award][-1] for award in possible_awards)
            # if the new timestamp is outside the range of possible awards, 
            # then we are unsure (low confidence) and use the whole list instead
            if new_timestamp < min_possible or new_timestamp > max_possible:
                unsure_ratio = self.unsure_ratio
                possible_awards = self.timestamp_list.keys()
        
        min_timestamp = min(self.timestamp_list[award][0] for award in self.timestamp_list)
        max_timestamp = max(self.timestamp_list[award][-1] for award in self.timestamp_list)
        if new_timestamp < min_timestamp or new_timestamp > max_timestamp:
            return None, 0
        
        for award in possible_awards:
            timestamps = self.timestamp_list[award]
            if new_timestamp < timestamps[0]:
                continue
            avg_distance = sum(abs(new_timestamp - ts) for ts in timestamps) / len(timestamps)
            cluster_range = max(timestamps[-1] - timestamps[0], 180000)
            if avg_distance < min_distance:
                min_distance = avg_distance
                best_award = award
                confidence = 1 - min_distance / cluster_range
        
        if confidence < 0:
            # print(f"award: {best_award}, confidence: {confidence}, min_distance: {min_distance}, cluster_range: {cluster_range}")
            return None, confidence
        
        return best_award, confidence * unsure_ratio
    
    def categorize_timestamp(self, new_timestamp, possible_awards=None) -> (str, float):
        award, confidence = self.strict_categorize_timestamp(new_timestamp, possible_awards)
        if not award:
            return self.loose_categorize_timestamp(new_timestamp, possible_awards)    
        else:
            return award, confidence
    
    def loose_categorize_timestamp_after(self, new_timestamp: float, possible_awards=None, ts_threshold=30000, speaking_time_before_awarding=120000) -> (str, float):
        """ quick function using top 4-10% avg of list to calculate confidence for possible_awards_list 
            
            Given the timestamp ts of the tweet, we want to find if an award is awarded between [ts - ts_threshold (audience response time), ts + speaking_time_before_awarding]
            Finding the smallest timestamp t such that t > ts - ts_threshold; if t + speaking_time_before_awarding < ts, then we are unsure (low confidence)
        """
        confidence_ratio = 1.0
        if not possible_awards:
            possible_awards = self.timestamp_list.keys()
            confidence_ratio = self.fuzzy_ratio
        elif len(possible_awards) == len(self.timestamp_list.keys()):
            confidence_ratio = self.fuzzy_ratio
        
        possible_timestamps = [t for t in self.timestamp_to_award.keys() if new_timestamp < t + ts_threshold and self.timestamp_to_award[t] in possible_awards]
        
        min_timestamp = min(possible_timestamps) if possible_timestamps else -1    
        if min_timestamp == -1:
            return None, 0
        
        confidence = 1.0 - max((abs(new_timestamp - min_timestamp) - speaking_time_before_awarding / 2) / speaking_time_before_awarding, 0)
        
        # TODO: uncomment this (debugging)
        # if confidence < 0:
        #     return None, confidence
        return self.timestamp_to_award[min_timestamp], confidence * confidence_ratio
    
    def categorize_timestamp_after(self, new_timestamp, possible_awards=None) -> (str, float):
        award, confidence = self.loose_categorize_timestamp_after(new_timestamp, possible_awards)
        if not award:
            return award, confidence 
        else:
            new_award, new_confidence = self.loose_categorize_timestamp(new_timestamp, [award])
            if new_award == award:
                return award, confidence + new_confidence
            else:
                return award, confidence