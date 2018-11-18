# -*- coding: utf-8 -*-
"""Module for working with Wikipedia text
"""

import re
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement

__version__ = 3


###############################################################################
# Public classes and functions

class WikiCorpus():
    """Class to describe a collection of Wikipedia pages.

    Args:
        links: A list of strings describing Wikipedia pages.
        stopwords: Logical. Should stopwords be removed from the text?
        num_clusters: Number of clusters to include in the output.
        **kwargs: Additional parameters, including:
            n_below: minimum number of times a word must occur to be in the
                     lexicon. Default is 5.
            n_above: maximum percentage of documents a word may occur in to
                     be included in the lexicon. Default is 0.7.
            iterations: number of iterations to perform in LDA. Default is 200.
    """
    def __init__(self, links, stopwords=True, num_clusters=4,
                 **kwargs):
        from gensim.models import TfidfModel
        from gensim.similarities.docsim import MatrixSimilarity

        if 'iterations' not in kwargs:
            kwargs['iterations'] = 200

        self.meta = _compute_meta_dataframe(links)
        self.lexicon, self.bow = _compute_lex_bow(self.meta,
                                                  stopwords=stopwords)
        self.tfidf = TfidfModel(self.bow)
        self.matsim = MatrixSimilarity(self.bow,
                                       num_features=len(self.lexicon))
        self.clust = _compute_spectral_clust(self.similarity_matrix(),
                                             num_clusters=num_clusters)

    def __str__(self):
        msg = "WikiCorpus object with '{0:d}' documents and lexicon with" \
              " '{1:d}' terms."
        return msg.format(self.meta.shape[0], len(self.lexicon))

    def dense_tf(self):
        """Get a dense term frequency matrix.
        """
        from gensim.models import matutils
        return matutils.corpus2dense(self.bow, num_terms=self.lexicon.num_pos)

    def sparse_tf(self):
        """Get a sparse (CSC) term frequency matrix.
        """
        from gensim.models import matutils
        return matutils.corpus2csc(self.bow)

    def top_terms(self, docx, n_terms=10):
        """List of top terms for a document.

        Args:
            docx: Numeric id of the document.
            n_terms: Number of terms to include. Default is 10.

        Returns:
            A list of terms.
        """
        tf_obj = self.tfidf[self.bow[docx]]
        output = []
        for obj in sorted(tf_obj, key=lambda x: x[1], reverse=True)[:n_terms]:
            output.append((self.lexicon[obj[0]], obj[1]))
        return output

    def most_similar(self, docx):
        """Get vector of most similar documents.

        Args:
            docx: Numeric id of the document.
            n_terms: Number of terms to include. Default is 10.

        Returns:
            Numpy array of document similarities.
        """
        return self.matsim[self.tfidf[self.bow[docx]]]

    def similarity_matrix(self):
        """Get similarity matrix.
        """
        return self.matsim[[self.tfidf[x] for x in self.bow]]

    def json_meta_template(self):
        """Dictionary of cluster names.
        """
        json = dict(clust_names=["Cluster {0:d}".format(x) for x in
                                 range(max(self.clust) + 1)])
        return json


def wiki_text_explorer(wcorp, input_file=None, output_dir="text-explore",
                       page_name="Default"):
    """Produce visualization webpage.

    Args:
        input_file: Optional path to a json file that describes cluster names.
        output_dir: Directory name of where to build the explorer.
    """
    from xml.dom import minidom
    from xml.etree.ElementTree import tostring
    import json
    import os

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if input_file is None:
        name_dict = wcorp.json_meta_template()
    else:
        with open(input_file, 'r', encoding='UTF-8') as fin:
            name_dict = json.load(fin)

    _make_custom_css(output_dir)
    clust_names = name_dict['clust_names']

    with open(os.path.join(output_dir, 'docs.html'), 'w',
              encoding="UTF-8") as fin:
        xml_page = _get_doc_page(wcorp, clust_names, page_name)
        page = minidom.parseString(tostring(xml_page)).toprettyxml(indent=" ")
        fin.write("<!DOCTYPE html>\n")
        fin.write(page[23:])

    index_page = os.path.join(output_dir, 'index.html')
    if not os.path.exists(index_page):
        with open(index_page, 'w', encoding="UTF-8") as fin:
            xml_page = _get_index_page(page_name)
            page = minidom.parseString(tostring(xml_page))
            page = page.toprettyxml(indent=" ")
            fin.write("<!DOCTYPE html>\n")
            fin.write(page[23:])

    with open(os.path.join(output_dir, 'clusters.html'), 'w',
              encoding="UTF-8") as fin:
        xml_page = _get_cluster_page(wcorp, clust_names, page_name)
        page = minidom.parseString(tostring(xml_page)).toprettyxml(indent=" ")
        fin.write("<!DOCTYPE html>\n")
        fin.write(page[23:])

    with open(os.path.join(output_dir, 'viz.html'), 'w',
              encoding="UTF-8") as fin:
        xml_page = _get_viz_page(wcorp, output_dir, page_name)
        page = minidom.parseString(tostring(xml_page)).toprettyxml(indent=" ")
        fin.write("<!DOCTYPE html>\n")
        fin.write(page[23:])


