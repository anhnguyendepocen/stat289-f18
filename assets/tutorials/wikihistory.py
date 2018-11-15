# -*- coding: utf-8 -*-
"""Module for working with Wikipedia text
"""

import re
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import SubElement
import wiki
import wikitext

__version__ = 1


###############################################################################
# Public classes and functions

def wiki_text_explore_page(wcorp, page_name="Default"):
    """Make pages for link.
    """

    for idx in range(wcorp.meta.shape[0]):
        _make_page(wcorp, idx, page_name=page_name)


def get_wikihistory_json(page_title, force=False):
    """Returns JSON data as a dictionary for the Wikipedia page.

    This function either loads a cached version of the page or,
    if a local version of the page is not available, calls the
    MediaWiki API directly.

    Args:
        page_title: A string containing the page title.

    Returns:
        A dictionary object with the complete parsed JSON data.
    """
    import os
    import json
    import gzip
    import time

    file_path = _wikihistory_json_path(page_title)
    if force or not os.path.exists(file_path):

        query = _wiki_page_revisions(page_title)
        parse = _get_page_history(query)
        page_history = dict(query=query, parse=parse)

        with gzip.open(file_path, 'wt', encoding='UTF-8') as fout:
            json.dump(page_history, fout)
        time.sleep(1)  # sleep for one second to avoid API limits

    with gzip.open(file_path, 'rt', encoding='UTF-8') as infile:
        page_history = json.load(infile)

    return page_history


def get_history_meta(page_link):
    """Return a pandas data frame of the page history.
    """
    import pandas as pd

    page_history = get_wikihistory_json(page_link)

    meta = dict(timestamp=[], pageid=[], revid=[], link=[], title=[], year=[],
                num_chars=[], num_p=[], num_sections=[], num_images=[],
                num_ilinks=[], num_elinks=[], num_langs=[], first_p=[],
                sections=[], section_anchors=[], doc=[])

    for rev, page_data in page_history['parse']:
        tree = ET.fromstring(page_data['text']['*'])
        meta['timestamp'].append(rev['timestamp'])
        meta['pageid'].append(page_data['pageid'])
        meta['revid'].append(rev['revid'])
        meta['link'].append(re.sub(' ', '_', page_data['title']))
        meta['title'].append(re.sub('<[^>]+>', '', page_data['displaytitle']))
        meta['year'].append(int(rev['timestamp'][:4]))
        meta['num_chars'].append(len(page_data['text']['*']))
        meta['num_p'].append(len(tree.findall(".//p")))
        meta['num_sections'].append(len(page_data['sections']))
        sec = ["{0:s}. {1:s}".format(x['number'], x['line']) for x in page_data['sections'] if x['toclevel'] == 1]
        asec = [x['anchor'] for x in page_data['sections'] if x['toclevel'] == 1]
        meta['sections'].append(sec)
        meta['section_anchors'].append(asec)
        meta['num_images'].append(len(page_data['images']))
        meta['num_ilinks'].append(len(page_data['links']))
        meta['num_elinks'].append(len(page_data['externallinks']))
        meta['num_langs'].append(len(page_data['langlinks']))
        next_doc, _ = wikitext.tree_to_doc(tree)
        meta['doc'].append(next_doc)

        first_p = None
        for child in tree.findall('.//p'):
            this_text = "".join(list(child.itertext()))
            if len(this_text) > 100:
                first_p = child
                for subchild in first_p.findall(".//a"):
                    subchild.attrib['href'] = "#"
                break
        meta['first_p'].append(first_p)

    pdf = pd.DataFrame(meta)
    return pdf


###############################################################################
# Private functions
#pylint: disable-msg=too-many-locals

def _wikihistory_json_path(page_title):
    """Returns local path to JSON file for Wikipedia page data.

    Args:
        page_title: A string containing the page title.

    Returns:
        A string describing a relative path to file.
    """
    import os
    page_title = re.sub("[ /]", "_", page_title)
    stat289_base_dir = os.path.dirname(os.getcwd())

    dir_name = os.path.join(stat289_base_dir, "data", "history")
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    file_name = page_title + ".json.gz"
    file_path = os.path.join(dir_name, file_name)

    return file_path


