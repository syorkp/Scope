from Utilitites.load_json import load_json
from KnowledgeGraph.graph import KnowledgeGraph
import cProfile
import pstats

if __name__ == "__main__":
    file = load_json("Immanuel Kant - Wikipedia.json")
    file2 = load_json("Friedrich Nietzsche - Wikipedia.json")
    file3 = load_json("Thus Spoke Zarathustra - Wikipedia.json")
    file4 = load_json("Ubermensch - Wikipedia.json")
    file5 = load_json("Human, All Too Human - Wikipedia.json")
    file6 = load_json("Orchestra of Bubbles - Wikipedia.json")
    profile = cProfile.Profile()
    profile.enable()

    graph = KnowledgeGraph()
    # graph.add_document_to_graph(file, "Kant")
    graph.add_document_to_graph(file2, "Nietzsche")
    # graph.add_document_to_graph(file3, "Zarathustra")
    # graph.add_document_to_graph(file4, "Ubermensch")
    # graph.add_document_to_graph(file5, "Human, All Too Human")
    # graph.add_document_to_graph(file6, "Bubbles")
    # graph.harvest_entity_links()
    graph.delete_node("Nietzsche-0:1")
    graph.remove_invalid_edges_and_nodes()
    graph.compute_node_embeddings()
    # ps = pstats.Stats(profile)
    # ps.sort_stats("tottime")
    # ps.print_stats()

    graph.display_graph()


