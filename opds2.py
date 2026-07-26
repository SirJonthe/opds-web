# OPDS v2 goes here
# Converts JSON into data structures

class ReaderV2:

	json : str

	def __init__(self, json : str):
		self.json = json