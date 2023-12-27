import networkx as nx
import matplotlib.pyplot as plt
import spacy
import numpy as np
from spacy.lang.en.examples import sentences
from sklearn.decomposition import PCA

from Utilitites.json_operations import load_json


class KnowledgeGraph2:

    def __init__(self):
        self.node_identifiers = []
        self.node_document_sources = []
        self.node_contents = []
        self.node_embeddings = []

        self.edge_identifiers = []
        self.edges = []
        self.available_levels = ["A", "B", "C", "D", "E"]
        self.spacy_model = spacy.load("en_core_web_md")

        self.adjacency_matrix = None
        self.incidence_matrix = None

        # TODO: Consider that future versions may benefit from having classes representing nodes/edges - current method
        #  of keeping a long list of edges and nodes is not scalable - have to sort entire list to get the edges of one
        #  node. Note though that this is somewhat solved by having an adjacency or incidence matrix.

        # Currently has number of connections encoded as number - note that for the incidence matrix this will lead to
        #  connection masking for reciprocal connections
        # TODO: Research and implement different ways of ranking connections between nodes.

    def create_identifier(self, level, document):
        level_identifier = self.available_levels[level]
        current_identifiers_of_that_level = len([i for i in self.node_identifiers if level_identifier in i])
        self.node_identifiers.append(f"{level_identifier}:{current_identifiers_of_that_level}")
        self.node_document_sources.append(document)

    def add_node(self, level, document, node_contents):
        self.create_identifier(level, document)
        self.node_contents.append(node_contents)

    def create_nodes(self, data, document, level=0):
        if type(data) is list:
            for d in data:
                self.add_node(level, document, d)
        else:
            for key in data.keys():
                if key != "None":
                    self.add_node(level, document, key)
                self.create_nodes(data[key], document, level+1)

    def build_flow_edges(self, document):
        """Adds all edges that make up the structure of the document read from top to bottom"""
        document_identifiers = [i for i, d in zip(self.node_identifiers, self.node_document_sources) if d == document]
        for i, identifier in enumerate(document_identifiers[1:]):
            self.edge_identifiers.append(f"{document_identifiers[i]}-{identifier}")
            self.edges.append([document_identifiers[i], identifier])

    def build_structural_edges(self, document):
        document_identifiers = [i for i, d in zip(self.node_identifiers, self.node_document_sources) if d == document]
        for i, identifier in enumerate(reversed(document_identifiers)):
            identifier_level = identifier[:1]
            identifier_level_index = self.available_levels.index(identifier_level)

            possible_owners = document_identifiers[:-(i+1)]
            for p in reversed(possible_owners):
                possible_level = p[:1]
                possible_level_index = self.available_levels.index(possible_level)

                if possible_level_index < identifier_level_index:
                    # It's the owner
                    self.edge_identifiers.append(f"{p}-{identifier}")
                    self.edges.append([p, identifier])
                    break

    def create_edges(self, document):
        self.build_flow_edges(document)
        self.build_structural_edges(document)

    def add_document_to_graph(self, data, document):
        self.create_nodes(data, document)
        self.create_edges(document)

    def compute_node_embeddings(self):
        self.node_embeddings = []
        # Note that this method fails if a word is not in the model e.g. here: perspectivism.
        for node in self.node_contents:
            embedding = self.spacy_model(node)
            self.node_embeddings.append(embedding.vector)

        # Dimensionality reduction
        self.node_embeddings = np.array(self.node_embeddings)
        pca = PCA(n_components=2)
        reduced_embeddings = pca.fit_transform(self.node_embeddings)
        self.node_embeddings = reduced_embeddings

    def compute_adjacency_matrix(self):
        """Produces adjacency/connectivity matrix."""
        num_nodes = len(self.node_identifiers)
        adjacency_matrix = np.zeros((num_nodes, num_nodes))
        for edge in self.edges:
            start_node_index = self.node_identifiers.index(edge[0])
            end_node_index = self.node_identifiers.index(edge[1])
            adjacency_matrix[start_node_index, end_node_index] += 1

        self.adjacency_matrix = adjacency_matrix

    def compute_incidence_matrix(self):
        num_nodes = len(self.node_identifiers)
        num_edges = len(self.edges)

        incidence_matrix = np.zeros((num_nodes, num_edges))
        for e, edge in enumerate(self.edges):
            start_node_index = self.node_identifiers.index(edge[0])
            end_node_index = self.node_identifiers.index(edge[1])

            incidence_matrix[start_node_index, e] += 1
            incidence_matrix[end_node_index, e] -= 1

        self.incidence_matrix = incidence_matrix

    def compute_graph_word_usage(self):
        ...

    def display_graph(self):
        colours = ['blue', 'red', 'green', 'orange']
        uniques = list(set(self.node_document_sources))

        G = nx.DiGraph()

        G.add_edges_from(self.edges)

        # pos = nx.spring_layout(G)
        pos = {label:self.node_embeddings[i] for i, label in enumerate(self.node_identifiers)}
        labels = {node_identifier: node_content for node_identifier, node_content in zip(self.node_identifiers, self.node_identifiers)}
        colour_map = [colours[uniques.index(value)] for value in self.node_document_sources]

        nx.draw(G, pos, node_color=colour_map)
        nx.draw_networkx_labels(G, pos, labels=labels)
        plt.show()

    def decompose_node_contents_to_sentences(self):
        """So that they have the structural properties of the original, and flow between them as we would expect. They should be based a hierarchy down.
        What should be done about the previous hierarchy?
        """
        indices_of_multisentence_nodes = [i for i, text in enumerate(self.node_contents) if len(text.split(". ")) > 1]
        new_node_identifiers = []
        new_node_contents = []
        new_edge_identifiers = []
        new_node_document_sources = []
        new_edges = []

        for i, identifier in enumerate(self.node_identifiers):
            if i not in indices_of_multisentence_nodes:
                new_node_identifiers.append(self.node_identifiers[i])
                new_node_contents.append(self.node_contents[i])
                new_edge_identifiers.append(self.edge_identifiers[i])
                new_node_document_sources.append(self.node_document_sources[i])
                for edge in self.edges:
                    if edge[1] == identifier:
                        new_edges.append(edge)
                        # TODO: Fix this - needs to check that both edges will continue to exist....
            else:
                split_node = self.node_contents[i].split(". ")
                node_constituents = [c + ". " if j + 1 != len(split_node) else c for j, c in enumerate(split_node)]

                original_identifier = self.node_identifiers[i]
                new_node_type = char(ord(original_identifier[0]) + 1)

                new_identifiers = ...
                x = True
        # TODO: Recompute adjacency and indices matrices? Recompute node embeddings. Recomputation of all previously
        #  computed aspects should be a method which can detect what needs recomputing.

    def decompose_node_contents_symbolically(self):
        ...


if __name__ == "__main__":
    file = load_json("Immanuel Kant - Wikipedia.json")
    file2 = load_json("Thus Spoke Zarathustra - Wikipedia.json")
    file3 = load_json("Friedrich Nietzsche - Wikipedia.json")

    graph = KnowledgeGraph2()
    # TODO: Plan for a new, more elegant class structure.
    # TODO: Plan for a new data storage regime that includes use of databases

    # graph.add_document_to_graph(file, "Kant")
    graph.add_document_to_graph(file2, "Zarathustra")
    # graph.add_document_to_graph(file3, "Nietzsche")
    graph.compute_node_embeddings()
    graph.compute_adjacency_matrix()
    graph.compute_incidence_matrix()
    # graph.decompose_node_contents_to_sentences()

    graph.display_graph()

    x = True