def get_internal_links(data):
    """Extract internal Wikipedia links.

    Args:
        data: Either a string describing the name of a Wikipedia page or a
              dictionary object already pulled with `wiki.get_wiki_json`.
    Returns:
        A dictionary with three elements: 'ilinks' (all of the internal links
        for the page), 'ilinks_p' (links from the page found inside paragraph
        tags), and 'ilinks_li' (links found inside list items). All links are
        checked to make sure they actually exist.
    """
    from wiki import get_wiki_json

    if isinstance(data, str):
        data = get_wiki_json(data)

    ilinks = [x['*'] for x in data['links'] if x['ns'] == 0 and 'exists' in x]
    ilinks = [re.sub(' ', '_', x) for x in ilinks]
    tree = ET.fromstring(data['text']['*'])

    output_p = []
    for child in tree:
        if child.tag == "p":
            for ilink in child.findall(".//a"):
                href = ilink.attrib['href']
                if href[:6] == "/wiki/":
                    output_p.append(href[6:])

    output_li = []
    for ilink in tree.findall(".//li/a"):
        if 'href' in ilink.attrib:
            href = ilink.attrib['href']
            if href[:6] == "/wiki/":
                output_li.append(href[6:])

    output_p = sorted(list(set(output_p).intersection(ilinks)))
    output_li = sorted(list(set(output_li).intersection(ilinks)))

    return dict(ilinks=ilinks, ilinks_p=output_p, ilinks_li=output_li)


def get_xml_page_head(page_name):
    """Return XML to add content to.
    """
    xml_root = Element("html", lang="en")

    xml_head = SubElement(xml_root, "head")
    SubElement(xml_head, "meta", charset="utf-8")
    SubElement(xml_head, "title", charset="utf-8")
    xml_head[-1].text = page_name
    elem = SubElement(xml_head, "script", type="text/javascript",
                      src="https://stackpath.bootstrapcdn.com/bootstrap/"
                          "3.3.7/js/bootstrap.min.js")
    elem.text = " "
    SubElement(xml_head, "link", rel="stylesheet",
               href="https://stackpath.bootstrapcdn.com/bootstrap/"
                    "3.3.7/css/bootstrap.min.css",
               media="screen")
    SubElement(xml_head, "link", rel="stylesheet",
               href="../css/custom.css", type="text/css")

    xml_nav = SubElement(SubElement(xml_root, "body"), "nav")
    xml_nav.attrib['class'] = "navbar navbar-default navbar-dark" \
                              "bg-dark navbar-fixed-top"
    SubElement(SubElement(SubElement(xml_nav, "div", {'class': 'container'}),
                          'div', {'class': 'navbar-header'}),
               'a', {'class': 'navbar-brand', 'href': "../index.html"})
    xml_nav[-1][0][0].text = page_name

    elem = SubElement(xml_nav[0], "div",
                      {'id': "navbar", 'class': "navbar-collapse collapse"})

    pages = [('docs', 'Docs'), ('clusters', 'Clusters'),
             ('viz', 'Viz')]
    for page in pages:
        ielem = SubElement(elem, "ul", {'class': "nav navbar-nav"})
        ielem = SubElement(SubElement(ielem, 'li', {'class': "nav-item",
                                                    'id': 'tag-' + page[0]}),
                           'a', {'class': "nav-link",
                                 'href': '../' + page[0] + ".html"})
        ielem.text = page[1]

    body = xml_root.find(".//body")
    container = SubElement(body, 'div', {'class': 'container',
                                         'style': 'padding-top: 30px;'})
    return xml_root, container


