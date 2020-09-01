from django.shortcuts import render, redirect
from django.http import JsonResponse

from .utils import Petrol, OSM
p = Petrol()


def home(request):
    p.init_data()
    return render(request, 'map.html', locals())

def map(request):
    bbox = request.GET.get('in_bbox')
    json_data = p.get_petrol_data(bbox)
    return JsonResponse(json_data)

def stations(request):
    if request.GET.get('error') == 'zoom':
        return render(request, 'stations_table.html', {'error': True})

    bbox = request.GET.get('bbox')[:-1]
    petrol_type = request.GET.get('petrol_type')
    stations = p.sort_stations(bbox, petrol_type)
    return render(request, 'stations_table.html', {'stations':stations, 'len_stations':len(stations)})

def station_infos(request):
    station_id = request.GET.get('station_id')
    station_infos = p.get_station_infos(station_id)[0]
    len_services = None

    if station_infos['properties'].get('services'):
        len_services = len(station_infos['properties'].get('services'))

    return render(request, 'stations_modal.html', {'station_infos': station_infos, 'jours': ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'], 'len_services': len_services})


def force_update(request):
    p.force_update()
    return redirect('/')

def force_json_stations(request):
    osm = OSM()
    osm.start_OSM_json_creation()
    return redirect('/nada')


