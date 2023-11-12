import copy
import cProfile
import pstats

from Utilitites.load_json import load_json
from KnowledgeGraph.graph import KnowledgeGraph


class GraphManager:

    """Manager class to handle multiple graphs and graph-graph operations. To add in the ability to run things
    concurrently e.g. display graphs while also having entity linkage happening in the background."""

    def __init__(self, profile):
        self.profile = profile
        if self.profile:
            self.profiler = cProfile.Profile()
            self.profiler.enable()

        self.graphs = {}

    def create_graph(self, graph_name: str):
        # TODO: Check doesnt overwrite exisinng
        self.graphs[graph_name] = KnowledgeGraph()

    def add_json_to_graph(self, graph_name: str, json_file_name: str):
        # TODO: Check doesnt overwrite exisinng
        file = load_json(json_file_name)
        self.graphs[graph_name].add_document_to_graph(file, json_file_name)

    def run_routine_graph_computations(self, graph_name):
        """RUn all the routine operations of the graph. Intended for when all the desired elements have been added to
        the graph"""
        # self.graphs[graph_name].harvest_entity_links()
        self.graphs[graph_name].compute_node_embeddings()

    def add_website_to_graph(self, graph_name: str, url: str):
        ...  # Utilise above function after creation.

    def merge_graphs(self, graph_1_name: str, graph_2_name: str):
        ...

    def split_graphs(self):
        ...

    def create_subgraph(self):
        ...

    def display_graph(self, graph_name: str):
        self.graphs[graph_name].remove_invalid_edges_and_nodes()
        self.graphs[graph_name].display_graph_gephi()

    def decompose_graph(self, graph_name: str):
        """
        Check if its possible to decompose the graph.
        Need to determine how many decompositions can be done - to allow a sliding scale to be possible.

        :param graph_name:
        :return:
        """
        decomposable = False
        for node in self.graphs[graph_name].nodes:
            if node.splits_into > 1:
                decomposable = True
                break
        if decomposable:
            if graph_name[-1].isdigit():
                new_graph_name = f"{graph_name[:-1]}{(int(graph_name[-1]) + 1)}"
            else:
                new_graph_name = graph_name + "-1"
            self.graphs[new_graph_name] = copy.copy(self.graphs[graph_name])
            self.graphs[new_graph_name].decompose_nodes()
            self.graphs[new_graph_name].remove_invalid_edges_and_nodes()
        else:
            print("Graph is not decomposable")

    def close(self):
        if self.profile:
            ps = pstats.Stats(self.profiler)
            ps.sort_stats("tottime")
            ps.print_stats()


if __name__ == "__main__":
    # graph.delete_node("Nietzsche-0:1")
    # graph.remove_invalid_edges_and_nodes()
    # graph.compute_node_embeddings()
    ...