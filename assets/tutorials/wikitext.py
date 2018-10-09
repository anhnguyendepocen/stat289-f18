# -*- coding: utf-8 -*-
"""Module for working with Wikipedia text
"""

import re
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement

__version__ = 2


###############################################################################
# Public classes and functions

class WikiCorpus():
    """Class to describe a collection of Wikipedia pages.
    """
    def __init__(self, links, stopwords=True, num_topics=40, num_clusters=40,
                 **kwargs):
        from gensim.models import TfidfModel
        from gensim.similarities.docsim import MatrixSimilarity

        if 'n_below' not in kwargs:
            kwargs['n_below'] = 5

        if 'n_above' not in kwargs:
            kwargs['n_above'] = 0.7

        if 'iterations' not in kwargs:
            kwargs['iterations'] = 200

        self.meta = _compute_meta_dataframe(links)
        self.lexicon, self.bow = _compute_lex_bow(self.meta,
                                                  stopwords=stopwords,
                                                  no_below=kwargs['n_below'],
                                                  no_above=kwargs['n_above'])
        self.tfidf = TfidfModel(self.bow)
        self.matsim = MatrixSimilarity(self.bow,
                                       num_features=len(self.lexicon))
        self.lda = _compute_lda(self.bow, self.lexicon, num_topics=num_topics,
                                iterations=kwargs['iterations'])
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
        """
        tf_obj = self.tfidf[self.bow[docx]]
        output = []
        for obj in sorted(tf_obj, key=lambda x: x[1], reverse=True)[:n_terms]:
            output.append((self.lexicon[obj[0]], obj[1]))
        return output

    def most_similar(self, docx):
        """Get vector of most similar documents.
        """
        return self.matsim[self.tfidf[self.bow[docx]]]

    def similarity_matrix(self):
        """Get similarity matrix.
        """
        return self.matsim[[self.tfidf[x] for x in self.bow]]

    def json_meta_template(self):
        """Dictionary of topic and cluster names.
        """
        json = dict(topic_names=["Topic {0:d}".format(x) for x in
                                 range(self.lda.num_topics)],
                    clust_names=["Cluster {0:d}".format(x) for x in
                                 range(max(self.clust) + 1)])
        return json


def wiki_text_explorer(wcorp, input_file=None, output_dir="text-explore"):
    """Produce visualization webpage.
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
        with open(input_file, 'r') as fin:
            name_dict = json.load(fin)

    _make_custom_css(output_dir)
    topic_names = name_dict['topic_names']
    clust_names = name_dict['clust_names']

    if not os.path.exists(os.path.join(output_dir, 'index.html')):
        with open(os.path.join(output_dir, 'index.html'), 'w') as fin:
            xml_page = _get_index_page(wcorp, topic_names)
            page = minidom.parseString(tostring(xml_page))
            page = page.toprettyxml(indent=" ")
            fin.write("<!DOCTYPE html>\n")
            fin.write(page[23:])

    with open(os.path.join(output_dir, 'docs.html'), 'w') as fin:
        xml_page = _get_doc_page(wcorp, topic_names, clust_names)
        page = minidom.parseString(tostring(xml_page)).toprettyxml(indent=" ")
        fin.write("<!DOCTYPE html>\n")
        fin.write(page[23:])

    with open(os.path.join(output_dir, 'clusters.html'), 'w') as fin:
        xml_page = _get_cluster_page(wcorp, clust_names)
        page = minidom.parseString(tostring(xml_page)).toprettyxml(indent=" ")
        fin.write("<!DOCTYPE html>\n")
        fin.write(page[23:])

    with open(os.path.join(output_dir, 'topics.html'), 'w') as fin:
        xml_page = _get_topic_page(wcorp, topic_names)
        page = minidom.parseString(tostring(xml_page)).toprettyxml(indent=" ")
        fin.write("<!DOCTYPE html>\n")
        fin.write(page[23:])

    with open(os.path.join(output_dir, 'viz.html'), 'w') as fin:
        xml_page = _get_viz_page(wcorp, output_dir)
        page = minidom.parseString(tostring(xml_page)).toprettyxml(indent=" ")
        fin.write("<!DOCTYPE html>\n")
        fin.write(page[23:])


def get_internal_links(data):
    """Extract internal Wikipedia links.
    """
    from wiki import get_wiki_json

    if isinstance(data, str):
        data = get_wiki_json(data)

    ilinks = [x['*'] for x in data['links'] if x['ns'] == 0]
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


###############################################################################
# Private functions
#pylint: disable-msg=too-many-locals

