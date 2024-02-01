import json
import requests
from bs4 import BeautifulSoup as bs


import numpy as np


class WikipediaScraper:

    def __init__(self, starting_url: str):
        if self.check_url_is_wikipedia(starting_url):
            self.starting_url = starting_url
        else:
            print("Error, incorrect URL provided")

        self.known_motifs = ["[edit]", "\n"] + \
                            [f"[{num}]" for num in range(500)]

        self.enclosing_elements = ["h1", "h2", "h3"]

        self.enclosed_elements = ["p"]

        # For Link Mining
        self.unwanted_link_formats = [
            "_(disambiguation)",
            "en.wikipedia.org/wiki/Main_Page",
            "en.wikipedia.org/wiki/Wikipedia:",
            "en.wikipedia.org/wiki/Special:",
            "en.wikipedia.org/wiki/Portal:",
            "en.wikipedia.org/wiki/Talk:",
            "en.wikipedia.org/wiki/File:",
            "en.wikipedia.org/wiki/Help:",
            "en.wikipedia.org/wiki/ISBN_(identifier)",
            "en.wikipedia.org/wiki/Doi_(identifier)"
        ]

    @staticmethod
    def check_url_is_wikipedia(url):
        """Checks if the URL is an English wikipedia page.
        I.e. if it includes en.wikipedia.org/wiki/
        Can change this in future to permit/refuse on different criteria.
        """
        if "en.wikipedia.org/wiki/" in url:
            return True
        else:
            return False

    def get_wiki_page_name(self, url):
        soup, title = self.load_soup(url)
        return soup.title.string

    @staticmethod
    def check_href_is_wikipedia(href):
        """Checks if the URL is an English wikipedia page.
        I.e. if it includes en.wikipedia.org/wiki/
        Can change this in future to permit/refuse on different criteria.
        """
        if "/wiki/" in href:
            return True
        else:
            return False

    @staticmethod
    def load_soup(url):
        page = requests.get(url)
        soup = bs(page.content, "html.parser")
        title = soup.title.string
        return soup, title

    def remove_all_wikipedia_motifs(self, text):
        for motif in self.known_motifs:
            text = text.replace(motif, "")
        return text

    def identify_links(self, tag):
        """Given a tag, returns appropriate wikipedia links, excluding those of identified types."""
        web_links = tag.select("a")
        wiki_urls = []
        for link in web_links:
            try:
                href = link["href"]
                if self.check_href_is_wikipedia(href):
                    url = "en.wikipedia.org" + href
                    if self.check_url_is_wikipedia(url):
                        remove = False
                        for unwanted in self.unwanted_link_formats:
                            if unwanted in url:
                                remove = True
                                break
                        if not remove:
                            wiki_urls.append("http://" + url)
            except KeyError:
                pass
        # TODO: Remove normal wikipedia pages.
        # Remove those pointing to files.

        # TODO: Remove those from references section.
        # From See also section, make so link from whole document (upon decomposition, is a special weak link between
        # whole article.


        # TODO: Remove redirections to same page

        return wiki_urls

    def strip_contents(self, soup):
        """
        Method to strip all the contents from the created soup.

        1. Iterates over all the tags in the soup.
          - Identifies if the tag is one which encloses others (e.g. if its h1 or h2, its likely to enclose other parts
        of the document. If so it updates the current scope.
          - Identifies if the tag is one which is at the bottom of the enclosing hierarchy i.e. p.
              i) Imbues the appropriate structural information to the json encoding;
              ii) Removes common wikipedia motifs from the text e.g. [edit]
              iii) Adds the tag contents to the appropriate structural position.

        """

        # To keep track of the current scope of the enclosed element.
        enclosing_element_name = ["None", "None", "None"]

        wiki_contents = {}
        wiki_links = {}

        for tag in soup.find_all():
            if tag.name in self.enclosing_elements:
                # If the tag is of a specific type, e.g. h1 or h2, its likely to contain other tags, so we preserve this
                #  structure by making a note of it.

                # Get the text in the element without any wikipedia motifs
                tag_text = self.remove_all_wikipedia_motifs(tag.text)

                # Index of the enclosing element e.g. h2 would be 1
                element_index = self.enclosing_elements.index(tag.name)
                # Set the corresponding element name to the tag_text
                enclosing_element_name[element_index] = tag_text
                # Get rid of the existing scope.
                new_enclosing_element_name = [name if i < element_index + 1 else "None"
                                              for i, name in enumerate(enclosing_element_name)]
                enclosing_element_name = new_enclosing_element_name

            elif tag.name in self.enclosed_elements:
                if enclosing_element_name[0] not in wiki_contents.keys():
                    wiki_contents[enclosing_element_name[0]] = {}
                    wiki_links[enclosing_element_name[0]] = {}
                if enclosing_element_name[1] not in wiki_contents[enclosing_element_name[0]].keys():
                    wiki_contents[enclosing_element_name[0]][enclosing_element_name[1]] = {}
                    wiki_links[enclosing_element_name[0]][enclosing_element_name[1]] = {}
                if enclosing_element_name[2] not in wiki_contents[enclosing_element_name[0]][enclosing_element_name[1]].keys():
                    wiki_contents[enclosing_element_name[0]][enclosing_element_name[1]][enclosing_element_name[2]] = []
                    wiki_links[enclosing_element_name[0]][enclosing_element_name[1]][enclosing_element_name[2]] = []

                tag_text = self.remove_all_wikipedia_motifs(tag.text)
                wiki_contents[enclosing_element_name[0]][enclosing_element_name[1]][enclosing_element_name[2]].append(tag_text)

                # Identify links at this point
                links = self.identify_links(tag)
                wiki_links[enclosing_element_name[0]][enclosing_element_name[1]][enclosing_element_name[2]].append(links)

        return wiki_contents, wiki_links

    @staticmethod
    def remove_empty_scopes(wiki_contents, wiki_links):
        for key_1 in wiki_contents.keys():
            for key_2 in wiki_contents[key_1].keys():
                for key_3 in wiki_contents[key_1][key_2].keys():
                    to_del = []
                    for i, p in enumerate(reversed(wiki_contents[key_1][key_2][key_3])):
                        if p == "":
                            to_del.append(i)
                    for i in reversed(to_del):
                        del wiki_contents[key_1][key_2][key_3][-1-i]

        # Do the same for links
        for key_1 in wiki_links.keys():
            for key_2 in wiki_links[key_1].keys():
                for key_3 in wiki_links[key_1][key_2].keys():
                    to_del = []
                    for i, p in enumerate(reversed(wiki_links[key_1][key_2][key_3])):
                        if p == "":
                            to_del.append(i)
                    for i in reversed(to_del):
                        del wiki_links[key_1][key_2][key_3][-1-i]

        return wiki_contents, wiki_links

    @staticmethod
    def save_json(document, links, title):
        with open(f"Data/Entities/{title}.json", "w") as file:
            as_json = json.dumps(document)
            file.write(as_json)
        with open(f"Data/Entities/{title}_links.json", "w") as file:
            as_json = json.dumps(links)
            file.write(as_json)

    def _create_wiki_json(self, url):
        soup, title = self.load_soup(url)
        document, links = self.strip_contents(soup)
        document, links = self.remove_empty_scopes(document, links)

        # Overwrite title to exclude wikipedia. Could be useful later though.
        title = list(document.keys())[0]
        return document, links, title

    def create_wiki_json_from_original_url(self):
        """Creates structural json document and links from the original URL provided."""
        document, links, title = self._create_wiki_json(url=self.starting_url)
        self.save_json(document, links, title)

    def build_from_document_links_list(self, links: list):
        """For interior parts of document links composed of lists"""
        links_names = []
        links_documents = []

        for l in links:
            if type(l) is list:
                new_names, new_documents = self.build_from_document_links_list(l)
                links_names.append(new_names)
                links_documents.append(new_documents)
            else:
                # Check link is a wikipedia link
                if self.check_url_is_wikipedia(l):
                    print(l)

                    doc, doc_links, doc_title = self._create_wiki_json(l)
                    links_documents.append(doc)
                    links_names.append(doc_title)
                else:
                    links_names.append("Invalid")
                    links_documents.append("Invalid")

        return links_names, links_documents

    def build_from_document_links(self, links: dict):

        # For creating names for each of the linked pages.
        links_names = {}

        # For compiling the documents within the list
        links_documents = {}

        for key in links.keys():
            sub_links = links[key]

            # Check if sub links are list
            if type(sub_links) is list:
                links_names[key], links_documents[key] = self.build_from_document_links_list(sub_links)

            else:
                links_documents[key], links_names[key] = self.build_from_document_links(sub_links)

        return links_documents, links_names

    def create_wiki_json_from_link_compliation(self, links):
        """
        Returns lists of all documents belonging to the links, and their respective links.

        Problems:
        - we want to keep a 1 to 1 mapping with all
        - we dont want to do the same document multiple times.
        :param links:
        :return:
        """
        # Get unique links and corresponding titles.
        compressed_links = links

        compressed_links = [compressed_links[key] for key in compressed_links.keys()]

        compressed_links_2 = {}
        for l in compressed_links:
            compressed_links_2 = {**compressed_links_2, **l}
        compressed_links = compressed_links_2

        compressed_links = [compressed_links[key] for key in compressed_links.keys()]

        compressed_links_2 = {}
        for l in compressed_links:
            compressed_links_2 = {**compressed_links_2, **l}
        compressed_links = compressed_links_2

        compressed_links = [compressed_links[key] for key in compressed_links.keys()]

        x = [a for ab in compressed_links for a in ab]
        x2 = [a for ab in x for a in ab]
        unique_links = np.unique(x2)

        # Get names

        # Create mapping between original list document and names

        # Get all link lists and documents for the given lists.
        x = True

    def _convert_nested_document_dict_to_unnested_list(self, nested_docs: dict, original_document_structure: dict, degree: int):
        compiled_documents = []
        if degree == 1:
            for key in original_document_structure.keys():
                for key_2 in original_document_structure[key].keys():
                    for key_3 in original_document_structure[key][key_2]:
                        contained_elements = nested_docs[key][key_2][key_3]
                        if type(contained_elements) is list:
                            compiled_documents += contained_elements
                        else:
                            print("Error: Function needs to be generalised")
        else:
            ...  # TODO: Case for larger degree: Then call recursively with degree-=1

        compiled_documents_flattened = [c for ci in compiled_documents for c in ci]
        return compiled_documents_flattened

    def create_wiki_json_from_article_links(self, degree: int):
        document, links, original_page_title = self._create_wiki_json(url=self.starting_url)

        # Compile all the links to be mined. Meanwhile, make a note of all the links between them.
        sub_documents, sub_names = self.build_from_document_links(links)

        # Flatten all the jsons to a list - the links can be found from the names in the sub_names
        all_wikis = self._convert_nested_document_dict_to_unnested_list(nested_docs=sub_documents,
                                                                        original_document_structure=sub_names,
                                                                        degree=degree)
        all_wikis.append(document)

        # Build a dictionary out of all the graph structures (removes repeats)
        wikis_dict = {}
        for wiki in all_wikis:
            key = list(wiki.keys())[0]
            wikis_dict[key] = wiki[key]

        self.save_json([wikis_dict], sub_names, f"{original_page_title}-{degree}")
        return original_page_title

        # self.create_wiki_json_from_link_compliation(links)   TODO: Work out if any of this is useful
        # Save all the wikis, then return a list of all the links between them.


if __name__ == "__main__":
    url1 = "https://en.wikipedia.org/wiki/Immanuel_Kant"
    url2 = "https://en.wikipedia.org/wiki/%C3%9Cbermensch"
    url3 = "https://en.wikipedia.org/wiki/Thus_Spoke_Zarathustra"
    url4 = "https://en.wikipedia.org/wiki/Human,_All_Too_Human"
    url5 = "https://en.wikipedia.org/wiki/Friedrich_Nietzsche"
    scraper = WikipediaScraper(url1)
    scraper.create_wiki_json_from_original_url()

    scraper = WikipediaScraper(url2)
    scraper.create_wiki_json_from_original_url()

    scraper = WikipediaScraper(url3)
    scraper.create_wiki_json_from_original_url()

    scraper = WikipediaScraper(url4)
    scraper.create_wiki_json_from_original_url()

    scraper = WikipediaScraper(url5)
    scraper.create_wiki_json_from_original_url()