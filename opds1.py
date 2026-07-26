# OPDS v1 goes here
# Converts XML into data structures

class ReaderV1:

	NS = { "atom": "http://www.w3.org/2005/Atom" }

	xml : str

	def __init__(self, xml : str):
		self.xml = xml