def tree_to_doc(tree):
    """Extract paragraph text from an ElementTree.
    """
    output = []
    first_p = None
    for child in tree.findall('.//p'):
        text = "".join(list(child.itertext()))
        text = _clean_text(text)
        if text:
            output.append(text)
            if first_p is None:
                first_p = child
                for subchild in first_p.findall(".//a"):
                    subchild.attrib['href'] = "#"

    return " ".join(output), first_p


###############################################################################
# Private functions
#pylint: disable-msg=too-many-locals

def _compute_meta_dataframe(links):
    """Convert links to a pandas DataFrame object
    """
    import pandas as pd
    from wiki import get_wiki_json

    meta = dict(link=[], title=[], doc=[], first_p=[], num_sections=[],
                num_images=[], num_ilinks=[], num_elinks=[],
                num_langs=[], langs=[], ilinks=[], first_img=[])
    for link in links:
        data = get_wiki_json(link)
        tree = ET.fromstring(data['text']['*'])

        meta['link'].append(re.sub(' ', '_', data['title']))
        meta['title'].append(re.sub('<[^>]+>', '', data['displaytitle']))
        next_doc, next_first_p = tree_to_doc(tree)
        meta['doc'].append(next_doc)
        meta['first_p'].append(next_first_p)
        meta['num_sections'].append(len(data['sections']))
        meta['num_images'].append(len(data['images']))
        meta['num_ilinks'].append(len(data['links']))
        meta['num_elinks'].append(len(data['externallinks']))
        meta['num_langs'].append(len(data['langlinks']))
        meta['langs'].append([(x['lang'], x['url']) for x in
                              data['langlinks']])
        meta['ilinks'].append([re.sub(' ', '_', x['*']) for x in
                               data['links'] if x['ns'] == 0])
        lat, lon = _tree_to_geo(tree)
        meta['lat'] = lat
        meta['lon'] = lon

        # add first image to the dataset
        first_img = ''
        for item in tree.findall('.//img'):
            if int(item.attrib.get('width', 0)) >= 150:
                first_img = 'https:' + item.attrib['src']
                break

        meta['first_img'].append(first_img)

    meta['eigen'] = _compute_centrality(links, meta)

    pdf = pd.DataFrame(meta)
    return pdf.reset_index()


def _compute_centrality(internal_links, meta):
    """Given the metadata dictionary, compute eigenvalue centrality scores.

    Args:
        internal_links: A list of links.
        meta: A dictionary of metadata.
    Results:
        A list of eigenvalue scores.
    """
    import networkx as nx

    gobj = nx.Graph()

    for start in internal_links:
        gobj.add_node(start)

    for start, links in zip(internal_links, meta['ilinks']):
        for new_link in links:
            if new_link in internal_links:
                gobj.add_edge(start, new_link)

    return list(nx.eigenvector_centrality_numpy(gobj).values())


def _clean_text(text):
    """Given a string, remove newlines and references.

    Args:
        text: A string object to clean.
    Results:
        A cleaned string object.
    """
    text = re.sub('\n', '', text)
    text = re.sub('\\[[0-9]+\\]', '', text)
    return text


def _tree_to_geo(tree):
    """Get latitude and longitude from an ElementTree.
    """
    geo = tree.find(".//span[@class='geo']")
    if geo is None:
        return None, None

    result = re.split(';', geo.text)
    if len(result) == 2:
        try:
            lat = float(result[0])
            lon = float(result[1])
        except ValueError:
            return None, None

    return lat, lon


def _compute_lex_bow(meta, stopwords):
    """Produce the full lexicon object.
    """
    from gensim import corpora

    word_list = []
    for doc in meta['doc']:
        word_list.append(re.findall('(\\w+)', doc.lower()))

    lexicon = corpora.Dictionary(word_list)
    lexicon = _reduce_lex(lexicon, stopwords=stopwords)

    bow = []
    for word in word_list:
        bow.append(lexicon.doc2bow(word))

    return lexicon, bow


