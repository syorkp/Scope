"""
A scraper that extracts only URLs.
- Scape the page
- Handle authentication
- Isolate all things that look like URLs.
- Verify they are working URLs

Note difference between static and dynamic websites - some may need further probing
for the information to be available in the HTML. Also need to execute the JS that is recieved
by the requests library. There are libraries to do this.

Other scrapers:
- All non code text
- All images
- Preserve context e.g. headers, indentation

Using https://realpython.com/beautiful-soup-web-scraper-python/
"""

import requests
from bs4 import BeautifulSoup as bs
import json


def prettify_html(html):
    soup = bs(html)  # make BeautifulSoup
    prettyHTML = soup.prettify()  # prettify the html
    return prettyHTML


def get_soup(url):
    page = requests.get(url)
    soup = bs(page.content, "html.parser")
    return soup


def get_soup_authfull():
    payload = {
        'inUserName': 'username',
        'inUserPass': 'password'
    }

    with requests.Session() as s:
        p = s.post('LOGIN_URL', data=payload)
        # print the HTML returned or something more intelligent to see if it's a successful login page.
        print(p.text)

        # An authorised request.
        r = s.get('A protected web page URL')
        print(r.text)


def get_soup_auth(url, user, password):
    # Digest Authentication
    page = requests.get(url, auth=requests.auth.HTTPDigestAuth(user, password))
    # OAuth 1
    from requests_oauthlib import OAuth1
    auth = OAuth1('YOUR_APP_KEY', 'YOUR_APP_SECRET', 'USER_OAUTH_TOKEN', 'USER_OAUTH_TOKEN_SECRET')
    page = requests.get(url, auth=requests.auth.HTTPDigestAuth(user, password))

    soup = bs(page.content, "html.parser")
    return soup


def get_text_major_elements(soup):
    results = soup.find(id="ResultsContainer")
    job_elements = results.find_all("div", class_="card-content")
    for job_element in job_elements:
        title_element = job_element.find("h2", class_="title")
        company_element = job_element.find("h3", class_="company")
        location_element = job_element.find("p", class_="location")
        print(title_element.text.strip())
        print(company_element.text.strip())
        print(location_element.text.strip())  # Note that strip removes indentation.
        print()


def find_all_containing(soup, keyword):
    results = soup.find(id="ResultsContainer")

    python_jobs = results.find_all("h2", string=lambda text: keyword in text.lower())

    python_job_elements = [
        h2_element.parent.parent.parent for h2_element in python_jobs
    ]


def get_all_links(python_job_elements):
    for job_element in python_job_elements:
        # -- snip --
        links = job_element.find_all("a")
        for link in links:
            link_url = link["href"]
            print(f"Apply here: {link_url}\n")


def remove_all_html(url):
    soup = get_soup(url)

    for data in soup(['style', 'script']):
        data.decompose()

    text = soup.get_text()
    text = text.strip()


# Can extract all the text (no html). This preserves indentation.
# Can instead extract specific HTML elements by their ID.
# print(results.prettify())
# Find all HTML class names


url1 = "https://en.wikipedia.org/wiki/Friedrich_Nietzsche"
url2 = "https://en.wikipedia.org/wiki/Composer"
convert_wikipedia(url1)

