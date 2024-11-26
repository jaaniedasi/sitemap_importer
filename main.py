from burp import IBurpExtender
from burp import IHttpService
from burp import IHttpRequestResponse
import urlparse
import os
import xml.etree.ElementTree as ET


class BurpExtender(IBurpExtender):

	def registerExtenderCallbacks(self, callbacks):
		self.callbacks = callbacks
		self.callbacks.setExtensionName("Sitemap Importer");
		self.helper = callbacks.getHelpers()

		root_folder = os.getcwd()
		sitemap_folder_path = os.path.join(root_folder, "source_sitemap")

		if not self.ensureSiteMapFolder(sitemap_folder_path):
			return

		
		summaries = []
		for file in os.listdir(sitemap_folder_path):
			if file.endswith(".xml"):
				file_path = os.path.join(sitemap_folder_path, file)

				parser = XMLParser(file_path)
				parser.parse()
				summaries.append(parser.getSummary())
				print(parser.getItems())
				for item in parser.getItems():
					self.addToSiteMap(item['url'], item['request'], item['response'], item['comment'], item['color'])

		print("\n---------- Summary ----------")
		for summary in summaries:
			self.printSummary(summary)


		print("done")
		return


	def addToSiteMap(self, url, request, response, comment, color):
		"""
		request: the whole request in base64 
		response: the whole response in base64
		url: url in string. Don't need path or query
		"""
		requestResponse = HttpRequestResponse(self.helper.base64Decode(request), self.helper.base64Decode(response), HttpService(url), comment, color)

		self.callbacks.addToSiteMap(requestResponse)


	def ensureSiteMapFolder(self, sitemap_folder_path):
		if not os.path.exists(sitemap_folder_path):
			print("Cannot find folder {}".format(sitemap_folder_path))
			return False

		if len([f for f in os.listdir(sitemap_folder_path) if f.endswith(".xml")]) == 0:
			print("no sitemap xml file found in {}".format(sitemap_folder_path))
			return False

		return True


	def printSummary(self, summary):
		print("- File: {}".format(summary["file_name"]))
		print("+ {} items successfully parsed".format(summary["item_count"]))

		if summary["skip_item_count"] > 0:
			print("+ {} items skipped due to response size > {} bytes".format(summary["skip_item_count"], summary["response_len_limit"]))
			for item in summary["skip_items"]:
				print("+++ skipped item: {}, reponse size: {}".format(item[0], item[1]))
		print("")


class XMLParser():
	"""
	Uses Element Tree. For this to work, find `add_class_path` and add xercesImpl.jar to it. 
	It returns an list of dictionaries containing the following data
	[request_base64, response_base64, url_string, color, comment] TODO: color does not work? there isn't a color/highlight property in the xml

	"""

	def __init__(self, file_path, verbose=True):
		self.items = []
		self.skip_items = []
		self.response_len_limit = 2000000
		self.verbose = verbose
		self.file_path = file_path
		self.file_name = file_path.split("/")[-1]

	def getItems(self):
		return self.items

	def getSkipItems(self):
		return self.skip_items

	def getSummary(self):
		summary_dict = {}
		summary_dict["file_name"] = self.file_name
		summary_dict["item_count"] = len(self.items)
		summary_dict["skip_item_count"] = len(self.skip_items)
		summary_dict["skip_items"] = self.skip_items
		summary_dict["response_len_limit"] = self.response_len_limit
		return summary_dict

	def _print(self, message, params):
		if self.verbose:
			print(message.format(*params))

	def _get_char(self, string, index):
			if len(string) > index:
				return string[index]
			else:
				return ""

	def parse(self):
		self._print("Begin parsing {}", [self.file_name])

		tree = ET.parse(self.file_path)
		root = tree.getroot()

		xml_items = root.findall('item')

		for xml_item in xml_items:
			item_dict = {
				"url": xml_item.find('url').text,
				"request": xml_item.find('request').text,
				"response": xml_item.find('response').text,
				"color": "" if xml_item.find('color') is None else xml_item.find('color').text,	
				"comment": "" if xml_item.find('comment') is None else xml_item.find('comment').text
			}
			self.items.append(item_dict)
		self._print("Finish parsing: {}", [self.file_name])

class HttpService(IHttpService):
	"""
	copied from https://github.com/modzero/burp-ResponseClusterer/blob/master/ResponseClusterer.py

	"""

	def __init__(self, url):
		x = urlparse.urlparse(url)
		if x.scheme in ("http", "https"):
			self._protocol = x.scheme
		else:
			raise ValueError()
		self._host = x.hostname
		if not x.hostname:
			self._host = ""
		self._port = None
		if x.port:
			 self._port = int(x.port)
		if not self._port:
			if self._protocol == "http":
				self._port = 80
			elif self._protocol == "https":
				self._port = 443

	def getHost(self):
		return self._host

	def getPort(self):
		return self._port

	def getProtocol(self):
		return self._protocol

	def __str__(self):
		return "protocol: {}, host: {}, port: {}".format(self._protocol, self._host, self._port)


class HttpRequestResponse(IHttpRequestResponse):

	def __init__(self, request, response, httpService, cmt, color):
		self.setRequest(request)
		self.setResponse(response)
		self.setHttpService(httpService)
		self.setHighlight(color)
		self.setComment(cmt)

	def getRequest(self):
		return self.req

	def getResponse(self):
		return self.resp

	def getHttpService(self):
		return self.serv

	def getComment(self):
		return self.cmt

	def getHighlight(self):
		return self.color

	def setHighlight(self, color):
		self.color = color

	def setComment(self, cmt):
		self.cmt = cmt

	def setHttpService(self, httpService):
		self.serv = httpService

	def setRequest(self, message):
		self.req = message

	def setResponse(self, message):
		self.resp = message
