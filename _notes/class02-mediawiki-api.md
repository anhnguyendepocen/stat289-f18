---
title: "MediaWiki API"
author: "Taylor Arnold"
output: html
---

## Application programming interface (API)

Last class we used the requests module to pull the raw HTML code
from a Wikipedia page. From this raw code we were able to extract
the most frequent words. We could also have located the internal
links, external references, and the location of any image files.

While the raw HTML code is useful, there is a better way to access
the information stored in a Wikipedia page. We can instead make use
of the MediaWiki API. An API is the preferred way for developers
(yes, that includes you now!) to interact with a website or service.
Benefits to us of using this API include:

- respecting the request of the Wikipedia Foundation
- the ability to access "old" versions of a Wikipedia page
- the structure of the returned API data is easier to parse

We will still make use of the requests library and require regular
expressions to parse some of the returned data, so everything we've
learned will still be useful as we pivot to using the MediaWiki API.

## MediaWiki API

To start today, we are going to play with the MediaWiki API from your
browser. This should help remove some of the mystery of what we are
doing before running the same requests in Python.

We need to understand a little bit about how HTTP requests are made,
though note that I am only going to explain a small subset of all the
details. When you make a request through HTTP (this is what happens
automatically when you visit a webpage), your browser requires two
pieces of information: the URL (where to make the request) and any
associated data. There are many different forms that the data can
take on; for the MediaWiki API we will only need simple variables that
are sent as part of the URL.

Here's an example of a URL that includes a variable. Everything after
the question mark `$` describes a set of variables that are passed to
the Google homepage. Here we have one variable named "q" (it stands
for query) which we have assigned to the value 'statistics'.

```
https://www.google.com/search?q=statistics
```

Copy and paste the above link in your browser. You'll see that it
automatically returns the search result for the string "statistics".
This is a basic example of calling an API by passing variables through
a URL.

In order to call the MediaWiki on the English version of Wikipedia,
we use the base url of "https://en.wikipedia.org/w/api.php". Let's
just look at a call before discussing the details. Copy and paste the
following into your browser:

```
https://en.wikipedia.org/w/api.php?action=query&prop=info|pageviews
|links&titles=University of Richmond
```

The data that gets returned is an format called JSON, rather than the
typical HTML that your browser expects. At least in Firefox, Chrome,
and Safari, a version of the JSON file should appear in an easy to
read format. Look through the information that is returned and consider:

- Why are only 10 links returned at the bottom of the page? Aren't there
a lot more on the website?
- Why are **these** 10 links returned over the others?
- What's captured by the "pageviews" result? What day has the highest
number of views?
- If you were going to save a copy of this returned information, what
might you name the file?

Let's now talk through the elements of the API call that you just made:

- **action**: this is the basic type of action that you want to make
with the API. Usually this will be either "query" or "parse".
- **prop**: the set of properties to get for the queried pages. Separate
properties by a vertical bar.
- **titles**: the set of page titles to work with; can specify more than
one by separating with a vertical bar.

We'll try another similar query now that will return the full text of
the site:

```
https://en.wikipedia.org/w/api.php?action=parse&format=json&page=University_of_Richmond
```

This won't look very nice in Safari but shows up cleanly in Firefox.
You should see just a single element "Parse". Open that up and you'll
get the title of the page, the id of the page, the id of the revision,
and information about the content of the page. Look around all of the
returned data. It should include:

- the text of the page parsed as HTML
- links to the webpage in other languages
- list of categories the page is a part of
- all of the internal page links
- all of the template pages used on the site
- links to the images on the page
- a list of external links
- a description of the sections on the page
- a few other metadata tags that won't be of particular use to us

## What now?

We are going to be good citizens of Wikipedia in this class by making use
of the MediaWiki API. Furthermore, we are going to cache requests made to
the API to reduce our drag on the Wikipedia servers (it's a non-profit
organization after all). That is, we want to build a Python function that
does the following:

- takes the title of a Wikipedia page as an input
- if we have not yet requested the page: download it with the MediaWiki
API and store a copy on your computer
- if we have a stored version of the file, load it
- return the JSON file regardless of how it was acquired

We will store the webpages in the data directory in the repository structure
that you created on the first day of class. Specifically, the UR JSON file
should be stored as:

```
data/en/University_of_Richmond.json
```

The "en" refers to the fact that we are looking at the English version of
Wikipedia. I've replaced spaces with underscores (Wikipedia thinks of underscores
and spaces as the same). I've also used the standard ".json" to represent a
JSON file. The tutorial today walks us through building a function to
do this for us!


