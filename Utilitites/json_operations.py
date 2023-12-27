import json


def load_json_entity(file_name):
    file_name = "Data/Entities/" + file_name
    with open(file_name, "r") as file:
        data = json.load(file)
    return data


def load_json_graph(file_name):
    ...


def convert_graph_to_json(graph):
    # What would a graph actually look like in JSON?
    ...


def save_json(graph, file_name):
    ...

