"""OPDS feed parsing and deserialization utilities."""

import xml.etree.ElementTree as ET


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
    links : dict[str, str]


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
        if rel in self.links:
            return self.links[rel]
        return None


    def is_file(self):
        """Determines if the entry is a file.

        Returns:
            True if the entry is a file. False if the entry is a directory.
        """
        return self.download_url() is not None


    def download_url(self) -> str | None:
        """Returns the download URL if present.

        Returns:
            The download URL or None if not present.
        """
        dl = self._link("http://opds-spec.org/acquisition")
        if dl is not None:
            return dl
        return self._link("http://opds-spec.org/acquisition/open-access")


    def thumbnail_url(self) -> str | None:
        """Returns the thumbnail URL if present.
        
        Returns:
            The thumbnail URL or None if not present.
        """
        return self._link("http://opds-spec.org/image/thumbnail")


    def subsection_url(self) -> str | None:
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
    entries : dict[str, Entry]
    links : dict[str, str]
    version : str

    def __init__(self, title : str):
        self.title = title
        self.entries = {}
        self.links = {}
        self.version = ""


def from_xml(xml : str) -> Reader:
    """Deserializes a XML (v1.2) OPDS feed.

    Args:
        xml: An XML OPDS (Atom) feed.

    Returns:
        An OPDS reader object.
    """
    root = ET.fromstring(xml)
    reader = Reader(root.find("atom:title", NS).text)
    reader.version = "1"
    for link in root.findall("atom:link", NS):
        reader.links[link.attrib.get("rel")] = link.attrib.get("href")
    for entry in root.findall("atom:entry", NS):
        e : Entry = Entry(
            entry.find("atom:id", NS).text,
            entry.find("atom:title", NS).text,
            entry.find("atom:content", NS).text
        )
        for link in entry.findall("atom:link", NS):
            e.links[link.attrib.get("rel")] = link.attrib.get("href")
        for author in entry.findall("atom:author", NS):
            for name in author.findall("atom:name", NS):
                e.authors += [ name.text ]
        reader.entries[e.id] = e
    return reader


def from_json(self, json : str) -> Reader:
    """Deserializes a JSON (v2) OPDS feed.
    
    Args:
        json: An JSON OPDS feed.

    Returns:
        An OPDS reader object.
    """
    # TODO: OPDS v2 goes here...
    reader = Reader()
    reader.version = "2"
    return reader