def _compute_meta_dataframe(links):
    """Convert links to a pandas DataFrame object
    """
    import pandas as pd
    from wiki import get_wiki_json

    meta = dict(link=[], title=[], doc=[], num_sections=[],
                num_images=[], num_ilinks=[], num_elinks=[],
                num_langs=[], langs=[], ilinks=[])
    for link in links:
        data = get_wiki_json(link)
        tree = ET.fromstring(data['text']['*'])

        meta['link'].append(re.sub(' ', '_', data['title']))
        meta['title'].append(re.sub('<[^>]+>', '', data['displaytitle']))
        meta['doc'].append(_tree_to_doc(tree))
        meta['num_sections'].append(len(data['sections']))
        meta['num_images'].append(len(data['images']))
        meta['num_ilinks'].append(len(data['links']))
        meta['num_elinks'].append(len(data['externallinks']))
        meta['num_langs'].append(len(data['langlinks']))
        meta['langs'].append([x['lang'] for x in data['langlinks']])
        meta['ilinks'].append([re.sub(' ', '_', x['*']) for x in
                               data['links'] if x['ns'] == 0])
        lat, lon = _tree_to_geo(tree)
        meta['lat'] = lat
        meta['lon'] = lon

    pdf = pd.DataFrame(meta).drop_duplicates(subset='link', keep="first")
    return pdf.reset_index()


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


def _tree_to_doc(tree):
    """Extract paragraph text from an ElementTree.
    """
    output = []
    for child in tree.findall('.//p'):
        text = "".join(list(child.itertext()))
        text = _clean_text(text)
        if text:
            output.append(text)

    return " ".join(output)


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


def _compute_lex_bow(meta, stopwords, no_below, no_above):
    """Produce the full lexicon object.
    """
    from gensim import corpora

    word_list = []
    for doc in meta['doc']:
        word_list.append(re.findall('(\\w+)', doc.lower()))

    lexicon = corpora.Dictionary(word_list)
    lexicon = _reduce_lex(lexicon, stopwords=stopwords, no_below=no_below,
                          no_above=no_above)

    bow = []
    for word in word_list:
        bow.append(lexicon.doc2bow(word))

    return lexicon, bow


def _reduce_lex(lexicon, stopwords, no_below, no_above):
    if stopwords:
        with open('ranksnl_large.txt', 'r') as fin:
            sw_list = fin.read().splitlines()
        sw_list = set(sw_list).intersection(lexicon.token2id.keys())
        ids = [lexicon.token2id[x] for x in sw_list]
        lexicon.filter_tokens(ids)

    lexicon.filter_extremes(no_below=no_below, no_above=no_above)
    lexicon.compactify()

    return lexicon


def _compute_lda(bow, lexicon, num_topics, iterations):
    from gensim.models import LdaModel
    return LdaModel(bow, id2word=lexicon, num_topics=num_topics, alpha='auto',
                    iterations=iterations, random_state=17)


def _compute_spectral_clust(similarity_matrix, num_clusters):
    from warnings import simplefilter
    from sklearn.cluster import SpectralClustering

    simplefilter("ignore", UserWarning)     # ignore disconnected warning
    scmodel = SpectralClustering(n_clusters=num_clusters,
                                 affinity='precomputed',
                                 random_state=17)

    return scmodel.fit_predict(similarity_matrix)


