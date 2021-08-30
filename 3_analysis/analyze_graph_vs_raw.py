import sklearn
from sklearn.cluster import KMeans
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os
import json
import scipy

from clustering import normalize_and_cluster, decision_tree_cluster
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import adjusted_rand_score

groups = {
    "travelers": {
        "mean_distance_random_walk": "high",
        "cycle_length_mu": "high",
        "core_periphery_random_walk": "high",
        "ratio_nodes_random_walk": "low",
    },
    "city_people": {
        "mean_distance_random_walk": "low",
        "cycle_length_mu": "high",
        "cycle_length_sigma": "low",
        "core_periphery_random_walk": "low",
        "ratio_nodes_random_walk": "high",
        "simple_powerlaw_transitions": "low",
    },
    "unpredictable": {
        "cycle_length_mu": "high",
        "core_periphery_random_walk": "high",
        "simple_powerlaw_transitions": "high",
        "ratio_nodes_random_walk": "low",
    },
    "inactive": {
        "mean_distance_random_walk": "low",
        "cycle_length_mu": "low",
        "cycle_length_sigma": "high",
        "core_periphery_random_walk": "low",
        "ratio_nodes_random_walk": "high",
    },
}
interpret_dict = {
    "mean_distance_random_walk": {"high": "high distances", "low": "low distances"},
    "cycle_length_mu": {"high": "high variance of cycle lengths", "low": "low variance of cycle length"},
    "cycle_length_sigma": {"high": "more low cycle lengths", "low": "more high cycle lengths"},
    "core_periphery_random_walk": {
        "high": "activity distributed over many nodes",
        "low": "activity centered on few nodes",
    },
    "ratio_nodes_random_walk": {
        "high": "many locations are often encountered",
        "low": "many locations are rarely encountered",
    },
    "simple_powerlaw_transitions": {"high": "few edges are used often", "low": "more edges are used often"},
}


def cluster_characteristics(in_features, cluster_labels=None):
    features = in_features.copy()
    if cluster_labels is not None:
        features["cluster"] = cluster_labels
    labels = features["cluster"]
    characteristics = {}
    for cluster in np.unique(labels):
        print(f"------- Cluster {cluster} of {np.sum(labels==cluster)} samples -------------")
        characteristics[cluster] = {}
        for column in features.columns:
            # skip cluster column
            if column == "cluster":
                continue
            if "waiting_time" in column and column != "waiting_time_mean":
                continue
            this_cluster = features.loc[features["cluster"] == cluster, column]
            other_clusters = features.loc[features["cluster"] != cluster, column]
            #         print(this_cluster)
            #         print(other_clusters)
            # TODO: other test?
            res, p_value = scipy.stats.mannwhitneyu(this_cluster, other_clusters)
            direction = "low" if np.mean(this_cluster) < np.mean(other_clusters) else "high"
            if p_value < 0.05:
                #                 print(f"{direction} {column} (p-value:{round(p_value, 3)})")
                print(interpret_dict[column][direction])
                characteristics[cluster][column] = direction
            else:
                # TODO: middle features? compare to each cluster?
                pass
    return characteristics


def sort_clusters_into_groups(characteristics):
    print("--------- Sorting cluster into predefined groups ------------")
    for cluster, cluster_characteristics in characteristics.items():
        # check whether we can put it in any group:
        for group_name, group in groups.items():
            is_group = True
            for key, val in cluster_characteristics.items():
                # maybe group is not characterized by this
                if key not in group:
                    continue
                # not part of group if one characteristic is different
                if group[key] != val:
                    is_group = False
            if is_group:
                print(f"Cluster {cluster} is part of group", group_name)
                break


def get_correlated_features(graph_features, raw_features):
    for raw_feat in raw_features.columns:
        # exclude waiting times, not useful
        if "waiting_time" in raw_feat:
            continue
        for graph_feat in graph_features.columns:
            r, p = scipy.stats.pearsonr(raw_features[raw_feat], graph_features[graph_feat])
            if abs(r) > 0.2:
                print("Correlation {:<25} and {:<25}: {:<5}".format(raw_feat, graph_feat, r))


def get_important_features(features, labels, n_important=4, method="forest"):
    assert method in ["tree", "forest"]
    if method == "forest":
        forest = RandomForestClassifier()
        forest.fit(np.array(features), labels)
        feature_importances = forest.feature_importances_
    elif method == "tree":
        feature_importances = decision_tree_cluster(features, labels)

    important_feature_inds = np.flip(np.argsort(feature_importances)[-n_important:])
    return np.array(features.columns)[important_feature_inds], feature_importances[important_feature_inds]


def returner_explorers(path_to_returner, graph_features):
    k_returners = pd.read_csv(path_to_returner, index_col="user_id")
    # fill Nans with highest k
    k_returners.loc[k_returners[pd.isna(k_returners["k_returner"])].index, "k_returner"] = 50
    median_k = np.median(k_returners["k_returner"].values)
    k_returners["explorer"] = k_returners["k_returner"].apply(lambda x: x > median_k)
    # align index
    k_returners = k_returners.loc[graph_features.index]
    graph_features.loc[k_returners.index, "cluster"] = k_returners["explorer"].astype(int)

    print("Features that are significantly different between returners and explorers:")
    cluster_characteristics(graph_features)

    print("Feature importances to predict returners and explorers according to decision tree:")
    feature_importances = decision_tree_cluster(
        graph_features.drop(columns=["cluster"]), graph_features["cluster"].values
    )
    important_feature_inds = np.flip(np.argsort(feature_importances)[-4:])
    print(np.array(graph_features.columns)[important_feature_inds], feature_importances[important_feature_inds])


if __name__ == "__main__":

    path = "gc_case_study"
    study = "gc1"
    node_importance = 0
    n_clusters = 4
    algorithm = "kmeans"

    # load features
    graph_features = pd.read_csv(
        os.path.join(path, f"{study}_graph_features_{node_importance}.csv"), index_col="user_id"
    )
    raw_features = pd.read_csv(os.path.join(path, f"{study}_raw_features_{node_importance}.csv"), index_col="user_id")
    raw_features = raw_features.loc[graph_features.index]
    assert all(raw_features.index == graph_features.index)
    print(graph_features.shape, raw_features.shape)

    get_correlated_features(graph_features, raw_features)

    labels = normalize_and_cluster(graph_features, impute_outliers=False, n_clusters=n_clusters, algorithm=algorithm)

    # try to characterize clusters
    characteristics = cluster_characteristics(graph_features, labels)
    sort_clusters_into_groups(characteristics)

    # cluster both with their features, compute similarity:
    labels_graph = normalize_and_cluster(np.array(graph_features), algorithm=algorithm)
    labels_raw = normalize_and_cluster(np.array(raw_features), algorithm=algorithm)
    print("rand score", adjusted_rand_score(labels_raw, labels_graph))

    # get best raw features to explain graph features
    selected_features, importances = get_important_features(raw_features, labels)

    raw_filtered = raw_features[selected_features]
    print("Selected columns", raw_filtered.columns)
    raw_labels_filtered = normalize_and_cluster(raw_filtered, algorithm=algorithm)
    print("rand score", adjusted_rand_score(raw_labels_filtered, labels_graph))

    # get five most important features:
    # important_feature_inds = np.argsort(feature_importances)[-5:]
    # print(np.array(raw_features.columns)[important_feature_inds], feature_importances[important_feature_inds])

    # returner_explorers("test_get_all/gc1_returner_explorer.csv", graph_features)
