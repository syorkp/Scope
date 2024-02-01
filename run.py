from KnowledgeGraph.graph_manager import GraphManager


if __name__ == "__main__":
    file_names = ["Immanuel Kant - Wikipedia.json", "Friedrich Nietzsche - Wikipedia.json",
                  "Thus Spoke Zarathustra - Wikipedia.json", "Ubermensch - Wikipedia.json",
                  "Human, All Too Human - Wikipedia.json", "Orchestra of Bubbles - Wikipedia.json"]
    url = "https://en.wikipedia.org/wiki/Friedrich_Nietzsche"
    url2 = "https://en.wikipedia.org/wiki/Alexander_Nehamas"

    graph_manager = GraphManager(profile=False)
    # graph_manager.create_graph("Nietzsche")
    graph_manager.build_graph_from_wikipedia_url(graph_name="Nehamas", url=url2, degree=1)
    # graph_manager.add_json_to_graph("Nietzsche", file_names[1])
    # graph_manager.decompose_graph("Nietzsche")
    # graph_manager.save_graph("Nietzsche")
    # graph_manager.close()

    # graph_manager.load_graph_csv("Nietzsche", file_name="Nietzsche")
    graph_manager.run_routine_graph_computations("Nehamas")

    graph_manager.display_graph("Nehamas", display_mode="gephi")


