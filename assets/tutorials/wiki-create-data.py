import gzip
import json
import os
import shutil
import re
import wiki
import wikitext

assert wiki.__version__ >= 6

def create_zip_file(links, name):
    """Downloads a set of links from Wikipedia and saves as zip file
    """
    links = list(set(links))  # make sure list is unique
    if not os.path.exists(name):
        os.mkdir(name)
    for page_title in links:
        try:
            page_data = wiki.download_wiki_json(page_title)
            file_path = wiki.wiki_json_path(page_title)
            file_path = os.path.split(file_path)[1]
            file_path = os.path.join(name, file_path)
            with gzip.open(file_path, 'wt') as outfile:
                json.dump(page_data, outfile)
        except:
            pass
    shutil.make_archive(name, 'zip', name)


# birthday cake
data_json = wiki.download_wiki_json("Birthday_cake")
rr_links = wiki.links_as_list(data_json)
create_zip_file(rr_links, 'birthday-cake')

# richmond, va
data_json = wiki.download_wiki_json("Richmond,_Virginia")
rr_links = wiki.links_as_list(data_json)
create_zip_file(rr_links, 'richmond-va')

# philosophy
links_us = wikitext.get_internal_links('List_of_important_publications_in_philosophy')
create_zip_file(links_us['ilinks'], 'philosophy')

# impressionists
page_links = wikitext.get_internal_links("Impressionism")['ilinks'] + ["Impressionism"]
create_zip_file(page_links, 'impressionists-text')

# novelists and poets
data = wiki.get_wiki_json("List_of_American_novelists")
data_html = data['text']['*']
authors = re.findall('<li><a href="/wiki/([^"]+)"', data_html)
nov_authors = authors[:(authors.index('Leane_Zugsmith') + 1)]

data = wiki.get_wiki_json("List_of_poets_from_the_United_States")
data_html = data['text']['*']
authors = re.findall('<li><a href="/wiki/([^"]+)"', data_html)
poe_authors = authors[:(authors.index('Louis_Zukofsky') + 1)]

create_zip_file(nov_authors + poe_authors, "novel-poem")