def _wiki_page_revisions(page_title):
    import requests
    base_api_url = 'https://' + 'en' + '.wikipedia.org/w/api.php?'

    page_json = wiki.get_wiki_json(page_title)
    pageid = page_json['pageid']
    revid = page_json['revid']

    api_query = base_api_url + \
        "action=query&" + "format=json&" + \
        "prop=revisions&" + "rvprop=ids|size|timestamp|comment|user&" \
        "rvlimit=max&" + \
        "pageids={0:d}&".format(pageid) + \
        "rvstartid={0:d}&".format(revid)
    req = requests.get(api_query)
    page_data = req.json()

    rev_data = page_data['query']['pages'][str(pageid)]['revisions']

    while 'continue' in page_data:
        rvcontinue = page_data['continue']['rvcontinue']
        api_query_continue = api_query + \
            "rvcontinue={0:s}&".format(rvcontinue)
        req = requests.get(api_query_continue)
        page_data = req.json()
        rev_data += page_data['query']['pages'][str(pageid)]['revisions']
        msg = "Loaded {0:d} revisions, through {1:s}"
        print(msg.format(len(rev_data), rev_data[-1]['timestamp']))

    return rev_data


def _get_page_history(rev_data):
    import requests

    base_api_url = 'https://' + 'en' + '.wikipedia.org/w/api.php?'
    page_history = []
    last_year = int(rev_data[0]['timestamp'][:4]) + 1

    for rev in rev_data:
        this_year = int(rev['timestamp'][:4])
        if this_year < last_year:
            last_year = this_year

            # grab the page
            revid = rev['revid']
            api_query = base_api_url + "action=parse&" + "format=json&" + \
                "oldid={0:d}&".format(revid)
            req = requests.get(api_query)
            page_data = req.json()['parse']

            page_history.append((rev, page_data))

            # output progress
            print("Grabbed page at {0:d}".format(revid))

    return page_history


def _top_words_doc(doc, wcorp):
    words = re.findall('(\\w+)', doc.lower())
    tf_obj = wcorp.tfidf[wcorp.lexicon.doc2bow(words)]

    output = []
    for obj in sorted(tf_obj, key=lambda x: x[1], reverse=True)[:15]:
        output.append((wcorp.lexicon[obj[0]], obj[1]))

    return output


def _write_xml_pages(xml_root, page_name, output_dir="text-explore"):
    """Write XML as HTML to a file.
    """
    import os
    from xml.dom import minidom
    from xml.etree.ElementTree import tostring

    output_pages_dir = os.path.join(output_dir, "pages")
    if not os.path.exists(output_pages_dir):
        os.makedirs(output_pages_dir)

    page = os.path.join(output_dir, 'pages', page_name + ".html")

    with open(page, 'wt', encoding='UTF-8') as fin:
        page = minidom.parseString(tostring(xml_root)).toprettyxml(indent=" ")
        fin.write("<!DOCTYPE html>\n")
        fin.write(page[23:])


