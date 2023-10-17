"""
Implement the most basic knowledge graph that can combine the wikipedia and pdf extracted elements sensibly.
"""
import networkx as nx
import matplotlib.pyplot as plt
from graphviz import Digraph

from Utilitites.load_json import load_json


class KnowledgeGraph1:

    def __init__(self):
        self.node_identifiers = []
        self.node_contents = []
        self.edges = []

        self.title_identifiers = 0
        self.h1_identifiers = 0
        self.h2_identifiers = 0
        self.p_identifiers = 0

    def create_identifier(self, level):
        if level == "title":
            self.node_identifiers.append("title:" + str(self.title_identifiers))
            self.title_identifiers += 1
        elif level == "h1":
            self.node_identifiers.append("h1:" + str(self.h1_identifiers))
            self.h1_identifiers += 1
        elif level == "h2":
            self.node_identifiers.append("h2:" + str(self.h2_identifiers))
            self.h2_identifiers += 1
        elif level == "p":
            self.node_identifiers.append("p:" + str(self.p_identifiers))
            self.p_identifiers += 1
        else:
            print("Error: Wrong level specified")

    def create_nodes(self, data):
        titles = data.keys()
        new_node_identifiers = []

        for title in titles:
            if title != "None":
                self.create_identifier("title")
                self.node_contents.append(title)

            for h1 in data[title].keys():
                if h1 != "None":
                    self.create_identifier("h1")
                    self.node_contents.append(h1)

                for h2 in data[title][h1].keys():
                    if h2 != "None":
                        self.create_identifier("h2")
                        self.node_contents.append(h2)

                    for p in data[title][h1][h2]:
                        if p != "None":
                            self.create_identifier("p")
                            self.node_contents.append(p)

    def create_document_structure_edges(self, data, added_node_identifiers):
        # Create edges from the start to end of document - implicit from the node list.
        for i, node in enumerate(self.node_identifiers[1:]):
            self.edges.append([self.node_identifiers[i], self.node_identifiers[i+1]])

        # Create edges from the structure of the document - enclosed by - signalled by type.
        for i, identifier in enumerate(self.node_identifiers[1:]):
            previous_valid = [identi for identi in self.node_identifiers[:i] if identifier[:2] not in identi]
            if len(previous_valid) > 0:
                self.edges.append([previous_valid[-1], self.node_identifiers[i+1]])

    def compute_document_structure_graph_from_json(self, data):
        # Assign an id to each node
        added_node_identifiers = self.create_nodes(data)

        # Create a list of edges - each has a 2d list with directional node A-> B is [A, B]
        self.create_document_structure_edges(data, added_node_identifiers)

    def recompose_document_from_directional_structure(self):
        # Not using the identifiers, just the contents and edges.
        ...

    def display_graph(self):
        G = nx.DiGraph()

        G.add_edges_from(self.edges)

        pos = nx.spring_layout(G)
        labels = {node_identifier: node_content for node_identifier, node_content in zip(self.node_identifiers, self.node_identifiers)}

        nx.draw_networkx_labels(G, pos, labels=labels)
        nx.draw_networkx_edges(G, pos)

        plt.show()


if __name__ == "__main__":
    file = load_json("Orchestra of Bubbles - Wikipedia.json")
    # file = load_json("Friedrich Nietzsche - Wikipedia.json")
    graph = KnowledgeGraph1()
    graph.compute_document_structure_graph_from_json(file)
    graph.display_graph()