def _get_xml_head(headings, name=None):
    xml_root = Element("html", lang="en")

    xml_head = SubElement(xml_root, "head")
    SubElement(xml_head, "meta", charset="utf-8")
    SubElement(xml_head, "title", charset="utf-8")
    xml_head[-1].text = "Wiki Text Explorer"
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
    xml_nav[-1][0][0].text = "Wiki Text Explorer"

    elem = SubElement(xml_nav[0], "div",
                      {'id': "navbar", 'class': "navbar-collapse collapse"})

    pages = [('docs', 'Docs'), ('clusters', 'Clusters'), ('topics', 'Topics'),
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


def _get_doc_page(wcorp, topic_names, clust_names):
    import numpy as np
    xml_root, tab = _get_xml_head(headings=['Page', 'Top Words', 'TF-IDF',
                                            'Topics'],
                                  name='docs')

    doc_top = np.zeros((len(wcorp.meta['link']), wcorp.lda.num_topics),
                       dtype=np.float32)
    for idx, doc in enumerate(list(wcorp.lda.get_document_topics(wcorp.bow))):
        for val in doc:
            doc_top[idx, val[0]] = val[1]

    for idx in range(wcorp.meta.shape[0]):
        xml_tr = SubElement(tab, 'tr', id='sec{0:d}'.format(idx))
        xml_td = SubElement(xml_tr, 'td')
        elem = SubElement(SubElement(SubElement(xml_td, 'p'), 'b'), 'a')
        title = "https://en.wikipedia.org/wiki/{0:s}"
        elem.attrib['href'] = title.format(wcorp.meta['link'][idx])
        elem.attrib['target'] = "_blank"
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

        msim = list(doc_top[idx, :])
        msim = sorted(zip(range(len(msim)), msim), key=lambda x: x[1],
                      reverse=True)[:10]
        msim = [x for x in msim if x[1] > 0.001]
        xml_ul = SubElement(SubElement(xml_tr, 'td'), 'ul',
                            style='list-style-type: none;')
        for idy, val in msim:
            elem = SubElement(xml_ul, 'li')
            SubElement(elem, 'a', href='topics.html#sec{0:d}'.format(idy - 1))
            elem.find('.//a').text = topic_names[idy]
            elem = SubElement(elem, 'span')
            elem.attrib['style'] = 'color: #bababa; font-size: 12px'
            elem.text = "{0:.03f}".format(val)

    return xml_root


def _make_doc_meta_table(wcorp, elem, idx, clust_names):
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
    eli = SubElement(elem, 'li')
    eli.attrib['style'] = 'padding-top: 18px'
    eli = SubElement(eli, 'a')
    eli.text = clust_names[wcorp.clust[idx]]
    eli.attrib['href'] = "clusters.html#sec{0:d}".format(wcorp.clust[idx])


def _get_cluster_page(wcorp, clust_names):
    xml_root, tab = _get_xml_head(headings=['Cluster', 'Pages'],
                                  name='clusters')

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


def _get_topic_page(wcorp, topic_names):
    import numpy as np

    xml_root, tab = _get_xml_head(headings=['Topic', 'Pages', 'Words'],
                                  name='topics')

    doc_top = np.zeros((len(wcorp.meta['link']), wcorp.lda.num_topics),
                       dtype=np.float32)
    for idx, val in enumerate(wcorp.lda.get_document_topics(wcorp.bow)):
        for topic in val:
            doc_top[idx, topic[0]] = topic[1]

    topics = wcorp.lda.get_topics()
    words = list(wcorp.lexicon.itervalues())
    for idy in range(doc_top.shape[1]):
        xml_tr = SubElement(tab, 'tr', id='sec{0:d}'.format(idy))
        elem = SubElement(SubElement(SubElement(xml_tr, 'td'), 'p'), 'b')
        elem.text = topic_names[idy]

        vals = sorted(zip(range(doc_top.shape[0]), list(doc_top[:, idy])),
                      key=lambda x: x[1], reverse=True)
        vals = [x for x in vals[:20] if x[1] > 0.001]

        xml_ul = SubElement(SubElement(xml_tr, 'td'), 'ul')
        xml_ul.attrib['style'] = 'list-style-type: none;'
        _add_topic_docs(xml_ul, vals, wcorp)

        vals = sorted(zip(range(len(words)), topics[idy, :]),
                      key=lambda x: x[1], reverse=True)[:20]
        vals = [(x[0], x[1] / vals[0][1]) for x in vals]

        xml_ul = SubElement(SubElement(xml_tr, 'td'), 'ul')
        xml_ul.attrib['style'] = 'list-style-type: none;'
        for idx, val in vals:
            elem = SubElement(xml_ul, 'li')
            elem.text = words[idx]
            elem = SubElement(elem, 'span',
                              style="color: #bababa; font-size: 12px")
            elem.text = "{0:.03f}".format(val)

    return xml_root


def _add_topic_docs(xml_ul, vals, wcorp):
    for idx, val in vals:
        elem = SubElement(xml_ul, 'li')
        elem_a = SubElement(elem, 'a',
                            href='docs.html#sec{0:d}'.format(idx - 1))
        elem_a.text = wcorp.meta['title'][idx]
        elem = SubElement(elem, 'span',
                          style="color: #bababa; font-size: 12px")
        elem.text = "{0:.03f}".format(val)


def _get_viz_page(wcorp, output_dir):
    """Create interactive plot pages.
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

    with open(os.path.join(output_dir, "js", "plot.js"), 'w') as fin:
        fin.write(script)

    xml_root, _ = _get_xml_head(headings=[], name='viz')
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


def _get_index_page(wcorp, output_dir):
    """Create interactive plot pages.
    """
    xml_root, _ = _get_xml_head(headings=[])
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
                                             "600px" })
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

    with open(os.path.join(output_dir, "css", "custom.css"), 'w') as fin:
        fin.write(ctext)
