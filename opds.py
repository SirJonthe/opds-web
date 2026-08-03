"""OPDS feed parsing and deserialization utilities."""

import xml.etree.ElementTree as ET
import json
from urllib.parse import urljoin
from html import escape


class Link:
    url : str
    mime : str

    def __init__(self : Link, url : str, mime : str | None = None):
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
    links : dict[str, Link]


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
        return self.download_url() is not None


    def download_url(self) -> Link | None:
        """Returns the download URL if present.

        Returns:
            The download URL or None if not present.
        """
        dl = self._link("http://opds-spec.org/acquisition")
        if dl is not None:
            return dl
        return self._link("http://opds-spec.org/acquisition/open-access")


    def thumbnail_url(self) -> Link | None:
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
        return self._link("subsection")


NS = { "atom": "http://www.w3.org/2005/Atom" }


class Reader:
    """Represents a deserialized OPDS feed.

    Attributes:
        title: The stored title of the OPDS feed.
        entries: A dictionary of deserialized OPDS feed entries grouped by entry ID as key.
        links: A dictionary of links stored in the root of the OPDS feed.
        version: A string indicating the version of the OPDS feed that was deserialized.
    """
    title : str
    entries : dict[str, Entry | Reader]
    links : dict[str, Link]
    version : str

    def __init__(self, title : str, version : str):
        self.title = title
        self.entries = {}
        self.links = {}
        self.version = version


def from_xml(xml_str : str, base_url : str) -> Reader:
    """Deserializes a XML (v1.2) OPDS feed.

    Args:
        xml_str: String containing XML OPDS (Atom).

    Returns:
        An OPDS reader object.
    """
    root = ET.fromstring(xml_str)
    reader = Reader(root.find("atom:title", NS).text, "1")
    for link in root.findall("atom:link", NS):
        reader.links[link.attrib.get("rel")] = Link(urljoin(base_url, link.attrib.get("href")))
    for entry in root.findall("atom:entry", NS):
        e : Entry = Entry(
            entry.find("atom:id", NS).text,
            entry.find("atom:title", NS).text,
            entry.find("atom:content", NS).text
        )
        for link in entry.findall("atom:link", NS):
            e.links[link.attrib.get("rel")] = Link(urljoin(base_url, link.attrib.get("href")))
        for author in entry.findall("atom:author", NS):
            for name in author.findall("atom:name", NS):
                e.authors += [ name.text ]
        reader.entries[e.id] = e
    return reader


def from_json(json_str : str, base_url : str) -> Reader:
    """Deserializes a JSON (v2) OPDS feed.

    Args:
        json_str: A string containing JSON OPDS v2.
    
    Returns:
        An OPDS reader object.
    """
    #print(json_str)
    obj = json.loads(json_str)
    reader : Reader = Reader(obj["metadata"]["title"], "2")
    for link in obj.get("links", []):
        rel = link.get("rel")
        href = link.get("href")
        if rel and href:
            reader.links[rel] = Link(href, link.get("type", None))
    if "navigation" in obj:
        r : Reader = Reader("Navigation", "2")
        for nav in obj.get("navigation", []):
            e = Entry(
                nav["href"],
                nav["title"],
                escape(nav.get("description", "")).replace("\n", "<br>\n")
            )
            e.links["subsection"] = Link(urljoin(base_url, nav["href"]), link.get("type", None))
            r.entries[e.id] = e
        reader.entries["Navigation"] = r
    for group in obj.get("groups", []):
        r : Reader = Reader(group["metadata"]["title"], "2")
        for nav in group.get("navigation", []):
            e = Entry(
                nav["href"],
                nav["title"],
                escape(nav.get("description", "")).replace("\n", "<br>\n")
            )
            e.links["subsection"] = Link(urljoin(base_url, nav["href"]), link.get("type", None))
            r.entries[e.id] = e
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
                    e.links[rel] = Link(urljoin(base_url, href), link.get("type", None))
            for image in pub.get("images", []):
                if "thumbnail" in image["href"]:
                    e.links["http://opds-spec.org/image/thumbnail"] = Link(urljoin(base_url, image["href"]), image.get("type", None))
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
                    e.links[rel] = Link(urljoin(base_url, href), link.get("type", None))
            for image in pub.get("images", []):
                if "thumbnail" in image["href"]:
                    e.links["http://opds-spec.org/image/thumbnail"] = Link(urljoin(base_url, image["href"]), image.get("type", None))
            r.entries[e.id] = e
        reader.entries["Publications"] = r
    return reader
