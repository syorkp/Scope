
def flatten_list_of_lists(unflattened_list):
    while type(unflattened_list[0]) is list:
        flattened_list = [l for li in unflattened_list for l in li]
        unflattened_list = flattened_list
    return unflattened_list


def flatten_document_to_list_elements(document):
    if type(document) == dict:
        components = []
        for key in document.keys():
            component = flatten_document_to_list_elements(document[key])
            components.append(component)
        return flatten_list_of_lists(components)
    elif type(document) == list:
        if type(document[0]) == list:
            return flatten_list_of_lists(document)
        elif type(document[0]) == str:
            return document
        else:
            raise Exception("Utilities: Data not provided in correct format.")
