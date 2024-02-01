import os
import networkx as nx

import matplotlib.pyplot as plt


import spacy
import numpy as np

from sklearn.decomposition import PCA
import gephistreamer

from KnowledgeGraph.nodes import Node
from KnowledgeGraph.edges import Edge
from Data.Entities.common_words import common_words
from Utilitites.json_operations import load_json_entity
from Utilitites.csv_operations import save_graph_to_csv


class KnowledgeGraph:
    """Principles underlying design
    - do not store information in more than one place unless this is accomplished through weak references (thus deletion
    of one is deletion everywhere).
    - Everything is object based
    """

    def __init__(self, graph_name, autosave=True):
        self.graph_name = graph_name

        self.nodes = []
        self.edges = []

        self.documents_used = []

        self.available_levels = ["A", "B", "C", "D", "E"]
        self.levels_tally = [0, 0, 0, 0, 0]
        self.spacy_model = spacy.load("en_core_web_md")

        self.inferred_entity_count = 0
        self.node_content = []

        self.autosave_graph = autosave
        self.maintained_formats = []

    def _run_operation(self):
        """
        A method that runs every time a major operation occurs, to allow maintenance to be carried out e.g. autosave.
        """
        if self.autosave_graph:
            for f in self.maintained_formats:
                ...  # TODO: Autosave

    def add_document_to_graph(self, data: dict, document_name: str):
        """Adds a json-encoded document to the graph."""
        self._run_operation()

        if document_name in self.documents_used:
            print("Error, document name already used...")
            return

        self.documents_used.append(document_name)
        self.create_nodes(data, document_name, level=0)
        self.create_document_edges(document_name)

    def remove_invalid_edges_and_nodes(self):
        """Checks all edge/nodes to see if their weak references to their nodes/edges are to Nonetypes - i.e.  the node
        no longer exists (and so the edge should be deleted) """
        self._run_operation()

        to_remove = []
        for i, edge in enumerate(self.edges):
            if not edge.check_connected():
                to_remove.append(i)
        for i in reversed(to_remove):
            del self.edges[i]

        # Check all weak references in Node objects to edges
        for node in self.nodes:
            node.remove_incomplete_edges()

    def create_node(self, level: int, document_name: str, content: str):
        if document_name != "Inferred":
            id_n = self.levels_tally[level]
        else:
            id_n = self.inferred_entity_count
        new_node = Node(level=level,
                        id_n=id_n,
                        document_name=document_name,
                        content=content)
        self.nodes.append(new_node)
        self.node_content.append(content)
        return new_node

    def create_nodes(self, data: dict, document_name: str, level: int):
        """Recursive method that creates nodes out of all the entries in a json document."""
        self._run_operation()

        if type(data) is list:
            for d in data:
                self.levels_tally[level] += 1
                self.create_node(level, document_name, d)
        else:
            for key in data.keys():
                if key != "None":
                    self.levels_tally[level] += 1
                    self.create_node(level, document_name, key)
                self.create_nodes(data[key], document_name, level+1)

    def build_flow_edges(self, document: dict):
        """Adds all edges that make up the structure of the document read from top to bottom."""
        document_nodes = [node for node in self.nodes if node.document_name == document]

        for i, node in enumerate(document_nodes[1:]):
            self.create_edge(parent_node=document_nodes[i], child_node=node, edge_type="Flow")

    def build_structural_edges(self, document: dict):
        """Builds edges which represent ownership i.e. document owns headings, headings own paragraphs."""
        document_nodes = [node for node in self.nodes if node.document_name == document]

        for i, node in enumerate(reversed(document_nodes)):
            node_level = node.level
            possible_owners = document_nodes[:-(i+1)]

            for p in reversed(possible_owners):
                p_level = p.level

                if p_level < node_level:
                    # It's the owner
                    self.create_edge(parent_node=p, child_node=node, edge_type="Structural")

                    break

    def create_edge(self, parent_node: Node, child_node: Node, edge_type: str):
        """The only place where edges can be created."""
        new_edge = Edge(parent_node, child_node, edge_type)
        self.edges.append(new_edge)
        parent_node.add_edge(new_edge)
        child_node.add_edge(new_edge)

    def create_document_edges(self, document: dict):
        self._run_operation()

        self.build_flow_edges(document)
        self.build_structural_edges(document)

    def harvest_entity_links(self):
        """
        Types:
        - Key words - A single node for a word that is shared. Will eventually want to exclude some words.

        Be sure to check the created edges dont already exist - might be easier to wipe them all out first.
        :return:
        """
        self._run_operation()

        starting_nodes = len(self.nodes)

        for i in range(starting_nodes):
            node_1 = self.nodes[i]
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
                                    self.create_edge(parent_node=new_node, child_node=node_1, edge_type=f"Keyword-{word_1}")
                                    self.create_edge(parent_node=new_node, child_node=node_2,
                                                     edge_type=f"Keyword-{word_1}")

    def create_new_inferred_entity(self, content: str):
        """Checks if a new word exists as an entity in the graph already and that it isnt a common word. If not, it
        creates a new node named this."""
        all_node_content = self.node_content
        if content in all_node_content:
            return self.nodes[all_node_content.index(content)]
        else:
            if content not in common_words:
                new_entity = self.create_node(level=0, document_name="Inferred", content=content)
                self.inferred_entity_count += 1
                return new_entity

    def return_node(self, node_identifier):
        """The most efficient way of identifying the node from the identifier"""
        for node in self.nodes:
            if node.identifier == node_identifier:
                return node
        print("Node does not exist")

    def compute_node_embeddings(self):
        self._run_operation()

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

    def display_graph_networkx(self):
        self._run_operation()

        colours = ['blue', 'red', 'green', 'orange', "yellow"]
        document_identifiers = [node.document_name for node in self.nodes]
        edge_types = [edge.edge_type for edge in self.edges]
        unique_documents = list(set(document_identifiers))
        unique_edge_types = list(set(edge_types))
        node_identifiers = [node.identifier for node in self.nodes]
        node_content = [node.content for node in self.nodes]
        node_embeddings = [node.embedding for node in self.nodes]

        G = nx.DiGraph()
        G.add_edges_from([[edge.parent_node().identifier, edge.child_node().identifier] for edge in self.edges])

        # pos = nx.spring_layout(G)
        pos = {label:node_embeddings[i] for i, label in enumerate(node_identifiers)}
        labels = {node_identifier: node_identifier for node_identifier, node_content in zip(node_identifiers, node_content)}
        node_colour_map = [colours[unique_documents.index(value)] for value in document_identifiers]
        edge_colour_map = [colours[unique_edge_types.index(value)] for value in edge_types]

        nx.draw(G, pos, node_color=node_colour_map, edge_color=edge_colour_map)
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=6)
        plt.show(block=True)
        plt.interactive(False)

    def display_graph_gephi(self):
        # The following commented code is from an attempt to stream the graph on a port.
        # self._run_operation()
        #
        # stream = gephistreamer.Streamer(gephistreamer.streamer.GephiREST(hostname="localhost", port=8080,
        #                                                                workspace="Workspace 1"))
        # for i in range(10):
        #     node = gephistreamer.graph.Node(self.nodes[i].content)
        #     stream.add_node(node)
        # node2 = gephistreamer.graph.Node(self.nodes[10].content)
        # stream.add_node(node2)
        # edge = gephistreamer.graph.Edge(node, node2)
        # stream.add_edge(edge)
        # stream.commit()

        # The following instead just launces gephi with the csv.
        # Save csv
        save_graph_to_csv(graph=self, file_name=self.graph_name)
        os.system(f"/home/sam/Programs/gephi-0.10.1/bin/gephi ./Data/Saved-Graphs/CSV/{self.graph_name}-edges.csv")

    def delete_node(self, node_id: str):
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

        # Delete node
        del self.nodes[node_index]

        # TODO: Update levels tally

    def decompose_nodes(self):
        """
        :return:
        """
        self._run_operation()

        print("Original Nodes: " + str(len(self.nodes)))
        new_nodes_count = 0
        deleted_nodes_count = 0

        to_delete = []
        all_new_nodes = []
        all_new_edges = []
        for i, node in enumerate(self.nodes):
            existing_nodes_at_level = self.levels_tally[node.level + 1]

            new_nodes, new_edges = node.decompose(existing_nodes_at_level=existing_nodes_at_level)

            if len(new_nodes) > 1:
                deleted_nodes_count += 1
                new_nodes_count += len(new_nodes)
                to_delete.append(i)
                all_new_nodes += new_nodes
                all_new_edges += new_edges

                # Update levels tally
                self.levels_tally[node.level] -= 1
                self.levels_tally[node.level + 1] += len(new_nodes)

        for i in reversed(to_delete):
            self.delete_node(self.nodes[i].identifier)

        self.nodes += all_new_nodes
        self.edges += all_new_edges

        # TODO: Remember to update the content store.

    def recompose_nodes(self):
        """
        Use document structure to consolidate nodes into smaller ones
        :return:
        """
        self._run_operation()


if __name__ == "__main__":
    file = load_json_entity("Immanuel Kant - Wikipedia.json")
    file2 = load_json_entity("Thus Spoke Zarathustra - Wikipedia.json")

    graph = KnowledgeGraph()
    # For calling directly on graph (may need to add to manager interface.
    # graph.delete_node("Nietzsche-0:1")
    # graph.remove_invalid_edges_and_nodes()
    # graph.compute_node_embeddings()
    graph.add_document_to_graph(file, "Kant")
    graph.add_document_to_graph(file2, "Zarathustra")
    graph.compute_node_embeddings()
    graph.remove_invalid_edges_and_nodes()
    graph.display_graph()
