import weakref


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

    def remove_edge(self, edge_to_remove):
        edge_ids = [edge().identifier for edge in self.edges]
        edge_to_remove_index = edge_ids.index(edge_to_remove.identifier)
        del self.edges[edge_to_remove_index]

    def get_child_edges(self):
        return [edge() for edge in self.edges if edge().parent_node is self]

    def get_parent_edges(self):
        return [edge() for edge in self.edges if edge().child_node is self]

    def compute_individual_word_indices(self):
        ...

    def remove_incomplete_edges(self):
        to_remove = []

        for i, edge in enumerate(self.edges):
            if edge() is None:
                print("Edge no longer exists, deleting")
                to_remove.append(i)
        for i in reversed(to_remove):
            del self.edges[i]
