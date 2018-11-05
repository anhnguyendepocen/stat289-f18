# -*- coding: utf-8 -*-
"""Functions to grab, parse, and display images from the MediaWiki API.
"""

__version__ = 1

#pylint: disable-msg=too-many-locals
#pylint: disable-msg=bare-except

###############################################################################
# Public classes and functions

def image_data_frame(links, min_size=200, max_size=750, max_page=None,
                     download=True):
    """Return metadata about images found on a Wikipedia page.

    Args:
        links: A list of page links.
        min_size: An integer describing the minimum dimensions that an image
            must have (both height and width) in order to be returned.
        max_size: The maximum size allowed to be returned by the function.
        max_page: The maximum number of images to be returned from a page.
        download: Boolean; should the images be downloaded if they have not yet
            been?

    Returns:
        A pandas DataFrame with one row for each image found.
    """
    import pandas as pd
    import re
    from os.path import basename

    page = []
    img = []
    size = []
    all_img_links = []

    for link in links:
        img_links, sizes = _page_img_links(link, min_size, max_size)
        if img_links:
            try:
                if max_page is not None:
                    img_links = img_links[:max_page]
                    sizes = sizes[:max_page]

                img_names = [basename(x).lower() for x in img_links]
                img_names = [x[-160:] for x in img_names]
                img_names = [re.sub('[^a-z\.-]+', '', x) for x in img_names]
                img_names = [re.sub('\\Apx-', '', x) for x in img_names]

                if download:
                    _download_img_links(img_links, img_names)

                page += [link] * len(img_links)
                img += img_names
                size += sizes
                all_img_links += img_links

            except:
                pass

    return pd.DataFrame(dict(page=page, img=img, max_size=size,
                             img_links=all_img_links))


def vgg19_embed(img_links):
    """Return embedded values from the penultimate layer of the VGG19 model.

    Args:
        img_links: A list of image links.

    Returns:
        A numpy array with one row for each image.
    """
    from keras.applications.vgg19 import VGG19
    from keras.applications.vgg19 import preprocess_input
    from keras.models import Model
    from keras.preprocessing import image
    import numpy as np
    import os

    stat289_base_dir = os.path.dirname(os.getcwd())
    dir_name = os.path.join(stat289_base_dir, "data", "embed")
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    vgg19_full = VGG19(weights='imagenet')
    vgg_fc2 = Model(inputs=vgg19_full.input,
                    outputs=vgg19_full.get_layer('fc2').output)

    data = []
    for link in img_links:
        output_file = os.path.join(dir_name, link[:-3] + "npy")

        if os.path.exists(output_file):
            embed_mat = np.load(output_file)

        else:

            embed_mat = load_image(link, target_size=(224, 224))
            embed_mat = image.img_to_array(embed_mat)
            embed_mat = np.expand_dims(embed_mat, axis=0)
            embed_mat = preprocess_input(embed_mat)
            embed_mat = vgg_fc2.predict(embed_mat, verbose=True)
            embed_mat.dump(output_file)

        data.append(embed_mat[0, :])

    return np.stack(data)


def load_image(img_link, target_size=None):
    """Load an image from a URL.

    Args:
        img_link: string giving the URL path to the image.
        target_size: tuple describing the desired dimensions of the image. If
            None, load in the native dimensions.

    Returns:
        A PIL Image instance.
    """
    from os.path import join, dirname
    import os
    from keras.preprocessing import image
    import numpy as np

    stat289_base_dir = dirname(os.getcwd())
    dir_name = join(stat289_base_dir, "data", "img")
    img_path = join(dir_name, img_link)

    if not os.path.exists(img_path):
        if target_size is None:
            target_size = (224, 224)
        img = np.zeros((target_size[0], target_size[1], 3))
    elif target_size is not None:
        img = image.load_img(img_path, target_size=target_size)
    else:
        img = image.load_img(img_path)

    return img


###############################################################################
# Private functions

def _download_img_links(img_links, img_names):
    """Take image links and save locally.

    Args:
        img_links: A list of image links.
        img_names: A list of image names.

    Returns:
        None.
    """
    from os.path import join, dirname, exists
    import os
    import shutil
    import requests

    stat289_base_dir = dirname(os.getcwd())
    dir_name = join(stat289_base_dir, "data", "img")
    if not exists(dir_name):
        os.makedirs(dir_name)

    for link, page_title in zip(img_links, img_names):
        output_path = join(dir_name, page_title)
        if not os.path.exists(output_path):
            print("Pulling image from MediaWiki: '" + page_title + "'")
            req = requests.get(link, stream=True)
            if req.status_code == 200:
                with open(output_path, 'wb') as fin:
                    req.raw.decode_content = True
                    shutil.copyfileobj(req.raw, fin)


def _page_img_links(page_title, min_size, max_size):
    """Return all image links from a Wikipedia page.

    Args:
        page_title: A string containing the page title.
        min_size: An integer describing the minimum dimensions that an image
            must have (both height and width) in order to be returned.
        max_size: The maximum size allowed to be returned by the function.

    Returns:
        A tuple of the image links as a list and the image (max) sizes.
    """
    import xml.etree.ElementTree as ET
    import wiki

    data = wiki.get_wiki_json(page_title)
    tree = ET.fromstring(data['text']['*'])
    req_keys = set(['alt', 'src', 'width', 'height'])

    img_links = []
    sizes = []
    for img in tree.findall(".//img"):
        attributes = set(img.attrib.keys())
        if len(attributes.intersection(req_keys)) == 4:
            width = int(img.attrib['width'])
            height = int(img.attrib['height'])
            size = max(height, width)
            if min_size <= size <= max_size:
                if img.attrib['src'][-3:] in ['jpg', 'png']:
                    img_links.append("https://" + img.attrib['src'][2:])
                    sizes.append(max(height, width))

    return img_links, sizes
