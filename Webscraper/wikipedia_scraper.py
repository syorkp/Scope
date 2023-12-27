import requests
from bs4 import BeautifulSoup as bs
import json


class WikipediaScraper:

    def __init__(self, url):
        self.url = url
        self.soup = None
        self.title = None

        self.wiki_contents = {}

        self.known_motifs = ["[edit]", "\n"] + \
                            [f"[{num}]" for num in range(500)]

        self.enclosing_elements = ["h1", "h2", "h3"]
        self.enclosing_element_name = ["None", "None", "None"]

        self.enclosed_elements = ["p"]

    def load_soup(self):
        page = requests.get(self.url)
        self.soup = bs(page.content, "html.parser")

        self.title = self.soup.title.string

    def remove_all_wikipedia_motifs(self, text):
        for motif in self.known_motifs:
            text = text.replace(motif, "")
        return text

    def strip_contents(self):
        for tag in self.soup.find_all():
            if tag.name in self.enclosing_elements:
                # Get the text in the element without any wikipedia motifs
                tag_text = self.remove_all_wikipedia_motifs(tag.text)

                # Index of the enclosing element e.g. h2 would be 1
                element_index = self.enclosing_elements.index(tag.name)
                # Set the corresponding element name to the tag_text
                self.enclosing_element_name[element_index] = tag_text
                # Get rid of the existing scope.
                new_enclosing_element_name = [name if i < element_index + 1 else "None"
                                              for i, name in enumerate(self.enclosing_element_name)]
                self.enclosing_element_name = new_enclosing_element_name

            elif tag.name in self.enclosed_elements:
                if self.enclosing_element_name[0] not in self.wiki_contents.keys():
                    self.wiki_contents[self.enclosing_element_name[0]] = {}
                if self.enclosing_element_name[1] not in self.wiki_contents[self.enclosing_element_name[0]].keys():
                    self.wiki_contents[self.enclosing_element_name[0]][self.enclosing_element_name[1]] = {}
                if self.enclosing_element_name[2] not in self.wiki_contents[self.enclosing_element_name[0]][self.enclosing_element_name[1]].keys():
                    self.wiki_contents[self.enclosing_element_name[0]][self.enclosing_element_name[1]][self.enclosing_element_name[2]] = []

                tag_text = self.remove_all_wikipedia_motifs(tag.text)

                self.wiki_contents[self.enclosing_element_name[0]][self.enclosing_element_name[1]][self.enclosing_element_name[2]].append(tag_text)

    def remove_empty_scopes(self):
        for key_1 in self.wiki_contents.keys():
            for key_2 in self.wiki_contents[key_1].keys():
                for key_3 in self.wiki_contents[key_1][key_2].keys():
                    for i, p in enumerate(reversed(self.wiki_contents[key_1][key_2][key_3])):
                        if p == "":
                            del self.wiki_contents[key_1][key_2][key_3][-1-i]

    def save_json(self):
        with open(f"../Data/{self.title}.json", "w") as file:
            as_json = json.dumps(self.wiki_contents)
            file.write(as_json)

    def create_wiki_json(self):
        self.load_soup()
        self.strip_contents()
        self.remove_empty_scopes()
        self.save_json()


if __name__ == "__main__":
    url1 = "https://en.wikipedia.org/wiki/Immanuel_Kant"
    url2 = "https://en.wikipedia.org/wiki/%C3%9Cbermensch"
    url3 = "https://en.wikipedia.org/wiki/Thus_Spoke_Zarathustra"
    url4 = "https://en.wikipedia.org/wiki/Human,_All_Too_Human"
    url5 = "https://en.wikipedia.org/wiki/Friedrich_Nietzsche"
    scraper = WikipediaScraper(url1)
    scraper.create_wiki_json()

    scraper = WikipediaScraper(url2)
    scraper.create_wiki_json()

    scraper = WikipediaScraper(url3)
    scraper.create_wiki_json()

    scraper = WikipediaScraper(url4)
    scraper.create_wiki_json()

    scraper = WikipediaScraper(url5)
    scraper.create_wiki_json()