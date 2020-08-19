import requests
from pathlib import Path
import os
import zipfile
import xmltodict
import json
import time
import threading
from pyproj import Proj, transform

from django.conf import settings


class Petrol:
	def __init__(self):
		self.data_download_url = "https://donnees.roulez-eco.fr/opendata/instantane"
		self.static_path = settings.MEDIA_ROOT + '/data/'
		self.geojson_data = None
		self.petrol_type = None
		self.create_petrol_data()
		if not self.geojson_data:
			self.geojson_data = self.xml_to_json(self.static_path, 'PrixCarburants_instantane')

		self.thread = threading.Thread(target=self.create_json_stations, args=())

	def download_petrol_data(self, requests_url, static_url, filename, chunk_size=128):
		"""
			Download data from donnees.roulez-eco.fr
		"""
		r = requests.get(requests_url, stream=True)
		with open(static_url + filename, 'wb+') as fd:
			for chunk in r.iter_content(chunk_size=chunk_size):
				fd.write(chunk)

	def extract_zip(self, static_url, filename):
		"""
			Extract downloaded zip
		"""
		with zipfile.ZipFile(static_url + filename,"r") as zip_ref:
			zip_ref.extractall(static_url)

	def xml_to_json(self, static_url, xml_name):
		"""
			Convert xml to json
			Create the geojson
		"""
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
		"""
			Download petrol data from donnees.roulez-eco.fr if the xml does not exists or is expired
		"""
		now = time.time()

		if (not os.path.isfile(self.static_path + 'PrixCarburants_instantane.xml')
			or os.path.getctime(self.static_path + 'PrixCarburants_instantane.xml') + 24*3600 < now):

			self.download_petrol_data(self.data_download_url, self.static_path, 'data.zip')
			self.extract_zip(self.static_path, 'data.zip')

			self.geojson_data = self.xml_to_json(self.static_path, 'PrixCarburants_instantane')

			os.remove(self.static_path + 'data.zip')

	def get_station_name_nominatim(self, lat, lon):
		"""
			Return station name from nominatim
		"""
		url = 'https://nominatim.openstreetmap.org/search.php?type=fuel&q=fuel+near+[{},{}]&limit=1&format=jsonv2'.format(lat, lon)
		res = requests.get(url).json()
		if len(res):
			name = res[0]['display_name'].split(',')[0]
		else:
			name='Station service'

		return name

	def create_json_stations(self):
		"""
			Create stations_name.json file
			For each station nominatim finds the station name from its coordinates
			/!\Takes a while/!\
		"""
		data = {'features': []}
		for i, station in enumerate(self.geojson_data.get('features')):
			lon, lat = station['geometry']['coordinates']
			name = self.get_station_name_nominatim(lat, lon)
			data['features'].append({'name': name, 'lon': lon, 'lat': lat})
			print(name, i, '/', len(self.geojson_data.get('features')))

		with open(self.static_path+'stations_name.json', 'w+') as f:
			json.dump(data, f)

	def get_station_name_json(self, json, lat, lon):
		"""
			Find the station name in stations_name.jsn from its coordinates
		"""
		return [obj['name'] for obj in json['features'] if obj['lat'] == lat and obj['lon'] == lon]

	def add_station_name_isopened(self, stations):
		"""
			Add the station name to data from its coordinates
		"""
		with open(self.static_path+'stations_name.json', 'r') as f:
			json_data = json.loads(f.read())
			for i, temp_station in enumerate(stations):
				lon, lat = temp_station['geometry']['coordinates']
				name = self.get_station_name_json(json_data, lat, lon)[0]

				if name:
					temp_station['properties']['name'] = name
				else:
					temp_station['properties']['name'] = self.get_station_name_nominatim(lat, lon)
					#There is an error in the json file
					self.thread.daemon = True
					self.thread.start()

				img = 'independant'

				for word in name.lower().replace('é', 'e').split(" "):
					if word+'.png' in os.listdir(str(settings.BASE_DIR) + '/static/img/'):
						img = word

				temp_station['properties']['img'] = img
				temp_station['properties']['isopened'] = self.is_opened(temp_station)#Add if the station is opened

				stations[i] = temp_station

		return stations

	def get_petrol_data(self, bbox):
		"""
			Bbox filter
			Return only the stations in the bbox
		"""
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

		geo_json_name = self.add_station_name_isopened(geo_json['features'])

		return geo_json

	def findPetrol(self, value):
		"""
			Key to sort petrol stations
		"""
		if isinstance(value['properties']['prix'], list):
			#print('\n', value['properties']['prix'], '\n\n', value['properties'])
			for prix in value['properties']['prix']:
				if prix is not None and prix.get('@nom') == self.petrol_type:
					return float(prix['@valeur'])
		else:
			if value['properties']['prix'].get('@nom') == self.petrol_type:
				return float(value['properties']['prix']['@valeur'])
		return float('nan')


	def sort_stations(self, bbox, petrol_type):
		"""
			Sort stations on petrol_type requested by the user
		"""
		self.petrol_type = petrol_type

		stations_with_petrol = list()

		for station in self.get_petrol_data(bbox)['features']:
			if isinstance(station['properties']['prix'], list):
				for prix in station['properties']['prix']:
					if prix is not None and prix.get('@nom') == self.petrol_type:
						stations_with_petrol.append(station)
			else:#dict
				if prix is not None and prix.get('@nom') == self.petrol_type:
					station['properties']['prix'] = [station['properties']['prix']]
					stations_with_petrol.append(station)

		sortedStations = sorted(stations_with_petrol, key=self.findPetrol)

		return sortedStations


	def is_opened(self, station):
		now = time.time()
		if station['properties'].get('automate') == '1':
			return True
		return False
		

	def force_update(self):
		os.remove(self.static_path + 'PrixCarburants_instantane.xml')
		self.create_petrol_data()













