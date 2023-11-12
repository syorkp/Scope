from Utilitites.load_json import load_json
from KnowledgeGraph.graph_manager import GraphManager

if __name__ == "__main__":
    file_names = ["Immanuel Kant - Wikipedia.json", "Friedrich Nietzsche - Wikipedia.json",
                  "Thus Spoke Zarathustra - Wikipedia.json", "Ubermensch - Wikipedia.json",
                  "Human, All Too Human - Wikipedia.json", "Orchestra of Bubbles - Wikipedia.json"]

    graph_manager = GraphManager(profile=False)
    graph_manager.create_graph("Nietzsche")
    graph_manager.add_json_to_graph("Nietzsche", file_names[1])
    # graph_manager.decompose_graph("Nietzsche")
    graph_manager.run_routine_graph_computations("Nietzsche")
    graph_manager.display_graph("Nietzsche")
    graph_manager.close()




