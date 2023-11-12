import weakref
from KnowledgeGraph.edges import Edge


class Node:

    def __init__(self, level: int, id_n: int, document_name: str, content: str):
        self.identifier = f"{document_name}-{level}:{id_n}"
        self.id_n = id_n
        self.level = level
        self.content = content
        self.document_name = document_name

        self.edges = []
        self.embedding = []

        self.individual_words = [word.lower().replace(".", "") for word in content.split(" ")]

        # For decompositions
        self.splits_into = len(content.split(". "))

    def add_edge(self, edge: Edge):
        self.edges.append(weakref.ref(edge))

    def remove_edge(self, edge_to_remove: Edge):
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

    def decompose(self, existing_nodes_at_level):
        # TODO: Compartmentalise this class
        if self.splits_into > 1:
            new_edges = []
            new_nodes = []

            # Isolate this instance's structural edges
            structural_edges = [edge for edge in self.edges if edge().edge_type == "Structural"]
            flow_edges = [edge for edge in self.edges if edge().edge_type == "Flow"]
            inferred_edges = [edge for edge in self.edges if edge().edge_type[:7] == "Keyword"]

            components = self.content.split(". ")

            for i in range(self.splits_into):
                new_node = Node(level=self.level + 1, id_n=existing_nodes_at_level+i+1, document_name=self.document_name,
                                content=components[i])
                new_nodes.append(new_node)

                # Add structural edges
                for s_edge in structural_edges:
                    new_structural_edge = Edge(parent=s_edge().parent_node(), child=new_node, edge_type="Structural")
                    new_edges.append(new_structural_edge)

            input_flow_edge = [edge for edge in flow_edges if edge().child_node() is self][0]
            output_flow_edge = [edge for edge in flow_edges if edge().parent_node() is self][0]

            for i, node in enumerate(new_nodes):
                if i == 0:
                    # The first node inherits the flow edge to the original node
                    new_flow_edge = Edge(parent=input_flow_edge().parent_node(), child=node, edge_type="Flow")
                elif i == self.splits_into - 1:
                    # The last node inherits the outgoing flow edge in addition to the edge in between the last one.
                    new_flow_edge = Edge(parent=new_nodes[i-1], child=node, edge_type="Flow")
                    new_edges.append(new_flow_edge)
                    new_flow_edge = Edge(parent=node, child=output_flow_edge().child_node(), edge_type="Flow")
                else:
                    # Other Nodes get edges in between them.
                    new_flow_edge = Edge(parent=new_nodes[i-1], child=node, edge_type="Flow")
                new_edges.append(new_flow_edge)

            # Inferred entity edges
            for edge in inferred_edges:
                # Find which of the newly created nodes contains the specified entity
                inferred_entity_node = edge.parent_node()
                inferred_entity_content = inferred_entity_node.content
                relevant_nodes = [node for node in new_nodes if inferred_entity in node.individual_words]
                for node in relevant_nodes:
                    new_inferred_edge = Edge(parent=inferred_entity_node, child=node, edge_type=f"Inferred-{inferred_entity_content}")
                    new_edges.append(new_inferred_edge)

            return new_nodes, new_edges
        else:
            return [self], self.edges
