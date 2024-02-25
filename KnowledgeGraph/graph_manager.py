import copy
import cProfile
import pstats

from KnowledgeGraph.edges import Edge
from KnowledgeGraph.graph import KnowledgeGraph

from Webscraper.wikipedia_scraper import WikipediaScraper

from Utilitites.csv_operations import save_graph_to_csv, load_graph_elements_from_csv
from Utilitites.json_operations import load_json_entity


class GraphManager:
    """
    Manager class to handle multiple graphs and graph-graph operations.
    """

    # TODO: To add in the ability to run things concurrently e.g. display graphs while also having entity linkage
    #  happening in the background.

    def __init__(self, profile: bool):
        self.profile = profile
        if self.profile:
            self.profiler = cProfile.Profile()
            self.profiler.enable()

        self.graphs = {}

    def save_graph(self, graph_name: str):
        """
        Save graph to hard drive.
        Supported formats:
        - CSV
        """

        # TODO: Build capability to save in other formats.
        save_graph_to_csv(self.graphs[graph_name], graph_name)

    def load_graph_csv(self, graph_name: str, file_name: str):
        """Loads a full graph from CSV."""

        # Get the full csv of graph nodes and edges (in csv form)
        graph_nodes, graph_edges = load_graph_elements_from_csv(file_name)
        new_graph = self.graphs[graph_name]

        # Creating nodes
        node_contents = graph_nodes.content
        node_id_n = graph_nodes.id_n
        node_level = graph_nodes.level
        node_identifiers = graph_nodes.node_identifier
        node_documents = graph_nodes.document

        for identifier, level, id_n, content, document in zip(node_identifiers, node_level, node_id_n, node_contents,
                                                              node_documents):
            new_node = new_graph.create_node(level=level, document_name=document, content=content)
            new_node.id_n = id_n
            new_node.identifier = identifier

        # Creating Edges
        edge_identifiers = graph_edges.edge_identifier
        edge_type = graph_edges.edge_type
        edge_weight = graph_edges.edge_weight
        edge_source = graph_edges.source
        edge_target = graph_edges.target

        for identifier, type, weight, source, target in zip(edge_identifiers, edge_type, edge_weight, edge_source,
                                                            edge_target):
            parent_node = new_graph.return_node(source)
            child_node = new_graph.return_node(target)
            new_edge = Edge(parent=parent_node, child=child_node, edge_type=type, edge_weight=weight)
            new_graph.edges.append(new_edge)

            parent_node.add_edge(new_edge)
            child_node.add_edge(new_edge)

    def build_graph_from_wikipedia_url(self, graph_name: str, url: str, degree: int):
        """

        :param graph_name:
        :param url: Wikipedia URL
        :param degree: The degree of separation with the original article to be included. 0 would only use the original
        page.
        :return:
        """
        # Create a wikipedia scraper
        wiki_scraper = WikipediaScraper(starting_url=url)

        # Creates json for the original page combined with all articles with separation within degrees. Also keeps
        # track of links between original and others.
        original_article_name = wiki_scraper.create_wiki_json_from_article_links(degree=degree)

        # Load the json of the documents and their links.
        documents = load_json_entity(f"{original_article_name}-{degree}.json")
        original_document = documents[0][original_article_name]
        across_document_links = load_json_entity(f"{original_article_name}-{degree}_links.json")

        # Initialise graph - create all nodes etc.
        self.create_graph(graph_name=graph_name)
        for document in documents:
            doc_name = list(document.keys())[0]
            self.graphs[graph_name].add_document_to_graph(document, document_name=doc_name)

        # Create the across-document edges
        for key_1 in across_document_links.keys():
            for key_2 in across_document_links[key_1].keys():
                for key_3 in across_document_links[key_1][key_2].keys():
                    for p, para in enumerate(across_document_links[key_1][key_2][key_3]):
                        # Find the parent node (the node in the original document)
                        original_document_content = documents[0][key_1][key_2][key_3][p]
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

    def create_graph(self, graph_name: str):
        if graph_name in self.graphs.keys():
            print(f"Graph {graph_name} already exists.")
            overwrite = input("Overwrite existing? (y/n)")
            if overwrite.lower() == "y":
                print("Graph overwritten.")
            else:
                print("Graph not created or overwritten.")
                return
        self.graphs[graph_name] = KnowledgeGraph(graph_name)

    def add_json_to_graph(self, graph_name: str, json_file_name: str):
        """Add a new json-encoded document to the graph."""
        file = load_json_entity(json_file_name)
        self.graphs[graph_name].add_document_to_graph(file, json_file_name)

    def run_routine_graph_computations(self, graph_name: str):
        """Run all the routine operations of the graph. Intended for when all the desired elements have been added to
        the graph"""
        # self.graphs[graph_name].harvest_entity_links()
        self.graphs[graph_name].compute_node_embeddings()

    def add_website_to_graph(self, graph_name: str, url: str):   # TODO: Test
        """Given a (wikipedia) URL and a graph name, saves the page to a json file and loads that to a graph."""

        # Save a website (assumed to be wikipedia) to json.  TODO: In future, build handling for other types of urls.
        wiki_scraper = WikipediaScraper(starting_url=url)
        page_name = wiki_scraper.get_wiki_page_name(url=url)
        wiki_scraper.create_wiki_json_from_original_url()

        # Add the saved website to the graph.
        self.add_json_to_graph(graph_name=graph_name, json_file_name=page_name)

    def merge_graphs(self, graph_1_name: str, graph_2_name: str, combined_graph_name: str):  # TODO: FINISH and test
        # Create new combined graph
        self.create_graph(graph_name=combined_graph_name)

        # Add all nodes and edges to graph.
        self.graphs[combined_graph_name].nodes += self.graphs[graph_1_name].nodes + \
                                                  self.graphs[graph_2_name].nodes
        self.graphs[combined_graph_name].edges += self.graphs[graph_1_name].edges + \
                                                  self.graphs[graph_2_name].edges
        ...

    def split_graphs(self):
        ...  # What could the criteria for a split be?

    def create_subgraph(self):
        ...  # Criteria for selection to a subgraph. What would the difference be with split? That there's no overlap
        # in split?

    def display_graph(self, graph_name: str, display_mode: str = "networkx"):
        """

        :param graph_name:
        :param display_mode: Determines which mode to display graph. Options: networkx, gephi.
        :return:
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
            print("Decomposing graph.")
            if graph_name[-1].isdigit():
                new_graph_name = f"{graph_name[:-1]}{(int(graph_name[-1]) + 1)}"
            else:
                new_graph_name = graph_name + "-1"
            self.graphs[new_graph_name] = copy.copy(self.graphs[graph_name])
            self.graphs[new_graph_name].decompose_nodes()
            self.graphs[new_graph_name].remove_invalid_edges_and_nodes()
        else:
            raise Exception("Graph is not decomposable")

    def close(self):
        if self.profile:
            ps = pstats.Stats(self.profiler)
            ps.sort_stats("tottime")
            ps.print_stats()
