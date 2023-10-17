import weakref
import networkx as nx
import matplotlib.pyplot as plt
import spacy
import numpy as np

from spacy.lang.en.examples import sentences
from sklearn.decomposition import PCA
from word2number import w2n

from Utilitites.load_json import load_json


"""Using object oriented paradigm, should aim to create a representation of a graph where, as everything is object based, 
there are no repetitions."""


class Edge:

    def __init__(self, parent, child, edge_type, edge_weight=1):
        self.edge_identifier = f"{parent.identifier}-{child.identifier}"
        self.edge_type = edge_type
        self.edge_weight = edge_weight

        self.parent_node = weakref.ref(parent)
        self.child_node = weakref.ref(child)

    def delete_edge(self):
        self.parent_node.remove_child(self.child_node)
        self.child_node_node.remove_parent(self.parent_node)
        del self

    def check_connected(self):
        if self.parent_node() is None:
            print(f"Parent dead, deleting {self.edge_identifier}")
            return False
        if self.child_node() is None:
            print(f"Child dead, deleting {self.edge_identifier}")
            return False
        return True


class Node:

    def __init__(self, level, id_n, document, content):
        self.identifier = f"{document}-{level}:{id_n}"
        self.level = level
        self.content = content
        self.document = document

        self.edges = []
        self.embedding = []

        self.individual_words = [word.lower().replace(".", "") for word in content.split(" ")]

    def add_edge(self, edge):
        self.edges.append(weakref.ref(edge))

    def get_child_edges(self):
        return [edge() for edge in self.edges if edge().parent_node is self]

    def get_parent_edges(self):
        return [edge() for edge in self.edges if edge().child_node is self]

    def compute_individual_word_indices(self):
        ...


