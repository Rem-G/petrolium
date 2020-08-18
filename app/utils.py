import requests
from pathlib import Path
import os
import zipfile
import xmltodict
import json
import time
from pyproj import Proj, transform


from django.contrib.gis.geos import Point, GeometryCollection
from django.conf import settings


class Petrol:
	def __init__(self):
		self.data_download_url = "https://donnees.roulez-eco.fr/opendata/instantane"
		self.static_path = settings.MEDIA_ROOT + '/data/'
		self.create_petrol_data()
		self.geojson_data = self.xml_to_json(self.static_path, 'PrixCarburants_instantane')
		self.petrol_type = None

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

		geo_json = {
						"type": "FeatureCollection",
						"features": []
					}

		for pdv in doc.get('pdv_liste').get('pdv'):
			horaires = pdv.get('horaires')
			automate = None
			if horaires:
				automate = horaires.get('@automate-24-24')

			ville = pdv.get('ville')
			if ville is None:
				ville = ""
			else:
				ville = ville.upper()

			geo_json['features'].append(
						{
							"type": "Feature",
							"properties": {
								"id":  pdv.get('@id'),
								"cp": pdv.get('@cp'),
								"pop": pdv.get('@pop'),
								"adresse": pdv.get('adresse'),
								"ville": ville,
								"automate": automate,
								"horaires": pdv.get('horaires'),
								"services": pdv.get('services'),
								"prix": pdv.get('prix')
								},
							"geometry": {
								"type": "Point",
								"coordinates": [float(pdv.get('@longitude'))/100000,float(pdv.get('@latitude'))/100000]
							}
						}
			)
		
		return geo_json

	def create_petrol_data(self):
		now = time.time()
		if (not os.path.isfile(self.static_path + 'PrixCarburants_instantane.xml')
			or os.path.getctime(self.static_path + 'PrixCarburants_instantane.xml') < 24*3600):

			self.download_petrol_data(self.data_download_url, self.static_path, 'data.zip')
			self.extract_zip(self.static_path, 'data.zip')

			os.remove(self.static_path + 'data.zip')

	def get_petrol_data(self, bbox):
		bbox_list = [float(b) for b in bbox.split(',')]

		inProj = Proj('EPSG:3857')
		outProj = Proj('EPSG:4326')
		y1, x1 = transform(inProj,outProj, bbox_list[0], bbox_list[1])
		y2, x2 = transform(inProj,outProj, bbox_list[2], bbox_list[3])

		geo_json = {
						"type": "FeatureCollection",
						"features": []
					}

		for feature in self.geojson_data.get('features'):
			coor = feature['geometry']['coordinates']
			if (coor[0] > x1
				and coor[0] <= x2
				and coor[1] >= y1
				and coor[1] <= y2):

				geo_json['features'].append(feature)

		return geo_json

	def findPetrol(self, value):
		if isinstance(value['properties']['prix'], list):
			#print('\n', value['properties']['prix'], '\n\n', value['properties'])
			for prix in value['properties']['prix']:
				if prix.get('@nom') == self.petrol_type:
					return float(prix['@valeur'])
		else:
			if value['properties']['prix'].get('@nom') == self.petrol_type:
				return float(value['properties']['prix']['@valeur'])
		return float('nan')


	def sortStations(self, bbox, petrol_type):
		self.petrol_type = petrol_type

		stations_with_petrol = list()

		for station in self.get_petrol_data(bbox)['features']:
			if isinstance(station['properties']['prix'], list):
				for prix in station['properties']['prix']:
					if prix.get('@nom') == self.petrol_type:
						stations_with_petrol.append(station)
			else:#dict
				if prix.get('@nom') == self.petrol_type:
					station['properties']['prix'] = [station['properties']['prix']]
					stations_with_petrol.append(station)

		sortedStations = sorted(stations_with_petrol, key=self.findPetrol)
		nameStations = self.add_station_name(sortedStations)

		return sortedStations

	def add_station_name(self, stations):
		for i, station in enumerate(stations):
			lon, lat = station['geometry']['coordinates']
			url = 'https://nominatim.openstreetmap.org/search.php?type=fuel&q=fuel+near+[{},{}]&limit=1&format=jsonv2'.format(lat, lon)
			res = requests.get(url)
			res = res.json()[0]
			name = res['display_name'].split(',')[0]

			station['properties']['name'] = name
			station['properties']['img'] = 'independant'
			for word in name.lower().replace('é', 'e').split(" "):
				if word+'.png' in os.listdir(str(settings.BASE_DIR) + '/static/img/'):
					station['properties']['img'] = word

			stations[i] = station

		return stations


	def force_update(self):
		os.remove(self.static_path + 'PrixCarburants_instantane.xml')
		self.create_petrol_data()













