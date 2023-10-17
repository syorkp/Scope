import json


def load_json(file_name):
    file_name = "Data/" + file_name
    with open(file_name, "r") as file:
        data = json.load(file)
    return data