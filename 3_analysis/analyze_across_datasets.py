import os
import numpy as np
import pandas as pd

from clustering import ClusterWrapper
from compare_clustering import compute_all_scores


def load_all(path, type="graph", node_importance=50):
    """
    type: one of graph, raw
    """
    all_together = []
    study_labels = []
    for study in STUDIES:  # , "yumuv_graph_rep"]: # _{node_importance}
        graph_features = pd.read_csv(
            os.path.join(path, f"{study}_graph_features_{node_importance}.csv"), index_col="user_id"
        )
        # TODO: need to filter raw features?
        if type == "graph":
            all_together.append(graph_features)
        elif type == "raw":
            raw_features = pd.read_csv(
                os.path.join(path, f"{study}_raw_features_{node_importance}.csv"), index_col="user_id"
            )
            raw_features = raw_features[raw_features.index.isin(graph_features.index)]
            all_together.append(raw_features)

        study_labels.extend([study for _ in range(len(graph_features))])
    # concatenate
    features_all_datasets = pd.concat(all_together)
    features_all_datasets["study"] = study_labels
    print("Samples per study:", np.unique(study_labels, return_counts=True))
    return features_all_datasets


def mean_features_by_study(features, out_path=None):
    # leave away last column because it's the study label
    agg = {feat: ["mean", "std"] for feat in features.columns[:-1]}
    # group and aggregate
    mean_features = features.groupby("study").agg(agg).round(2)
    if out_path:
        mean_features.to_csv(out_path)
    else:
        print(mean_features)


if __name__ == "__main__":
    STUDIES = [
        "gc1",
        "gc2",
        "tist_toph100",
        "geolife",
        "yumuv_graph_rep",
        "yumuv_before_cg",
        "yumuv_after_cg",
        "yumuv_before_tg",
        "yumuv_after_tg",
    ]
    # parameters
    nodes = 0
    path = f"out_features/final_2_n{nodes}_cleaned"
    n_clusters = len(STUDIES)
    feature_type = "raw"

    # tist does not have trip data
    if feature_type == "raw" and "tist_toph100" in STUDIES:
        STUDIES.remove("tist_toph100")

    features_all_datasets = load_all(path, type=feature_type, node_importance=nodes)
    cluster_wrapper = ClusterWrapper()
    cluster_labels = cluster_wrapper(features_all_datasets.drop(columns=["study"]), n_clusters=n_clusters)
    print(np.unique(cluster_labels, return_counts=True))
    # compare relation between cluster and study labels
    compute_all_scores(cluster_labels, np.array(features_all_datasets["study"]))
    mean_features_by_study(features_all_datasets, out_path=f"out_features/dataset_comparison_{nodes}.csv")
