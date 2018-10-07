# -*- coding: utf-8 -*-
"""Module for working with Wikipedia text
"""

import re
import warnings
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring
from bokeh.embed import components
import wiki

assert wiki.__version__ >= 3
__version__ = 1


print("DO NOT USE THIS MODULE; JUST TO ILLUSTRATE TUTORIAL 18")


def print_hello():
    """Display a friendly greeting.
    """
    print("Hello!")


def clean_text(text):
    """Given a string, remove newlines and references.

    Args:
        text: A string object to clean.
    Results:
        A cleaned string object.
    """
    text = re.sub('\n', '', text)
    text = re.sub('\\[[0-9]+\\]', '', text)
    return text


def link_to_p(link):
    """Returns each paragraph in Wikipedia page as a string.

    Args:
        link: A string giving the link to a Wikipedia page.
    Results:
        A list of non-empty strings.
    """
    data = wiki.get_wiki_json(link)
    tree = ET.fromstring(data['text']['*'])

    output = []
    for child in tree.findall('.//p'):
        text = "".join(list(child.itertext()))
        text = clean_text(text)
        if text:
            output.append(text)

    return output


def link_to_doc(link):
    """Takes a Wikipedia page title and returns all of the text as a string.

    Args:
        link: A string giving the link to a Wikipedia page.
    Results:
        A string containing the entire (cleaned) page.
    """
    return " ".join(link_to_p(link))


def link_to_section(link):
    """Extract internal Wikipedia links by section.

    Args:
        link: A string giving the link to a Wikipedia page.
    Results:
        A list of dictionaries, one for each heading.
    """
    data = wiki.get_wiki_json(link)
    tree = ET.fromstring(data['text']['*'])

    output = []
    temp = []
    heading = "Header"
    for child in tree:
        if child.tag == "p":
            temp.append("".join(list(child.itertext())))
        elif child.tag == "h2":
            if temp:
                output.append(dict(heading=heading,
                                   text=clean_text("".join(temp))))
            temp = []
            heading = child.find('.//span[@class="mw-headline"]')
            if heading is not None:
                heading = heading.text
            else:
                heading = ""

    if temp:
        output.append(dict(heading=heading,
                           text=clean_text("".join(temp))))

    return output


def link_to_plinks(link):
    """Extract internal Wikipedia links from paragraphs.

    Args:
        link: A string giving the link to a Wikipedia page.
    Results:
        A list of unique internal links.
    """
    data = wiki.get_wiki_json(link)
    tree = ET.fromstring(data['text']['*'])

    output = []
    for child in tree:
        if child.tag == "p":
            for ilink in child.findall(".//a"):
                href = ilink.attrib['href']
                if href[:6] == "/wiki/":
                    output.append(href[6:])

    ilinks = [re.sub(' ', '_', x) for x in wiki.links_as_list(data)]
    output = list(set(output).intersection(ilinks))
    return sorted(output)


def link_to_lilinks(link):
    """Extract internal Wikipedia links from paragraphs.

    Args:
        link: A string giving the link to a Wikipedia page.
    Results:
        A list of unique internal links.
    """
    data = wiki.get_wiki_json(link)
    tree = ET.fromstring(data['text']['*'])

    output = []
    for ilink in tree.findall(".//li/a"):
        if 'href' in ilink.attrib:
            href = ilink.attrib['href']
            if href[:6] == "/wiki/":
                output.append(href[6:])

    ilinks = [re.sub(' ', '_', x) for x in wiki.links_as_list(data)]
    output = list(set(output).intersection(ilinks))
    return sorted(output)


def link_to_geo(link):
    """Extract geolocation information from a Wikipedia page.

    Args:
        link: A string giving the link to a Wikipedia page.
    Results:
        Either None, if no results found, or a tuple giving the
        (lat, lon) from the page's metadata.
    """
    data = wiki.get_wiki_json(link)
    tree = ET.fromstring(data['text']['*'])

    geo = tree.find(".//span[@class='geo']")
    if geo is None:
        return None

    result = re.split(';', geo.text)
    if len(result) == 2:
        try:
            lat = float(result[0])
            lon = float(result[1])
        except ValueError:
            return None

    return lat, lon


def links_to_bow(links):
    """Provide bag of words corpus and lexicon from list of links.

    Args:
        links: List of strings giving Wikipedia links.
    Returns:
        Tuple of bag of words corpus and the lexicon.
    """
    from gensim import corpora

    documents = []
    for link in links:
        documents.append(link_to_doc(link))

    word_list = []
    for doc in documents:
        word_list.append(re.findall('(\\w+)', doc.lower()))

    lexicon = corpora.Dictionary(word_list)
    lexicon.filter_extremes()

    corpus = []
    for doc in word_list:
        corpus.append(lexicon.doc2bow(doc))

    return corpus, lexicon


def corpus_to_top_terms(corpus, tfidf, lexicon, n_terms=5, score=False):
    """fun
    """
    top_terms = []
    for doc in corpus:
        these_terms = []
        tf_obj = tfidf[doc]
        for obj in sorted(tf_obj, key=lambda x: x[1], reverse=True)[:n_terms]:
            if score:
                val = "{0:s} ({1:01.03f})".format(lexicon[obj[0]], obj[1])
            else:
                val = "{0:s}".format(lexicon[obj[0]])
            these_terms.append(val)
        top_terms.append(these_terms)

    return top_terms