def _make_page(wcorp, idx, page_name):
    xml_root, xml_body = wikitext.get_xml_page_head(page_name=page_name)

    pdf = get_history_meta(wcorp.meta.link[idx])
    page_name = wcorp.meta.link[idx]

    # First row; data about the page
    xml_row = SubElement(xml_body, 'div', {'class': 'row'})

    xml_img = SubElement(SubElement(xml_row, 'div', {'class': 'col-sm-4'}),
                         'img')
    xml_img.attrib['src'] = wcorp.meta.first_img[idx]
    xml_img.attrib['style'] = "max-width: 300px"

    xml_elem = SubElement(xml_row, 'div', {'class': 'col-sm-8'})
    xml_h1 = SubElement(xml_elem, 'h1')
    xml_h1.text = wcorp.meta.title[idx]
    xml_elem.append(wcorp.meta.first_p[idx])

    # Title for page revisions
    xml_h2 = SubElement(xml_body, 'h3', style='padding-top: 15px')
    xml_h2.text = "Page Revisions"

    # Produce information about the revisions
    xml_table = SubElement(xml_body, 'table',
                           style='text-align: left; margin: 0px auto')
    xml_tr = SubElement(xml_table, 'tr')
    for header in ['Year', 'Metadata', 'Sections', 'Top Words', 'First Paragraph']:
        xml_td = SubElement(SubElement(xml_tr, 'td'), 'b')
        xml_td.text = header

    for idy in range(pdf.shape[0]):
        xml_tr = SubElement(xml_table, 'tr')

        xml_td = SubElement(SubElement(xml_tr, 'td', style='width: 5%;'), 'a')
        ltxt = "https://en.wikipedia.org/w/index.php?title={0:s}&oldid={1:d}"
        xml_td.attrib['href'] = ltxt.format(pdf.link[idy], pdf.revid[idy])
        xml_td.attrib['target'] = '_blank'
        xml_td.text = str(pdf.timestamp[idy])[:4]
        
        xml_td = SubElement(xml_tr, 'td', style='width: 15%;')

        eli = SubElement(xml_td, 'p', style='padding: 0px; margin: 0px; ')
        eli.text = "{0:d} characters".format(pdf['num_chars'][idy])
        eli = SubElement(xml_td, 'p', style='padding: 0px; margin: 0px; ')
        eli.text = "{0:d} sections".format(pdf['num_sections'][idy])
        eli = SubElement(xml_td, 'p', style='padding: 0px; margin: 0px; ')
        eli.text = "{0:d} paragraphs".format(pdf['num_p'][idy])
        eli = SubElement(xml_td, 'p', style='padding: 0px; margin: 0px; ')
        eli.text = "{0:d} images".format(pdf['num_images'][idy])
        eli = SubElement(xml_td, 'p', style='padding: 0px; margin: 0px; ')
        eli.text = "{0:d} internal links".format(pdf['num_ilinks'][idy])
        eli = SubElement(xml_td, 'p', style='padding: 0px; margin: 0px; ')
        eli.text = "{0:d} external links".format(pdf['num_elinks'][idy])

        xml_td = SubElement(xml_tr, 'td', style='width: 25%;')
        for section, anchor in zip(pdf['sections'][idy], pdf['section_anchors'][idy]):
            elem = SubElement(SubElement(xml_td, 'p', style='padding: 0px; margin: 0px; '), 'a')
            elem.text = section
            elem.attrib['href'] = (ltxt + "#{2:s}").format(pdf.link[idy], pdf.revid[idy], anchor)
            elem.attrib['target'] = '_blank'
        
        xml_td = SubElement(xml_tr, 'td', style='width: 15%;')
        msim = _top_words_doc(pdf.doc[idy], wcorp)
        for title, val in msim:
            elem = SubElement(xml_td, 'p', style='padding: 0px; margin: 0px; ')
            elem.text = title
            elem = SubElement(elem, 'span')
            elem.attrib['style'] = 'color: #bababa; font-size: 12px'
            elem.text = "{0:.03f}".format(val)

        xml_td = SubElement(xml_tr, 'td', style='width: 40%;')
        if pdf.first_p[idy] is not None:
            xml_td.append(pdf.first_p[idy])

    _write_xml_pages(xml_root, page_name)


def _make_custom_css(output_dir):
    """Output custom CSS file for webpage.
    """
    import os

    ctext = "html{min-height:100%;position:relative}body{margin-top:50px;z-" \
            "index:0}@media (min-width: 992px){body{margin-bottom:113px}}.s" \
            "ection{}.hidden{display:none}a{text-decoration:none;color:blac" \
            "k}a:hover{color:black;text-decoration:underline}a:visited{colo" \
            "r:black}a:active{color:black;text-decoration:underline}a.exter" \
            "nal{color:#3C88A8}a.external:visited{color:#A63E85}table a{dis" \
            "play:inline}table{border-collapse:collapse;position:relative}t" \
            "d,th{vertical-align:top;border-bottom:2px solid black;padding:" \
            "10px;text-align:left}td.weight{min-width:1em}td.weight div.pro" \
            "portion{background-color:#69adc9;text-align:right}td.weight di" \
            "v.proportion span.proportion{color:rgba(0,0,0,0)}th.th-right{t" \
            "ext-align:right}th.wide{min-width:20em}td.td-right{text-align:" \
            "right}"

    if not os.path.exists(os.path.join(output_dir, "css")):
        os.makedirs(os.path.join(output_dir, "css"))

    fname = os.path.join(output_dir, "css", "custom.css")
    with open(fname, 'w', encoding='UTF-8') as fin:
        fin.write(ctext)
