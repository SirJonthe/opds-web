"""OPDS feed parsing and deserialization utilities."""

import xml.etree.ElementTree as ET
import json
from urllib.parse import urljoin, quote
from html import escape
import uritemplate


class Link:
    """Represents a URL link with additional metadata to understand the contents at the other end of the link.

    Attributes:
        url: The URL as a string.
        mime: The MIME type.
    """
    url : str
    mime : str


    def __init__(self, url : str, mime : str | None = None):
        self.url = url
        self.mime = mime


class Entry:
    """Represents a single deserialized entry in an OPDS feed (generally a directory or a file).

    Attributes:
        id: The OPDS ID of the current entry.
        title: The title of the entry.
        description: The description of the entry.
        authors: If a file, contains a list of authors.
        links: A mess of links present in the entry. Use wrapper functions to get URL:s safely.
    """
    id : str
    title : str
    description : str
    authors : list[str]
    links : dict[str, list[Link]]


    def __init__(self, id : str, title : str, description : str):
        self.id = id
        self.title = title
        self.description = description
        self.authors = []
        self.links = {}


    def _link(self, rel : str) -> str | None:
        """Safely returns a link by key from the stored links.

        Args:
            rel: The key used to store a link.
        
        Returns:
            The URL or none if the key is not present.
        """
        return self.links.get(rel, None)


    def is_file(self):
        """Determines if the entry is a file.

        Returns:
            True if the entry is a file. False if the entry is a directory.
        """
        return self.download_urls() not in [ None, [] ]


    def download_urls(self) -> list[Link] | None:
        """Returns the download URL:s if present.

        Returns:
            The download URL:s or None if not present.
        """
        dl = self._link("http://opds-spec.org/acquisition")
        if dl is not None:
            return dl
        return self._link("http://opds-spec.org/acquisition/open-access")


    def thumbnail_urls(self) -> list[Link] | None:
        """Returns the thumbnail URL if present.
        
        Returns:
            The thumbnail URL or None if not present.
        """
        return self._link("http://opds-spec.org/image/thumbnail")


    def subsection_url(self) -> Link | None:
        """Returns the subsection URL if present.

        Returns:
            The subsection URL or None if not present.
        """
        return self._link("subsection")[0]


class SearchTemplateType:
    OPENSEARCH = "opensearch"
    URI_TEMPLATE = "uri-template"


class Search:
    """Represents the search function in an OPDS feed.
    
    Attributes:
        template: The template URL for searching.
        template_type: Open Search or URI template.
        description: The description of the particular search function.
    """
    template : str
    template_type : SearchTemplateType
    description : str


    def __init__(self, template : str, template_type : SearchTemplateType, description : str):
        self.template = template
        self.template_type = template_type
        self.description = description


    def url(self, query : str) -> str:
        """Performs a query and returns the resulting URL.

        Args:
            query: The query.

        Returns:
            The full URL with complete query.
        """
        if self.template_type == SearchTemplateType.URI_TEMPLATE:
            return uritemplate.expand(
                self.template,
                {"query": query}
            )
        elif self.template_type == SearchTemplateType.OPENSEARCH:
            return self.template.replace(
                "{searchTerms}",
                quote(query, safe="")
            )
        raise ValueError(f'Unsupported template type: "{self.template_type}"')


NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "os": "http://a9.com/-/spec/opensearch/1.1/"
}


class Reader:
    """Represents a deserialized OPDS feed.

    Attributes:
        title: The stored title of the OPDS feed.
        entries: A dictionary of deserialized OPDS feed entries grouped by entry ID as key.
        links: A dictionary of links stored in the root of the OPDS feed.
        version: A string indicating the version of the OPDS feed that was deserialized.
    """
    title : str
    entries : dict[str]
    links : dict[str, list[Link]]
    version : str
    search : Search | None
    page : int


    def __init__(self, title : str, version : str):
        self.title = title
        self.entries = {}
        self.links = {}
        self.version = version
        self.search = None
        self.page = 1


def _get_content(content : ET.Element[str] | None) -> str:
    if content is None:
        return ""
    return "".join(content.itertext()).replace("\n", "<br>\n")


def from_xml(xml_str : str, base_url : str, page : int) -> Reader:
    """Deserializes an XML (v1.2) OPDS feed.

    Args:
        xml_str: String containing XML OPDS (Atom).
        base_url: The base URL of the OPDS server.
        page: The page integer.

    Returns:
        An OPDS reader object.
    """
    root = ET.fromstring(xml_str)
    reader = Reader(root.find("atom:title", NS).text, "1")
    reader.page = max([page, 1])
    for link in root.findall("atom:link", NS):
        rel : str = link.attrib.get("rel")
        href : str = link.attrib.get("href")
        if rel not in reader.links:
            reader.links[rel] = []
        reader.links[rel] += [Link(urljoin(base_url, href), link.get("type", None))]
    for entry in root.findall("atom:entry", NS):
        e : Entry = Entry(
            entry.find("atom:id", NS).text,
            entry.find("atom:title", NS).text,
            _get_content(entry.find("atom:content", NS)) # Simple way of fetching content that strips out HTML/XHTML
        )
        for link in entry.findall("atom:link", NS):
            rel : str = link.attrib.get("rel")
            href : str = link.attrib.get("href")
            if rel not in e.links:
                e.links[rel] = []
            e.links[rel] += [Link(urljoin(base_url, href), link.get("type", None))]
        for author in entry.findall("atom:author", NS):
            for name in author.findall("atom:name", NS):
                e.authors += [ name.text ]
        reader.entries[e.id] = e
    return reader


