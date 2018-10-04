# -*- coding: utf-8 -*-
"""Functions to grab and parse data from the MediaWiki API.
"""

import gzip
import json
import os
from os.path import join
import re
import shutil
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile

import requests


__version__ = 5


def wiki_json_path(page_title, lang='en'):
    """Returns local path to JSON file for Wikipedia page data.

    This function is used to determine where the dump of a
    call to the MediaWiki API, using the parse method, should
    be stored. As an extra action, the function also checks that
    the relevant directory exists and creates it if it does not.

    Args:
        page_title: A string containing the page title.
        lang: Two letter language code describing the Wikipedia
            language used to grab the data.

    Returns:
        A string describing a relative path to file.
    """
    page_title = re.sub("[ /]", "_", page_title)
    stat289_base_dir = os.path.dirname(os.getcwd())

    dir_name = join(stat289_base_dir, "data", lang)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    file_name = page_title + ".json.gz"
    file_path = join(dir_name, file_name)

    return file_path


def get_mediawiki_request(page_title, lang):
    """Returns URL to make parse request to the MediaWiki API.

    See naming rules of MediaWiki pages:

        https://www.mediawiki.org/wiki/Manual:PAGENAMEE_encoding

    In short, its complicated.

    Args:
        page_title: A string containing the page title.
        lang: Two letter language code describing the Wikipedia
            language used to grab the data.

    Returns:
        A string giving the complete request URL.
    """
    page_title = urllib.parse.unquote(page_title)
    page_title = re.sub(" ", "_", page_title)
    page_title = re.sub("\"", "%22", page_title)
    page_title = re.sub("&", "%26", page_title)
    page_title = re.sub("\'", "%27", page_title)
    page_title = re.sub("\\+", "%2B", page_title)

    base_api_url = 'https://' + lang + '.wikipedia.org/w/api.php'
    default_query = 'action=parse&format=json&redirects&'
    url = base_api_url + "?" + default_query + 'page=' + page_title

    return url


def get_wiki_json(page_title, lang='en'):
    """Returns JSON data as a dictionary for the Wikipedia page.

    This function either loads a cached version of the page or,
    if a local version of the page is not available, calls the
    MediaWiki API directly.

    Args:
        page_title: A string containing the page title.
        lang: Two letter language code describing the Wikipedia
            language used to grab the data.

    Returns:
        A dictionary object with the complete parsed JSON data.
    """
    file_path = wiki_json_path(page_title, lang)

    # if page does not exist, grab it from Wikipedia
    if not os.path.exists(file_path):
        page_data = download_wiki_json(page_title, lang)

        with gzip.open(file_path, 'wt') as outfile:
            json.dump(page_data, outfile)
        time.sleep(0.5)  # sleep for half second to avoid API limits

    # read the JSON data from local filesystem
    with gzip.open(file_path, 'rt') as infile:
        new_data = json.load(infile)

    return new_data


def download_wiki_json(page_title, lang='en'):
    """Download json data file Wikipedia
    """
    print("Pulling data from MediaWiki API: '" + page_title + "'")
    url = get_mediawiki_request(page_title, lang)
    req = requests.get(url)
    if req.status_code != requests.codes['ok']:
        raise IOError('Website cannot be reached')
    page_data = req.json()
    if 'parse' not in page_data:
        raise IOError('Wikipedia page not found')

    return page_data['parse']


def bulk_download(name, lang='en', force=False,
                  base_url="http://distantviewing.org/"):
    """Bulk download Wikipedia files

    Args:
        name: A character string describing the
        lang: Two letter language code describing the Wikipedia
            language used to grab the data.
        force: Boolean value. Should files be overwritten.
        base_url: The URL path that contains the zip file.
    Returns:
        Number of files added to the archive.
    """
    # get file paths
    zip_file_url = base_url + name + ".zip"
    zip_file = tempfile.NamedTemporaryFile().name + ".zip"
    zip_dir = tempfile.NamedTemporaryFile().name
    stat289_json_dir = os.path.dirname(os.getcwd())
    stat289_json_dir = join(stat289_json_dir, "data", lang)

    # download the zip file
    urllib.request.urlretrieve(zip_file_url, zip_file)

    # unzip contents of the zip file
    with zipfile.ZipFile(zip_file, 'r') as zfile:
        zfile.extractall(zip_dir)

    # move files to correct location
    num_added = 0
    archive_files = os.listdir(zip_dir)
    for json_file in archive_files:
        ipath = join(zip_dir, json_file)
        opath = join(stat289_json_dir, json_file)
        if force or not os.path.exists(opath):
            num_added += 1
            shutil.move(ipath, opath)

    msg = "Added {0:d} files from an archive of {1:d} files."
    print(msg.format(num_added, len(archive_files)))

    return num_added


def links_as_list(data):
    """Extracts MediaWiki JSON links as a list object.

    This helper function extracts valid MediaWiki links from
    Wikipedia and returns the data as a list.

    Args:
        data: Data returned from the function get_wiki_json.

    Returns:
        A list containing the internal links on the page.
    """
    output = []
    for link in data['links']:
        if link['ns'] == 0 and 'exists' in link:
            output.append(link['*'])

    return output