def _reduce_lex(lexicon, stopwords):
    if stopwords:
        with open('ranksnl_large.txt', 'r', encoding='UTF-8') as fin:
            sw_list = fin.read().splitlines()
        sw_list = set(sw_list).intersection(lexicon.token2id.keys())
        ids = [lexicon.token2id[x] for x in sw_list]
        lexicon.filter_tokens(ids)

    lexicon.compactify()

    return lexicon


def _compute_spectral_clust(similarity_matrix, num_clusters):
    from warnings import simplefilter
    from sklearn.cluster import SpectralClustering

    simplefilter("ignore", UserWarning)     # ignore disconnected warning
    scmodel = SpectralClustering(n_clusters=num_clusters,
                                 affinity='precomputed',
                                 random_state=17)

    return scmodel.fit_predict(similarity_matrix)


def _get_xml_head(headings, name=None, page_name="Default"):
    xml_root = Element("html", lang="en")

    xml_head = SubElement(xml_root, "head")
    SubElement(xml_head, "meta", charset="utf-8")
    SubElement(xml_head, "title", charset="utf-8")
    xml_head[-1].text = page_name
    elem = SubElement(xml_head, "script", type="text/javascript",
                      src="https://stackpath.bootstrapcdn.com/bootstrap/"
                          "3.3.7/js/bootstrap.min.js")
    elem.text = " "
    SubElement(xml_head, "link", rel="stylesheet",
               href="https://stackpath.bootstrapcdn.com/bootstrap/"
                    "3.3.7/css/bootstrap.min.css",
               media="screen")
    SubElement(xml_head, "link", rel="stylesheet",
               href="css/custom.css", type="text/css")

    xml_nav = SubElement(SubElement(xml_root, "body"), "nav")
    xml_nav.attrib['class'] = "navbar navbar-default navbar-dark" \
                              "bg-dark navbar-fixed-top"
    SubElement(SubElement(SubElement(xml_nav, "div", {'class': 'container'}),
                          'div', {'class': 'navbar-header'}),
               'a', {'class': 'navbar-brand', 'href': "index.html"})
    xml_nav[-1][0][0].text = page_name

    elem = SubElement(xml_nav[0], "div",
                      {'id': "navbar", 'class': "navbar-collapse collapse"})

    pages = [('docs', 'Docs'), ('clusters', 'Clusters'),
             ('viz', 'Viz')]
    for page in pages:
        ielem = SubElement(elem, "ul", {'class': "nav navbar-nav"})
        ielem = SubElement(SubElement(ielem, 'li', {'class': "nav-item",
                                                    'id': 'tag-' + page[0]}),
                           'a', {'class': "nav-link",
                                 'href': page[0] + ".html"})
        ielem.text = page[1]

    if name is not None:
        elem = xml_root.find(".//li[@id='tag-{0:s}']".format(name))
        elem.attrib['class'] = "nav-item active"

    tab = SubElement(SubElement(xml_root.find(".//body"), 'div',
                                style='padding: 25px;'),
                     'table', style="text-align: left; margin: 0px auto; "
                                    "padding-top: 50px")

    xml_tr = SubElement(tab, 'tr')
    for heading in headings:
        elem = SubElement(SubElement(xml_tr, 'td'), 'b')
        elem.text = heading

    return xml_root, tab


