import requests
from pathlib import Path
import os
import zipfile
import xmltodict
import json
import time

from django.contrib.gis.geos import Point, GeometryCollection
from django.conf import settings


class Petrol:
	def __init__(self):
		self.data_download_url = "https://donnees.roulez-eco.fr/opendata/instantane"
		self.static_path = settings.MEDIA_ROOT + '/data/'

	def download_petrol_data(self, requests_url, static_url, filename, chunk_size=128):
		r = requests.get(requests_url, stream=True)
		with open(static_url + filename, 'wb+') as fd:
			for chunk in r.iter_content(chunk_size=chunk_size):
				fd.write(chunk)

	def extract_zip(self, static_url, filename):
		with zipfile.ZipFile(static_url + filename,"r") as zip_ref:
			zip_ref.extractall(static_url)

	def xml_to_json(self, static_url, xml_name):
		with open(static_url + xml_name + '.xml', 'rb') as fd:
			doc = xmltodict.parse(fd.read())

		with open(self.static_path+'data.json', 'w', encoding='utf-8') as f:
			#json.dump(doc, f, ensure_ascii=False, indent=4)
			geo_json = {
							"type": "FeatureCollection",
							"features": []
						}


			for pdv in doc.get('pdv_liste').get('pdv'):

				geo_json['features'].append(
							{
								"type": "Feature",
								"properties": {
									"id":  pdv.get('@id'),
									"cp": pdv.get('@cp'),
									"pop": pdv.get('@pop'),
									"adresse": pdv.get('adresse'),
									"ville": pdv.get('ville'),
									"services": pdv.get('services'),
									"prix": pdv.get('prix')
									},
								"geometry": {
									"type": "Point",
									"coordinates": [float(pdv.get('@longitude'))/100000,float(pdv.get('@latitude'))/100000]
								}
							}
				)
			
			json.dump(geo_json, f, ensure_ascii=False, indent=4)

	def create_petrol_data(self):
		now = time.time()
		if (not os.path.isfile(self.static_path + 'data.json')
			or os.path.getctime(self.static_path + 'data.json') < 24*3600):

			self.download_petrol_data(self.data_download_url, self.static_path, 'data.zip')
			self.extract_zip(self.static_path, 'data.zip')
			self.xml_to_json(self.static_path, 'PrixCarburants_instantane')

			os.remove(self.static_path + 'data.zip')
			os.remove(self.static_path + 'PrixCarburants_instantane.xml')

	def get_petrol_data(self):
		self.create_petrol_data()
		json_file = open(self.static_path + 'data.json')
		return json.load(json_file)