def search_from_xml(xml_str : str, base_url : str) -> Search:
    """Deserializes an XML Open Search feed.

    Args:
        xml_str: String containing XML Open Search.
        base_url: The base URL of the OPDS server.
    
    Returns:
        An OPDS Search object.
    """
    root = ET.fromstring(xml_str)
    if root is None:
        return None
    url = None
    for u in root.findall("os:Url", NS):
        t = u.get("type")
        if t is not None and t in ["application/atom+xml"]:
            url = u
            break
    if url is None:
        url = root.find("os:Url", NS) # Sometimes only one URL is present and it does not signal its type
        if url is None:
            return None
    template = url.get("template")
    if template is None:
        return None
    description = root.find("os:Description", NS)
    if description is None:
        description = root.find("os:ShortName", NS)
    if description is not None:
        description = description.text
    else:
        description = "Search"
    return Search(urljoin(base_url, template), SearchTemplateType.OPENSEARCH, description)


def from_json(json_str : str, base_url : str, page : int) -> Reader:
    """Deserializes a JSON (v2) OPDS feed.

    Args:
        json_str: A string containing JSON OPDS v2.
        base_url: The base URL of the OPDS server.
        page: The page integer. This might be overwritten by whatever the JSON says about what the current page is.
    
    Returns:
        An OPDS reader object.
    """
    obj = json.loads(json_str)
    reader : Reader = Reader(obj["metadata"]["title"], "2")
    reader.page = int(obj["metadata"].get("currentPage", max([page, 1])))
    for link in obj.get("links", []):
        rel = link.get("rel")
        href = link.get("href")
        if rel and href:
            if rel not in reader.links:
                reader.links[rel] = []
            reader.links[rel] += [Link(href, link.get("type", None))]
    if "navigation" in obj:
        r : Reader = Reader("Navigation", "2")
        for nav in obj.get("navigation", []):
            e = Entry(
                nav["href"],
                nav["title"],
                escape(nav.get("description", "")).replace("\n", "<br>\n")
            )
            if "subsection" not in e.links:
                e.links["subsection"] = []
            e.links["subsection"] += [Link(urljoin(base_url, nav["href"]), link.get("type", None))]
            r.entries[e.id] = e
        reader.entries["Navigation"] = r
    for group in obj.get("groups", []):
        r : Reader = Reader(group["metadata"]["title"], "2")
        r.page = int(group["metadata"].get("currentPage", "1"))
        for nav in group.get("navigation", []):
            e = Entry(
                nav["href"],
                nav["title"],
                escape(nav.get("description", "")).replace("\n", "<br>\n")
            )
            if "subsection" not in e.links:
                e.links["subsection"] = []
            e.links["subsection"] += [Link(urljoin(base_url, nav["href"]), link.get("type", None))]
            r.entries[e.id] = e
        for pub in group.get("publications", []):
            md = pub["metadata"]
            e = Entry(
                pub["links"][0]["href"],
                md["title"],
                escape(md.get("description", "")).replace("\n", "<br>\n")
            )
            if "author" in md:
                for author in md["author"]:
                    e.authors.append(author["name"])
            if "contributor" in md:
                for contributor in md["contributor"]:
                    if isinstance(contributor, str):
                        e.authors.append(contributor)
                    elif isinstance(contributor, map) and "aut" in contributor.get("role", []):
                        e.authors.append(contributor["name"])
            for link in pub.get("links", []):
                rel = link.get("rel")
                href = link.get("href")
                if rel and href:
                    if rel not in e.links:
                        e.links[rel] = []
                    e.links[rel] = [Link(urljoin(base_url, href), link.get("type", None))]
            for image in pub.get("images", []):
                if "thumbnail" in image["href"]:
                    e.links["http://opds-spec.org/image/thumbnail"] = [Link(urljoin(base_url, image["href"]), image.get("type", None))]
                    break
            r.entries[e.id] = e
        if len(r.entries) > 0:
            reader.entries[r.title] = r
    if "publications" in obj:
        r : Reader = Reader("Publications", "2")
        for pub in obj.get("publications", []):
            md = pub["metadata"]
            e = Entry(
                pub["links"][0]["href"],
                md["title"],
                escape(md.get("description", "")).replace("\n", "<br>\n")
            )
            if "author" in md:
                for author in md["author"]:
                    e.authors.append(author["name"])
            if "contributor" in md:
                for contributor in md["contributor"]:
                    if isinstance(contributor, str):
                        e.authors.append(contributor)
                    elif isinstance(contributor, map) and "aut" in contributor.get("role", []):
                        e.authors.append(contributor["name"])
            for link in pub.get("links", []):
                rel = link.get("rel")
                href = link.get("href")
                if rel and href:
                    if rel not in e.links:
                        e.links[rel] = []
                    e.links[rel] += [Link(urljoin(base_url, href), link.get("type", None))]
            for image in pub.get("images", []):
                if "thumbnail" in image["href"]:
                    e.links["http://opds-spec.org/image/thumbnail"] = [Link(urljoin(base_url, image["href"]), image.get("type", None))]
                    break
            r.entries[e.id] = e
        reader.entries["Publications"] = r
        for link in obj["links"]:
            if link.get("rel", "") == "search" and link.get("type", "") in ["application/opds+json"]:
                reader.search = search_from_json(link, base_url)
                break
    return reader


def search_from_json(json_map : dict[str], base_url : str) -> Search:
    """Deserializes an OPDS (v2) JSON search entry.
    
    Args:
        json_map: Map with string keys containing JSON OPDS search information.
        base_url: The base URL of the OPDS server.
    
    Returns:
        An OPDS Search object.
    """
    if "href" not in json_map:
        return None
    url = urljoin(base_url, json_map["href"])
    return Search(url, SearchTemplateType.URI_TEMPLATE, json_map.get("title", "Search"))
