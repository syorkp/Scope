import weakref


class Edge:

    def __init__(self, parent, child, edge_type: str, edge_weight: int = 1):   # TODO: Do typing by fixing recursive import problem.
        self.identifier = f"{parent.identifier}-{child.identifier}-{edge_type}"
        self.edge_type = edge_type
        self.edge_weight = edge_weight

        self.parent_node = weakref.ref(parent)
        self.child_node = weakref.ref(child)

    def delete_edge(self):
        self.parent_node().remove_edge(self)
        self.child_node().remove_edge(self)

    def check_connected(self) -> bool:
        if self.parent_node() is None:
            print(f"Parent dead, deleting {self.identifier}")
            return False
        if self.child_node() is None:
            print(f"Child dead, deleting {self.identifier}")
            return False
        return True
