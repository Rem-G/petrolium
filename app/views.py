from django.shortcuts import render, redirect
from django.http import JsonResponse

from .utils import Petrol, OSM
p = Petrol()


def home(request):
    return render(request, 'map.html', locals())

def map(request):
    bbox = request.GET.get('in_bbox')
    json_data = p.get_petrol_data(bbox)
    return JsonResponse(json_data)

def station(request):
    if request.GET.get('error') == 'zoom':
        return render(request, 'stations_table.html', {'error': True})

    bbox = request.GET.get('bbox')[:-1]
    petrol_type = request.GET.get('petrol_type')
    stations = p.sort_stations(bbox, petrol_type)

    return render(request, 'stations_table.html', {'stations':stations, 'len_stations':len(stations)})

def force_update(request):
    p.force_update()
    return redirect('/')

def force_json_stations(request):
    osm = OSM()
    osm.start_OSM_json_creation()
    return redirect('/nada')


