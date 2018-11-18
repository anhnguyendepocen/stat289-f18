import json
import os
import re
import requests
import time
import urllib.parse

from os.path import join


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
        
    file_name = page_title + ".json"
    file_path = join(dir_name, file_name)
    
    return file_path


def get_mediawiki_request(page_title, lang):
    """Returns URL to make parse request to the MediaWiki API.
        
    Args:
        page_title: A string containing the page title.
        lang: Two letter language code describing the Wikipedia
            language used to grab the data.
            
    Returns:
        A string giving the complete request URL.
    """
    page_title = re.sub(" ", "_", page_title)
    #page_title = urllib.parse.urlencode({'page': page_title})
    #page_title = re.sub('%2F', '/', page_title) # don't encode '/'
    page_title = urllib.parse.unquote(page_title)
    
    base_api_url = 'https://' + lang + '.wikipedia.org/w/api.php'
    default_query = 'action=parse&format=json&'

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
        print("Pulling data from MediaWiki API: '" + page_title + "'")
        url = get_mediawiki_request(page_title, lang)
        r = requests.get(url)
        if r.status_code != requests.codes.ok:
             raise IOError('Website cannot be reached')
        page_data = r.json()
        if 'parse' not in page_data:
            raise IOError('Wikipedia page not found')
        with open(file_path, 'w') as outfile:
            json.dump(page_data['parse'], outfile)
        time.sleep(0.5) # sleep for half second to avoid API limits
            
    # read the JSON data from local filesystem
    with open(file_path, 'r') as infile:
        new_data = json.load(infile)
    
    return new_data


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
