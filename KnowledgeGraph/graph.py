import weakref
import networkx as nx
import matplotlib.pyplot as plt
import spacy
import numpy as np

from spacy.lang.en.examples import sentences
from sklearn.decomposition import PCA
from word2number import w2n

from KnowledgeGraph.nodes import Node
from KnowledgeGraph.edges import Edge
from Data.common_words import common_words
from Utilitites.load_json import load_json


class KnowledgeGraph:
    """Principles underlying design
    - do not store information in more than one place unless this is accomplished through weak references (thus deletion
    of one is deletion everywhere).
    - Everything is object based
    """

    def __init__(self):
        self.nodes = []
        self.edges = []

        self.documents_used = []

        self.available_levels = ["A", "B", "C", "D", "E"]
        self.levels_tally = [0, 0, 0, 0, 0]
        self.spacy_model = spacy.load("en_core_web_md")

        self.inferred_entity_count = 0
        self.node_content = []

    def add_document_to_graph(self, data, document):
        """Adds a json-encoded document to the graph."""

        if document in self.documents_used:
            print("Error, document name already used...")
            return

        self.documents_used.append(document)
        self.create_nodes(data, document, level=0)
        self.create_document_edges(document)

    def remove_invalid_edges_and_nodes(self):
        """Checks all edge/nodes to see if their weak references to their nodes/edges are to Nonetypes - i.e.  the node
        no longer exists (and so the edge should be deleted) """

        to_remove = []
        for i, edge in enumerate(self.edges):
            if not edge.check_connected():
                to_remove.append(i)
                print("Found invalid edge.")
        for i in reversed(to_remove):
            del self.edges[i]

        # Check all weak references in Node objects to edges
        for node in self.nodes:
            node.remove_incomplete_edges()

    def create_node(self, level, document, content):
        new_node = Node(level, self.levels_tally[level], document, content)
        self.nodes.append(new_node)
        self.node_content.append(content)
        return new_node

    def create_nodes(self, data, document, level):
        """Recursive method that creates nodes out of all the entries in a json document."""
        if type(data) is list:
            for d in data:
                self.levels_tally[level] += 1
                self.create_node(level, document, d)
        else:
            for key in data.keys():
                if key != "None":
                    self.levels_tally[level] += 1
                    self.create_node(level, document, key)
                self.create_nodes(data[key], document, level+1)

    def build_flow_edges(self, document):
        """Adds all edges that make up the structure of the document read from top to bottom."""
        document_nodes = [node for node in self.nodes if node.document == document]

        for i, node in enumerate(document_nodes[1:]):
            new_edge = Edge(document_nodes[i], node, edge_type="Flow")
            self.edges.append(new_edge)
            document_nodes[i].add_edge(new_edge)
            node.add_edge(new_edge)

    def build_structural_edges(self, document):
        """Builds edges which represent ownership i.e. document owns headings, headings own paragraphs."""
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

    def harvest_entity_links(self):
        """
        Types:
        - Key words - A single node for a word that is shared. Will eventually want to exclude some words.

        Be sure to check the created edges dont already exist - might be easier to wipe them all out first.
        :return:
        """
        starting_nodes = len(self.nodes)

        for i in range(starting_nodes):
            node_1 = self.nodes[i]
            print(i)
            for j in range(starting_nodes):
                node_2 = self.nodes[j]
                if i == j:
                    pass
                else:
                    for word_1 in node_1.individual_words:
                        for word_2 in node_2.individual_words:
                            if word_1 == word_2:
                                new_node = self.create_new_inferred_entity(word_1)
                                if new_node is not None:
                                    new_edge_1 = Edge(parent=new_node, child=node_1, edge_type=f"Keyword-{word_1}")
                                    new_edge_2 = Edge(parent=new_node, child=node_2, edge_type=f"Keyword-{word_1}")
                                    self.edges.append(new_edge_1)
                                    self.edges.append(new_edge_2)

                                    new_node.add_edge(new_edge_1)
                                    new_node.add_edge(new_edge_2)

                                    node_1.add_edge(new_edge_1)
                                    node_2.add_edge(new_edge_2)

    def create_new_inferred_entity(self, content):
        """Checks if a new word exists as an entity in the graph already and that it isnt a common word. If not, it
        creates a new node named this."""
        # all_node_content = [node.content for node in self.nodes]  # TODO: Improve speed: maybe keep another record of content (and delete from here when deleting nodes)
        all_node_content = self.node_content
        if content in all_node_content:
            return self.nodes[all_node_content.index(content)]
        else:
            if content not in common_words:
                new_entity = self.create_node(level=0, document="Inferred", content=content)
                return new_entity

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
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=6)
        plt.show()

    def delete_node(self, node_id):
        """
        Attempts to make this faster than checking for validity of every existing edge
        Find node via id.
        del node
        check_edges()?
        :param node_id:
        :return:
        """
        node_ids = [node.identifier for node in self.nodes]
        node_index = node_ids.index(node_id)

        # Delete node content shorthand
        del self.node_content[node_index]

        # Find location of edges
        edges_to_delete = self.nodes[node_index].edges
        edges_to_delete_ids = [edge().identifier for edge in edges_to_delete]
        edge_ids = [edge.identifier for edge in self.edges]
        edge_indexes = [edge_ids.index(edge_id) for edge_id in edges_to_delete_ids]

        # Delete edges
        for edge_i in reversed(edge_indexes):
            self.edges[edge_i].delete_edge()
            del self.edges[edge_i]

        # Find location of effected nodes.

        # Delete node
        del self.nodes[node_index]

        # TODO: Check that no null edges remain...

        x = True


if __name__ == "__main__":
    file = load_json("Immanuel Kant - Wikipedia.json")
    file2 = load_json("Thus Spoke Zarathustra - Wikipedia.json")

    graph = KnowledgeGraph()
    graph.add_document_to_graph(file, "Kant")
    graph.add_document_to_graph(file2, "Zarathustra")
    graph.compute_node_embeddings()
    graph.remove_invalid_edges_and_nodes()
    graph.display_graph()
