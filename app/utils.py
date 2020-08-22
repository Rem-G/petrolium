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

class Petrol():
	def __init__(self):
		self.data_download_url = "https://donnees.roulez-eco.fr/opendata/instantane"
		self.static_path = settings.MEDIA_ROOT + '/data/'
		self.petrol_type = None
		self.create_petrol_data()
		with open(self.static_path + 'PrixCarburants_instantane' + '.xml', 'rb') as fd:
			self.stations_data = xmltodict.parse(fd.read())

		with open(self.static_path+'osm_stations.json', 'r') as f:
			self.osm_data = json.loads(f.read())

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

	
	def create_horaires(self, horaires_pdv):
		jours = {'0': 'lundi', '1': 'mardi', '2': 'mercredi', '3': 'jeudi', '4': 'vendredi', '5': 'samedi', '6': 'dimanche'}
		horaires = {}
		for key, value in jours.items():
			current_day = horaires_pdv.get('jour')[int(key)]
			if current_day.get('horaire'):
				horaires[value+'-ferme'] = False

				if isinstance(current_day.get('horaire'), list):
					ouverture = list()
					fermeture = list()
					for period in current_day.get('horaire'):
						ouverture.append(period.get('@ouverture'))
						fermeture.append(period.get('@fermeture'))

					horaires[value+'-ouverture'] = ' '.join(ouverture)
					horaires[value+'-fermeture'] = ' '.join(fermeture)

				else:
					horaires[value+'-ouverture'] = current_day.get('horaire').get('@ouverture')
					horaires[value+'-fermeture'] = current_day.get('horaire').get('@fermeture')


			elif current_day.get('@ferme') == '1':
				horaires[value+'-ferme'] = True

		return horaires


	def xml_to_json(self):
		"""
			Convert xml to json
			Create the geojson
		"""
		geo_json = {
						"type": "FeatureCollection",
						"features": []
					}

		for pdv in self.stations_data.get('pdv_liste').get('pdv'):
			horaires_pdv = pdv.get('horaires')

			if horaires_pdv:
				automate = False
				if horaires_pdv.get('@automate-24-24') == '1':
					automate = True

				horaires = self.create_horaires(horaires_pdv)

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
								"horaires": horaires,
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
			or os.path.getctime(self.static_path + 'PrixCarburants_instantane.xml') + 12*3600 < now):

			self.download_petrol_data(self.data_download_url, self.static_path, 'data.zip')
			self.extract_zip(self.static_path, 'data.zip')

			os.remove(self.static_path + 'data.zip')

	def add_stations_info(self, stations):
		"""
			Add name, isopened, OSM_coor of the station to data from its coordinates
		"""
		for i, temp_station in enumerate(stations):
			lon, lat = temp_station['geometry']['coordinates']
			station_info = self.osm_data['features'].get(str([lon, lat]))

			if not station_info:
				#There is an error in the json file
				station_info = OSM().get_station_info_OSM(lat, lon, temp_station['properties']['adresse'])

			temp_station['properties']['name'] = station_info.get('name')
			temp_station['geometry']['coordinates'] = station_info.get('OSM_coor')

			img = 'independant'
			station_name_as_list = temp_station['properties']['name'].lower().replace('é', 'e').replace('è', 'e').split(" ")

			for index, word in enumerate(station_name_as_list):
				if index < len(station_name_as_list)-1 and word+station_name_as_list[index+1]+'.png' in os.listdir(str(settings.BASE_DIR) + '/static/img/'):
					img = word+station_name_as_list[index+1]
				elif word+'.png' in os.listdir(str(settings.BASE_DIR) + '/static/img/'):
					img = word

			temp_station['properties'].update({'isopened': self.is_opened(temp_station)})#Add if the station is opened
			temp_station['properties'].update({'img': img})

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

		for feature in self.xml_to_json().get('features'):
			coor = feature['geometry']['coordinates']
			if (coor[0] > x1
				and coor[0] <= x2
				and coor[1] >= y1
				and coor[1] <= y2):

				geo_json['features'].append(feature)

		geo_json_name = self.add_stations_info(geo_json['features'])

		return geo_json


	def get_station_infos(self, station_id):
		return [station for station in self.xml_to_json().get('features') if station['properties'].get('id') == station_id]


	################SORT STATIONS###################
	################################################
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
	######################################################################################
	######################################################################################

	def is_opened(self, station):
		now = time.time()
		if station['properties'].get('automate') :
			return True
		return False


	def force_update(self):
		os.remove(self.static_path + 'PrixCarburants_instantane.xml')
		self.create_petrol_data()


class OSM(Petrol):
	def __init__(self):
		super().__init__()
		self.thread = threading.Thread(target=self.create_OSM_json, args=())

	def start_OSM_json_creation(self):
		self.thread.daemon = True
		self.thread.start()

	def create_OSM_json(self):
		"""
			Create stations_name.json file
			For each station nominatim finds the station name from its coordinates
			/!\Takes a while/!\
		"""
		data = {}
		features = {}

		geojson_data = self.xml_to_json()

		for i, station in enumerate(geojson_data.get('features')):
			lon, lat = station['geometry']['coordinates']
			adresse = station['properties']['adresse'] + ' ' + station['properties']['ville']
			pop = station['properties']['pop']

			station_info = self.get_station_info_OSM(lon, lat, adresse, pop)
			OSM_coor = [float(c) for c in station_info['OSM_coor']]

			features[str([lon, lat])] =  {'name': station_info['name'], 'OSM_coor': OSM_coor}

			print( i, '/', len(geojson_data.get('features')))
		
		data['features'] = features
		with open(self.static_path+'osm_stations.json', 'w+') as f:
			json.dump(data, f)


	def get_station_info_OSM(self, lon, lat, adresse, pop):
		"""
			Return station name from nominatim
		"""
		url = 'https://nominatim.openstreetmap.org/search.php?type=fuel&q=fuel+near+[{},{}]&limit=4&format=jsonv2'.format(lat, lon)
		res = requests.get(url).json()

		if len(res):
			OSM_pertinent_station = self.get_most_pertinent_OSM_station(res, adresse, pop)
			name = OSM_pertinent_station.get('OSM_name')
			coor = OSM_pertinent_station.get('OSM_coor')
		else:
			name = 'Station service'
			coor = [lon, lat]#initial coor

		return {'name': name, 'OSM_coor': coor}


	def get_most_pertinent_OSM_station(self, res, adresse, pop):
		"""
		"""
		matches = dict()
		loc = dict()
		adresse = adresse.replace(',', '').replace('é', 'e').replace('è', 'e').upper().split(" ")
		best_name = res[0]['display_name'].split(',')[0]
		best_coor = [res[0]['lon'], res[0]['lat']]
		best_match = 0

		for place in res:
			display_name = place['display_name'].replace(',', '').replace('é', 'e').replace('è', 'e').upper().split(" ")
			if pop.upper() == 'A' and 'A' in display_name:
				try:
					int(display_name[display_name.index('A')+1])
					A_number = display_name[display_name.index('A')+1]
					display_name[display_name.index('A')] = 'A' + A_number
					display_name.remove(A_number)
				except Exception as e:
					print(e)
					pass

			n_match = 0
			for element in adresse:
				if element in display_name:
					n_match += 1

			if n_match > best_match:
				best_name = place['display_name'].split(',')[0]
				best_coor = [place['lon'], place['lat']]
				best_match = n_match

		return {'OSM_name': best_name, 'OSM_coor': best_coor}