def _get_doc_page(wcorp, clust_names, page_name):
    import os
    xml_root, tab = _get_xml_head(headings=['', 'Page', 'Top Words', 'TF-IDF'],
                                  name='docs', page_name=page_name)

    for idx in range(wcorp.meta.shape[0]):
        xml_tr = SubElement(tab, 'tr', id='sec{0:d}'.format(idx))

        xml_td = SubElement(xml_tr, 'td')
        if wcorp.meta.first_img[idx]:
            page_name = wcorp.meta['link'][idx] + ".html"
            xml_a = SubElement(xml_td, 'a', href=os.path.join('pages',
                                                              page_name))
            SubElement(xml_a, 'img', src=wcorp.meta.first_img[idx],
                       style="max-width: 150px; border:1px solid black")

        xml_td = SubElement(xml_tr, 'td')
        elem = SubElement(SubElement(SubElement(xml_td, 'p'), 'b'), 'a')
        elem.attrib['href'] = os.path.join('pages',
                                           wcorp.meta['link'][idx] + ".html")
        elem.text = wcorp.meta['title'][idx]

        elem = SubElement(xml_td, 'ul')
        elem.attrib['style'] = 'list-style-type: none;'
        _make_doc_meta_table(wcorp, elem, idx, clust_names)

        msim = wcorp.top_terms(idx)
        xml_ul = SubElement(SubElement(xml_tr, 'td'), 'ul',
                            style='list-style-type: none;')
        for title, val in msim:
            elem = SubElement(xml_ul, 'li')
            elem.text = title
            elem = SubElement(elem, 'span')
            elem.attrib['style'] = 'color: #bababa; font-size: 12px'
            elem.text = "{0:.03f}".format(val)

        msim = wcorp.most_similar(idx)
        msim = sorted(zip(wcorp.meta['title'], msim, range(len(msim))),
                      key=lambda x: x[1], reverse=True)[:11]
        msim = [x for x in msim if x[0] is not wcorp.meta['title'][idx]]
        xml_ul = SubElement(SubElement(xml_tr, 'td'), 'ul',
                            style='list-style-type: none;')
        for title, val, idy in msim:
            elem = SubElement(xml_ul, 'li')
            SubElement(elem, 'a', href='#sec{0:d}'.format(idy - 1))
            elem.find('.//a').text = title
            elem = SubElement(elem, 'span')
            elem.attrib['style'] = 'color: #bababa; font-size: 12px'
            elem.text = "{0:.03f}".format(val)

    return xml_root


def _make_doc_meta_table(wcorp, elem, idx, clust_names):
    eli = SubElement(elem, 'li')
    eli.text = "centrality: {0:05.05f}".format(wcorp.meta['eigen'][idx])
    eli = SubElement(elem, 'li')
    eli.text = "{0:d} words".format(len(wcorp.bow[idx]))
    eli = SubElement(elem, 'li')
    eli.text = "{0:d} sections".format(wcorp.meta['num_sections'][idx])
    eli = SubElement(elem, 'li')
    eli.text = "{0:d} images".format(wcorp.meta['num_images'][idx])
    eli = SubElement(elem, 'li')
    eli.text = "{0:d} internal links".format(wcorp.meta['num_ilinks'][idx])
    eli = SubElement(elem, 'li')
    eli.text = "{0:d} external links".format(wcorp.meta['num_elinks'][idx])
    eli = SubElement(elem, 'li')
    eli.text = "{0:d} languages".format(wcorp.meta['num_langs'][idx])

    _add_country_flags(wcorp, idx, SubElement(elem, 'li'))

    eli = SubElement(elem, 'li')
    eli.attrib['style'] = 'padding-top: 18px'
    eli = SubElement(eli, 'a')
    eli.text = clust_names[wcorp.clust[idx]]
    eli.attrib['href'] = "clusters.html#sec{0:d}".format(wcorp.clust[idx])


def _add_country_flags(wcorp, idx, eli):

    # manually add English
    url = "https://en.wikipedia.org/wiki/{0:s}".format(wcorp.meta.link[idx])
    elink = SubElement(eli, 'a', href=url)
    elink.text = "[{0:s}]".format('en')
    elink.attrib['target'] = "_blank"

    langs = wcorp.meta.langs[idx]
    for langname, url in langs:
        if langname in ['de', 'fr', 'es', 'ru', 'ar', 'zh', 'ko']:
            elink = SubElement(eli, 'a', href=url)
            elink.text = "[{0:s}]".format(langname)
            elink.attrib['target'] = "_blank"


