import xml.etree.ElementTree as ET


class Entry:
    id : str
    title : str
    description : str
    authors : list[str]
    links : dict[str, str]


    def __init__(self, id : str, title : str, description : str):
        self.id = id
        self.title = title
        self.description = description


    def _link(self, rel : str) -> str | None:
        if rel in self.links:
            return self.links[rel]
        return None


    def is_file(self):
        return self.download_url() is not None


    def download_url(self) -> str | None:
        return self._link("http://opds-spec.org/acquisition")


    def thumbnail_url(self) -> str | None:
        return self._link("http://opds-spec.org/image/thumbnail")


    def subsection_url(self) -> str | None:
        return self._link("subsection")


NS = { "atom": "http://www.w3.org/2005/Atom" }


class Reader:
    entries : dict[str, Entry]


def from_xml(xml : str) -> Reader:
    reader = Reader()
    root = ET.fromstring(xml)
    for entry in root.findall("atom:entry", NS):
        entry_id = entry.find("atom:id", NS).text
        reader.entries[entry_id] = Entry(
            entry_id,
            entry.find("atom:title", NS).text,
            entry.find("atom:content", NS).text,
            ""
        )
        for link in entry.findall("atom:link", NS):
            reader.links[link.attrib.get("rel")] = link.attrib.get("href")
        for author in entry.findall("atom:author", NS):
            for name in author.findall("atom:name", NS):
                reader.authors += name.text
    return reader


def from_json(self, json : str) -> Reader:
    # OPDS v2 goes here...
    reader = Reader()
    return reader
