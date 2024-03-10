import copy
import cProfile
import os
import pstats

from KnowledgeGraph.edges import Edge
from KnowledgeGraph.graph import KnowledgeGraph

from Webscraper.wikipedia_scraper import WikipediaScraper

from Utilitites.csv_operations import save_graph_to_csv, load_graph_elements_from_csv
from Utilitites.json_operations import load_json_entity


class GraphManager:
    """
    Manager class to handle multiple graphs and graph-graph operations.

    Methods stdout a log of operations performed.
    """

    # TODO: To add in the ability to run things concurrently e.g. display graphs while also having entity linkage
    #  happening in the background.

    def __init__(self, profile: bool):
        self.profile = profile
        if self.profile:
            self.profiler = cProfile.Profile()
            self.profiler.enable()

        self.graphs = {}
        self._build_directories()

        print("Graph Manager created")

    @staticmethod
    def _build_directories():
        """Makes sure that all the directories necessary to save and load data are created."""

        if not os.path.isdir("Data"):
            os.mkdir("Data")
        if not os.path.isdir("Data/Entities"):
            os.mkdir("Data/Entities")
        if not os.path.isdir("Data/PDFs"):
            os.mkdir("Data/PDFs")
        if not os.path.isdir("Data/Entities/Saved-Graphs"):
            os.mkdir("Data/Entities/Saved-Graphs")
        if not os.path.isdir("Data/Entities/Saved-Graphs/CSV"):
            os.mkdir("Data/Entities/Saved-Graphs/CSV")

        print("Data directories initialised")

    def save_graph(self, graph_name: str):
        """
        Save specified graph to CSV encoding.

        :param graph_name:
        """

        # TODO: Build capability to save in other formats.
        save_graph_to_csv(self.graphs[graph_name], graph_name)

        print("Graph saved")

    def load_graph_csv(self, graph_name: str, file_name: str):
        """
        Loads a full graph from CSV-encoded graph to a KnowledgeGraph object.

        :param graph_name: Name to which the loaded KnowledgeGraph is assigned
        :param file_name: Doesn't include -edge/node suffix or .csv.
        """

        # Get the full csv of graph nodes and edges (in csv form)
        graph_nodes, graph_edges = load_graph_elements_from_csv(file_name)
        new_graph = self.graphs[graph_name]

        # Creating nodes
        node_contents = graph_nodes.content
        node_id_ns = graph_nodes.id_n
        node_levels = graph_nodes.level
        node_identifiers = graph_nodes.node_identifier
        node_documents = graph_nodes.document

        for node_identifier, node_level, node_id_n, node_content, node_document in zip(node_identifiers, node_levels,
                                                                                       node_id_ns, node_contents,
                                                                                       node_documents):
            new_node = new_graph.create_node(level=node_level, document_name=node_document, content=node_content)
            new_node.id_n = node_id_n
            new_node.identifier = node_identifier

        # Creating Edges
        edge_identifiers = graph_edges.edge_identifier
        edge_types = graph_edges.edge_type
        edge_weights = graph_edges.edge_weight
        edge_sources = graph_edges.source
        edge_targets = graph_edges.target

        for edge_identifier, edge_type, edge_weight, edge_source, edge_target in zip(edge_identifiers, edge_types,
                                                                                     edge_weights, edge_sources,
                                                                                     edge_targets):
            try:
                parent_node = new_graph.return_node(edge_source)
            except Exception:
                raise Exception("Necessary node has not been created from CSV loading")

            try:
                child_node = new_graph.return_node(edge_target)
            except Exception:
                raise Exception("Necessary node has not been created from CSV loading")

            new_edge = Edge(parent=parent_node, child=child_node, edge_type=edge_type, edge_weight=edge_weight)
            new_graph.edges.append(new_edge)

            parent_node.add_edge(new_edge)
            child_node.add_edge(new_edge)

        print("Graph loaded from CSV")

    def build_graph_from_wikipedia_url(self, graph_name: str, url: str, degree: int):
        """
        Given the URL to a wikipedia page, creates a graph using that page and any pages that are linked within the
        specified number of degrees.

        :param graph_name:
        :param url: Wikipedia URL
        :param degree: The degree of separation with the original article to be included. 0 would only use the original
        page.
        """

        # Create a wikipedia scraper
        wiki_scraper = WikipediaScraper(starting_url=url)

        # Creates json for the original page combined with all articles with separation within degrees. Also keeps
        # track of links between original and others.
        document, links, original_article_name = wiki_scraper.create_wiki_json_from_article_links(url=url, degree=degree)
        self.save_json([document], links, f"{original_page_title}-{degree}")

        # Load the json of the documents and their links.
        documents = load_json_entity(f"{original_article_name}-{degree}.json")
        across_document_links = load_json_entity(f"{original_article_name}-{degree}_links.json")

        # Initialise graph - create all nodes etc.
        self.create_graph(graph_name=graph_name)
        if type(documents) == list:
            documents = documents[0]

        num_linked_documents = len(documents.keys())
        print(f"Found {num_linked_documents} Within-Degree Pages")

        for i, doc_name in documents.keys():
            specified_document = {doc_name: documents[doc_name]}
            self.graphs[graph_name].add_document_to_graph(specified_document, document_name=doc_name)

        # If degree is zero, dont bother truing to build across-document links.
        if degree == 0:
            return

        # Create the across-document edges
        for key_1 in across_document_links.keys():
            for key_2 in across_document_links[key_1].keys():
                for key_3 in across_document_links[key_1][key_2].keys():
                    for p, para in enumerate(across_document_links[key_1][key_2][key_3]):
                        # Find the parent node (the node in the original document)
                        original_document_content = documents[key_1][key_2][key_3][p]
                        parent_node_index = self.graphs[graph_name].node_content.index(original_document_content)
                        parent_node = self.graphs[graph_name].nodes[parent_node_index]

                        for linked_document in para:
                            # TODO: Build a method to find the ID of a point in a document, use to set the IDs, as well
                            #  as to provide a means of accessing them more easily.

                            # Find the child node (the linked document)
                            child_node_index = self.graphs[graph_name].node_content.index(linked_document)
                            child_node = self.graphs[graph_name].nodes[child_node_index]

                            # Create link with contents
                            self.graphs[graph_name].create_edge(parent_node=parent_node, child_node=child_node,
                                                                edge_type="Hyperlink")
        # TODO: Find way to build ownership edges into system for de/reconstruction.
        # TODO: Get all links in between pages already existing
        print(f"Graph {graph_name} created from Wikipedia URL")

    def create_graph(self, graph_name: str):
        """
        Instantiates a KnowledgeGraph and assigns it to graph_name in the self.graphs dict.

        Gives an option for overwriting an existing KnowledgeGraph already assigned to graph_name.

        :param graph_name:
        """

        if graph_name in self.graphs.keys():
            print(f"Graph {graph_name} already exists.")
            overwrite = input("Overwrite existing? (y/n)")
            if overwrite.lower() == "y":
                print("Graph overwritten.")
            else:
                print("Graph not created or overwritten.")
                return
        self.graphs[graph_name] = KnowledgeGraph(graph_name)

        print(f"Created new graph: {graph_name}")

    def _add_json_to_graph(self, graph_name: str, json_file_name: str):
        """
        Add a new json-encoded document to the graph.

        :param graph_name:
        :param json_file_name:
        """

        file = load_json_entity(json_file_name)
        self.graphs[graph_name].add_document_to_graph(file, json_file_name)

        print(f"Added JSON {json_file_name} to graph {graph_name}")

    def run_routine_graph_computations(self, graph_name: str):
        """
        Run all the routine operations of the graph:
        1. Create links between entities in the graph.
        2. Compute node embeddings

        Intended for when all the desired elements have been added to the graph.

        :param graph_name:
        """

        # self.graphs[graph_name].harvest_entity_links()
        self.graphs[graph_name].compute_node_embeddings()
        print(f"Node embeddings computed for graph {graph_name}")

    def add_website_to_graph(self, graph_name: str, url: str):
        """
        Given a (wikipedia) URL and a graph name, converts the wikipedia page to a json file and loads that to the
        specified graph.

        :param graph_name:
        :param url:
        """

        # Save a website (assumed to be wikipedia) to json.  TODO: In future, build handling for other types of urls.
        wiki_scraper = WikipediaScraper(starting_url=url)
        page_name = wiki_scraper.get_wiki_page_name(url=url)
        wiki_scraper.create_wiki_json_from_original_url()

        # Add the saved website to the graph.
        self._add_json_to_graph(graph_name=graph_name, json_file_name=f"{page_name}.json")
        print(f"Added URL {url} to graph {graph_name}")

    def merge_graphs(self, graph_1_name: str, graph_2_name: str, combined_graph_name: str):
        """
        Provided the names of two instantiated graphs, combines them into a new graph (without deleting them) and
        removes any node/edge repeats.

        :param graph_1_name:
        :param graph_2_name:
        :param combined_graph_name:
        """

        # Create new combined graph
        self.create_graph(graph_name=combined_graph_name)

        # Add all nodes and edges to graph.
        self.graphs[combined_graph_name].nodes += self.graphs[graph_1_name].nodes + \
                                                  self.graphs[graph_2_name].nodes
        self.graphs[combined_graph_name].edges += self.graphs[graph_1_name].edges + \
                                                  self.graphs[graph_2_name].edges
        # TODO: Check if I need to do a deep copy

        print(f"Merged graphs {graph_1_name} and {graph_2_name} to {combined_graph_name}")
        # TODO: Build in checking for node repeats and remove but keep all unique edges.

    def split_graphs(self):
        """
        Given criteria, creates a subgraph of a specified graph, and a graph from what is not included in the subgraph.
        """

        ...  # What could the criteria for a split be?
        self.create_subgraph()
        # Create graph from what remains...

    def create_subgraph(self):
        """
        Given criteria, creates a subgraph of a specified graph.
        """
        ...

    def display_graph(self, graph_name: str, display_mode: str = "networkx"):
        """
        Displays graph graph_name according to a selected display mode.

        :param graph_name:
        :param display_mode: Determines which mode to display graph. Options: networkx, gephi.
        """

        self.graphs[graph_name].remove_invalid_edges_and_nodes()

        if display_mode == "gephi":
            self.graphs[graph_name].display_graph_gephi()
        elif display_mode == "networkx":
            self.graphs[graph_name].display_graph_networkx()
        else:
            raise Exception("Invalid display mode given.")

    def decompose_graph(self, graph_name: str):
        """
        Given a graph, goes through its elements and splits them into smaller elements.
        1. Check if it's possible to decompose any parts of the graph.
        2. Creates a new graph with a number at the end to indicate that the graph has undergone so many decompositions.
    `   3. Decomposes nodes where possible.
        4. Removes any invalid nodes or edges.

        :param graph_name:
        """
        # TODO: Need to determine how many decompositions can be done - to allow a sliding scale to be possible. Could
        #  then have an input option for level of max decompositions.

        decomposable = False
        for node in self.graphs[graph_name].nodes:
            if node.splits_into > 1:
                decomposable = True
                break

        if decomposable:
            print(f"Decomposing graph {graph_name}.")
            if graph_name[-1].isdigit():
                new_graph_name = f"{graph_name[:-1]}{(int(graph_name[-1]) + 1)}"
            else:
                new_graph_name = graph_name + "-1"

            self.graphs[new_graph_name] = copy.copy(self.graphs[graph_name])
            self.graphs[new_graph_name].decompose_nodes()
            self.graphs[new_graph_name].remove_invalid_edges_and_nodes()
        else:
            raise Exception(f"Graph {graph_name} is not decomposable")

    def close(self):
        """
        Closes the graph manager and displays profiler output.
        """

        if self.profile:
            ps = pstats.Stats(self.profiler)
            ps.sort_stats("tottime")
            ps.print_stats()