class KnowledgeGraph:
    """Principles underlying design - do not store information in more than one place unless this is accomplished
    through pointer links"""
    # TODO: Implement in such a way that a graph can contain its own subgraphs (but that the nodes are still accessible
    #  in the same way (while graph attributes are also accessible). Alternatively, just do this KG separation through
    #  decomposition - or subgraph identification?

    def __init__(self):
        self.nodes = []
        self.edges = []

        self.documents_used = []

        self.available_levels = ["A", "B", "C", "D", "E"]
        self.levels_tally = [0, 0, 0, 0, 0]
        self.spacy_model = spacy.load("en_core_web_md")

    def add_document_to_graph(self, data, document):
        if document in self.documents_used:
            print("Error, document name already used...")
            return

        self.documents_used.append(document)
        self.create_nodes(data, document, level=0)
        self.create_document_edges(document)
        # TODO: Instansiate edges within nodes and only have variables referring to them within the nodes - so when the
        #  nodes are deleted, the edges are too. This better reflects the dependency - nodes without edges but no edges
        #  without nodes

    def check_edges(self):
        """Checks all edge objects to see if their weak references to """
        # Check all edge objects
        to_remove = []
        for i, edge in enumerate(self.edges):
            if not edge.check_connected():
                to_remove.append(i)

        for i in reversed(to_remove):
            del self.edges[i]

        # Check all weak references in Node objects

        for node in self.nodes:
            # TODO: Move code to node class.
            to_remove = []

            for i, edge in enumerate(node.edges):
                if edge() is None:
                    print("Edge no longer exists, deleting")
                    to_remove.append(i)
            for i in reversed(to_remove):
                del node.edges[i]

    def create_nodes(self, data, document, level):
        if type(data) is list:
            for d in data:
                self.levels_tally[level] += 1
                new_node = Node(level, self.levels_tally[level], document, d)
                self.nodes.append(new_node)
        else:
            for key in data.keys():
                if key != "None":
                    self.levels_tally[level] += 1
                    new_node = Node(level, self.levels_tally[level], document, key)
                    self.nodes.append(new_node)
                self.create_nodes(data[key], document, level+1)

    def build_flow_edges(self, document):
        """Adds all edges that make up the structure of the document read from top to bottom"""
        document_nodes = [node for node in self.nodes if node.document == document]

        for i, node in enumerate(document_nodes[1:]):
            new_edge = Edge(document_nodes[i], node, edge_type="Flow")
            self.edges.append(new_edge)
            document_nodes[i].add_edge(new_edge)
            node.add_edge(new_edge)

    def build_structural_edges(self, document):
        document_nodes = [node for node in self.nodes if node.document == document]

        for i, node in enumerate(reversed(document_nodes)):
            node_level = node.level
            possible_owners = document_nodes[:-(i+1)]

            for p in reversed(possible_owners):
                p_level = p.level

                if p_level < node_level:
                    # It's the owner
                    new_edge = Edge(p, node, "Structural")
                    self.edges.append(new_edge)
                    p.add_edge(new_edge)
                    node.add_edge(new_edge)

                    break

    def create_document_edges(self, document):
        self.build_flow_edges(document)
        self.build_structural_edges(document)

    def create_interdocument_edges(self):
        """
        Types:
        - Key words - A single node for a word that is shared. Will eventually want to exclude some words.
        - Key phrases - Need to think of a way to do this.

        Be sure to check the created edges dont already exist - might be easier to wipe them all out first.
        :return:
        """
        for i, node_1 in enumerate(self.nodes):
            for j, node_2 in enumerate(self.nodes):
                if i == j:
                    pass
                else:
                    for word_1 in node_1.individual_words:
                        for word_2 in node_2.individual_words:
                            if word_1 == word_2:
                                new_edge = Edge(node_1, node_2, f"Keyword-{word_1}")  # TODO: Make clear this edge is non-directional. Or create keyword entity (first check whether this already exists).
                                self.edges.append(new_edge)
                                node_1.add_edge(new_edge)
                                node_2.add_edge(new_edge)

    def compute_node_embeddings(self):
        node_embeddings = []
        # Note that this method fails if a word is not in the model e.g. here: perspectivism.
        for node in self.nodes:
            embedding = self.spacy_model(node.content)
            node_embeddings.append(embedding.vector)

        # Dimensionality reduction
        node_embeddings = np.array(node_embeddings)
        pca = PCA(n_components=2)
        reduced_embeddings = pca.fit_transform(node_embeddings)

        for i, node in enumerate(self.nodes):
            self.nodes[i].embedding = reduced_embeddings[i]

    def display_graph(self):
        colours = ['blue', 'red', 'green', 'orange', "yellow"]
        document_identifiers = [node.document for node in self.nodes]
        uniques = list(set(document_identifiers))
        node_identifiers = [node.identifier for node in self.nodes]
        node_content = [node.content for node in self.nodes]
        node_embeddings = [node.embedding for node in self.nodes]

        G = nx.DiGraph()
        G.add_edges_from([[edge.parent_node().identifier, edge.child_node().identifier] for edge in self.edges])

        # pos = nx.spring_layout(G)
        pos = {label:node_embeddings[i] for i, label in enumerate(node_identifiers)}
        labels = {node_identifier: node_identifier for node_identifier, node_content in zip(node_identifiers, node_content)}
        colour_map = [colours[uniques.index(value)] for value in document_identifiers]

        nx.draw(G, pos, node_color=colour_map)
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=6, alpha=0.1)
        plt.show()

    def delete_node(self, node_id):
        """
        Find node via id.
        del node
        check_edges()?
        :param node_id:
        :return:
        """


if __name__ == "__main__":
    file = load_json("Immanuel Kant - Wikipedia.json")
    file2 = load_json("Thus Spoke Zarathustra - Wikipedia.json")

    graph = KnowledgeGraph()
    graph.add_document_to_graph(file, "Kant")
    graph.add_document_to_graph(file2, "Zarathustra")
    graph.compute_node_embeddings()
    graph.check_edges()
    graph.display_graph()
