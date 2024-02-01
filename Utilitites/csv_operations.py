import csv
import pandas as pd


def load_csv(file_name):
    ...


def load_graph_elements_from_csv(file_name):
    nodes_pandas = pd.read_csv(f"Data/Saved-Graphs/CSV/{file_name}-nodes.csv")
    edges_pandas = pd.read_csv(f"Data/Saved-Graphs/CSV/{file_name}-edges.csv")
    return nodes_pandas, edges_pandas


def save_graph_to_csv(graph, file_name):
    # Return two CSV tables as the graph representations.
    edges = {
        "edge_identifier": [edge.identifier for edge in graph.edges],
        "source": [edge.parent_node().identifier for edge in graph.edges],
        "target": [edge.child_node().identifier for edge in graph.edges],
        "edge_weight": [edge.edge_weight for edge in graph.edges],
        "edge_type": [edge.edge_type for edge in graph.edges],
             }
    edges_pandas = pd.DataFrame(edges)
    edges_pandas.to_csv(f"Data/Saved-Graphs/CSV/{file_name}-edges.csv", index=False)

    nodes = {
        "node_identifier": [node.identifier for node in graph.nodes],
        "content": [node.content for node in graph.nodes],
        "id_n": [node.id_n for node in graph.nodes],
        "level": [node.level for node in graph.nodes],
        "document": [node.document_name for node in graph.nodes],
    }

    if graph.nodes[0].embedding is not None:
        nodes["pca_encoding_x"] = [node.embedding[0] for node in graph.nodes]
        nodes["pca_encoding_y"] = [node.embedding[1] for node in graph.nodes]

    nodes_pandas = pd.DataFrame(nodes)
    nodes_pandas.to_csv(f"Data/Saved-Graphs/CSV/{file_name}-nodes.csv", index=False)


def save_csv(nodes, edges, file_name):
    ...
