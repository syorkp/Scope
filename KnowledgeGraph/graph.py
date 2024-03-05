import os
import networkx as nx

import matplotlib.pyplot as plt


import spacy
import numpy as np

from sklearn.decomposition import PCA

from KnowledgeGraph.graph_precursor import Graph
from KnowledgeGraph.nodes import Node
from KnowledgeGraph.edges import Edge
from Models.common_words import common_words
from Utilitites.json_operations import load_json_entity
from Utilitites.csv_operations import save_graph_to_csv


class KnowledgeGraph(Graph):
    """
    A Knowledge Graph object, including attributes and methods to allow instantiation and necessary operations for
    building and processing data in the format of a basic Knowledge Graph ontology.

    Principles underlying design:
    - do not store information in more than one place unless this is accomplished through weak references (thus deletion
    of one is deletion everywhere).
    - Everything is object based

    Shouldn't use stdout at this level, rather raise exceptions.
    """

    def __init__(self, graph_name: str, autosave: bool = True):
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

        self.incidence_matrix = None
        self.adjacency_matrix = None

    def _run_operation(self):
        """
        A method that runs every time a major operation occurs, to allow maintenance to be carried out e.g. autosave.
        """

        if self.autosave_graph:
            for f in self.maintained_formats:
                ...  # TODO: Autosave

    def add_document_to_graph(self, data: dict, document_name: str):
        """
        Adds a json-encoded document to the graph.

        :param data: Structured document in json format.
        :param document_name:
        """

        self._run_operation()

        if document_name in self.documents_used:
            print("Error, document name already used...")
            return

        self.documents_used.append(document_name)
        self._create_nodes(data, document_name, level=0)
        self.create_document_edges(document_name)

    def compute_adjacency_matrix(self):
        """
        Produces adjacency (connectivity) matrix for the graph and assigns it to an attribute. This encodes which nodes
        are connected (and by how many edges). Direction of edges is specified according to start node being row.

        The adjacency matrix has N rows and N columns, N being the total number of nodes in the graph.
        """

        node_identifiers = [node.identifier for node in self.nodes]
        num_nodes = len(node_identifiers)
        adjacency_matrix = np.zeros((num_nodes, num_nodes))
        for edge in self.edges:
            start_node_index = node_identifiers.index(edge[0])
            end_node_index = node_identifiers.index(edge[1])
            adjacency_matrix[start_node_index, end_node_index] += 1

        self.adjacency_matrix = adjacency_matrix

    def compute_incidence_matrix(self):
        """
        Produces incidence matrix for the graph and assigns it to an attribute. This encodes which nodes and which edges
        touch. Direction is provided sign of entry. Note that reciprocal opposite edges will therefore cancel out.

        The incidence matrix has N rows and E columns, N being the total number of nodes in the graph, and E being the
        total number of edges.
        """
        node_identifiers = [node.identifier for node in self.nodes]

        num_nodes = len(node_identifiers)
        num_edges = len(self.edges)

        incidence_matrix = np.zeros((num_nodes, num_edges))
        for e, edge in enumerate(self.edges):
            start_node_index = node_identifiers.index(edge.parent_node)
            end_node_index = node_identifiers.index(edge.child_node)

            incidence_matrix[start_node_index, e] += 1
            incidence_matrix[end_node_index, e] -= 1

        self.incidence_matrix = incidence_matrix

    def remove_invalid_edges_and_nodes(self):
        """
        Checks all edge/nodes to see if their weak references to their nodes/edges are Nonetypes i.e. the node no
        longer exists. If this is the case, deletes the edge.

        Needs to be called regularly.
        """

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

    def create_node(self, level: int, document_name: str, content: str) -> Node:
        """
        Instantiates a Node object

        :param level: How many levels down in the document the content came from.
        :param document_name: Document from which the content comes.
        :param content: Content assigned to the node.
        :return: The instantiated Node object.
        """

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

    def _create_nodes(self, data: dict, document_name: str, level: int):
        """
        Recursive method that creates nodes out of all the entries in a json document.

        Will call itself (with incremented level) until it reaches lists (where the structural hierarchy ends).

        :param data: Structured document in json format.
        :param document_name: Name of the json document.
        :param level: Point in the structural hierarchy.
        """
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
                self._create_nodes(data[key], document_name, level + 1)

    def _build_flow_edges(self, document_name: str):
        """
        Adds all edges that make up the structure of the document read from top to bottom.

        :param document_name: Name of the document.
        """

        document_nodes = [node for node in self.nodes if node.document_name == document_name]

        for i, node in enumerate(document_nodes[1:]):
            self.create_edge(parent_node=document_nodes[i], child_node=node, edge_type="Flow")

    def _build_structural_edges(self, document_name: str):
        """
        Builds edges which represent ownership i.e. document owns headings, headings own paragraphs.

        :param document_name: Name of the document.
        """

        document_nodes = [node for node in self.nodes if node.document_name == document_name]

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
        """
        Creates an edge object for two specified nodes and adds a weakref to each node of this edge.

        The only place where edges can be created.

        :param parent_node: Parent node
        :param child_node: Child node
        :param edge_type: Indicated edge type e.g. structural, flow
        """

        new_edge = Edge(parent_node, child_node, edge_type)
        self.edges.append(new_edge)
        parent_node.add_edge(new_edge)
        child_node.add_edge(new_edge)

    def create_document_edges(self, document_name: str):
        """
        Creates all the edges for a specified document.

        My ontology includes the following edge types:
        - Flow edges
        - Structural edges.

        :param document_name:
        """
        self._run_operation()

        self._build_flow_edges(document_name)
        self._build_structural_edges(document_name)

    def harvest_entity_links(self):
        """
        Produces potential entity links within the graph.
        1. Goes through all nodes
        2. Checks if any words match between the nodes
        3. Creates a new node to represent the inferred entity.
        4. Links both original nodes to that node.

        Be sure to check the created edges don't already exist -
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
                                new_node = self._create_new_inferred_entity(word_1)
                                if new_node is not None:
                                    self.create_edge(parent_node=new_node, child_node=node_1, edge_type=f"Keyword-{word_1}")
                                    self.create_edge(parent_node=new_node, child_node=node_2,
                                                     edge_type=f"Keyword-{word_1}")

    def _create_new_inferred_entity(self, content: str) -> Node:
        """
        Checks if a new word exists as an entity in the graph already and that it isn't a common word. If not, it
        creates a new node named this.

        :param content: The content which specifies the inferred entity.
        :returns node: The new inferred entity Node instance.
        """
        # TODO: instead of checking every word, could remove all the simple words from the node contents to begin with
        #  for the purpose of this search - might be easier to wipe them all out first.

        all_node_content = self.node_content
        if content in all_node_content:
            return self.nodes[all_node_content.index(content)]
        else:
            if content not in common_words:
                new_entity = self.create_node(level=0, document_name="Inferred", content=content)
                self.inferred_entity_count += 1
                return new_entity

    def return_node(self, node_identifier: str) -> Node:
        """
        Returns a node instance that matches the specified identifier.

        :param node_identifier:
        :returns node: The specified node.
        """

        # TODO: Look for a more efficient way of doing this.
        for node in self.nodes:
            if node.identifier == node_identifier:
                return node
        raise Exception("Node does not exist")

    def compute_node_embeddings(self):
        """
        Uses spacy to embed each node content in vector space, then reduces this vector to its two principal components.

        Saves this to an attribute for each node within the Node class.
        """

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
        """
        Shows a networkx representation of the graph, including colours for document type, and position reflecting the
        PCA node embedding.
        """
        # TODO: Check nodes are all embedded - could do with try except.
        # TODO: Consider moving this and other graph visualisation methods to graph manager or a visualisation service.

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
        """
        Saves graph to csv and launches gephi program to allow exploration of the graph.
        """
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
        # Launch gephi with the csv containing the edges. Note that this will exclude any isolated nodes.
        os.system(f"/home/sam/Programs/gephi-0.10.1/bin/gephi ./Data/Saved-Graphs/CSV/{self.graph_name}-edges.csv")

    def delete_node(self, node_id: str):
        """
        Deletes a node and all associated edges.
        1. Find node via id.
        2. del node
        3. Identifies edges (inefficiently)
        4. Deletes edge using its method, which should remove weakrefs to it in the other Nodes.

        :param node_id:
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

    def remove_node_repeats(self):
        ...

    def remove_edge_repeats(self):
        ...

    def decompose_nodes(self):
        """
        Goes through all nodes in graph, splitting these where possible into smaller nodes (only one level smaller).
        Deletes the original nodes.
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
        """
        self._run_operation()

        # TODO Build.


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