def _get_cluster_page(wcorp, clust_names, page_name):
    xml_root, tab = _get_xml_head(headings=['Cluster', 'Pages'],
                                  name='clusters', page_name=page_name)

    cluster2idx = {d: [] for d in range(max(wcorp.clust) + 1)}
    for idx, cid in zip(range(len(wcorp.clust)), wcorp.clust):
        cluster2idx[cid].append(idx)

    for cluster, idxs in cluster2idx.items():

        xml_tr = SubElement(tab, 'tr', id='sec{0:d}'.format(cluster))
        elem = SubElement(SubElement(SubElement(xml_tr, 'td'), 'p'), 'b')
        elem.text = clust_names[cluster]

        xml_ul = SubElement(SubElement(xml_tr, 'td'), 'ul')
        xml_ul.attrib['style'] = 'list-style-type: none;'
        for idx in idxs:
            elem = SubElement(SubElement(xml_ul, 'li'), 'a',
                              href='docs.html#sec{0:d}'.format(idx - 1))
            elem.text = wcorp.meta['title'][idx]

    return xml_root


def _get_viz_page(wcorp, output_dir, page_name):
    """Create interactive plot page.
    """
    from bokeh.embed import components
    import iplot
    import os

    pdata = wcorp.meta[['num_ilinks', 'num_langs', 'title']].copy(deep=True)
    pdata['dlink'] = ["docs.html#sec{0:d}".format(x - 1) for x in
                      range(wcorp.meta.shape[0])]
    pdata['Length'] = [len(x) for x in wcorp.meta.doc.values]

    plt = iplot.create_figure(pdata, 'num_ilinks', 'num_langs',
                              url='dlink', title='', color='Length',
                              x_axis_label='Number of internal links',
                              y_axis_label='Number of language pages',
                              url_raw=True)
    script, div = components(plt, wrap_script=False)

    if not os.path.exists(os.path.join(output_dir, "js")):
        os.makedirs(os.path.join(output_dir, "js"))

    fname = os.path.join(output_dir, "js", "plot.js")
    with open(fname, 'w', encoding='UTF-8') as fin:
        fin.write(script)

    xml_root, _ = _get_xml_head(headings=[], name='viz', page_name=page_name)
    xml_body = xml_root.find(".//body")
    xml_body.remove(xml_body[-1])

    xml_div = SubElement(xml_body, 'div',
                         style="padding: 25px; padding-left: 75px;")
    elem = ET.fromstring(div)
    elem.text = " "
    xml_div.append(elem)

    xml_footer = SubElement(xml_body, 'footer')

    elem = SubElement(xml_footer, 'script',
                      src="https://cdn.pydata.org/bokeh/release/"
                          "bokeh-0.13.0.min.js",
                      type="text/javascript")
    elem.text = " "
    elem = SubElement(xml_footer, 'script',
                      src="js/plot.js",
                      type="text/javascript")
    elem.text = " "
    elem = SubElement(xml_footer, 'link',
                      href="https://cdn.pydata.org/bokeh/release/"
                           "bokeh-0.13.0.min.css",
                      rel="stylesheet", type="text/css")

    return xml_root


def _get_index_page(page_name):
    """Create index page.
    """
    xml_root, _ = _get_xml_head(headings=[], page_name=page_name)
    xml_body = xml_root.find(".//body")
    xml_body.remove(xml_body[-1])

    elem = SubElement(xml_body, 'div', {'class': "container",
                                        'style': "padding-top: 30px;"})
    elem = SubElement(elem, 'div', {'class': "row"})
    elem_c4 = SubElement(elem, 'div', {'class': "col-lg-4"})
    SubElement(elem_c4, 'img', src="https://upload.wikimedia.org/wikipedia/"
                                   "commons/8/88/Plato_Silanion_Musei_Capito"
                                   "lini_MC1377.jpg",
               style="max-width: 300px")

    elem = SubElement(elem, 'div', {'class': "col-lg-8",
                                    'style': "font-size: 16px; max-width:"
                                             "600px"})
    elem_i = SubElement(elem, 'h1')
    elem_i.text = "Text Explorer"
    elem_i = SubElement(elem, 'p')
    elem_i.text = "Here is some explanation of what we are doing. Here is" \
                  "explanation of what we are doing. Here is some explana" \
                  "tion of what we are doing."
    elem_i = SubElement(elem, 'p')
    elem_i.text = "Here is some explanation of what we are doing. Here is" \
                  "explanation of what we are doing. Here is some explana" \
                  "tion of what we are doing."
    elem_i = SubElement(elem, 'p')

    return xml_root


def _make_custom_css(output_dir):
    """Output custom CSS file for
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
