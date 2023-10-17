from Utilitites.load_json import load_json
from object_based import KnowledgeGraph
from OldVersions.basic2 import KnowledgeGraph2
import cProfile
import pstats


if __name__ == "__main__":
    file = load_json("Immanuel Kant - Wikipedia.json")
    file2 = load_json("Friedrich Nietzsche - Wikipedia.json")
    file3 = load_json("Thus Spoke Zarathustra - Wikipedia.json")
    file4 = load_json("Ubermensch - Wikipedia.json")
    file5 = load_json("Human, All Too Human - Wikipedia.json")

    graph = KnowledgeGraph()
    # graph.add_document_to_graph(file, "Kant")
    graph.add_document_to_graph(file2, "Nietzsche")
    graph.add_document_to_graph(file3, "Zarathustra")
    # graph.add_document_to_graph(file4, "Ubermensch")
    # graph.add_document_to_graph(file5, "Human, All Too Human")
    graph.compute_node_embeddings()
    graph.create_interdocument_edges()
    graph.display_graph()
