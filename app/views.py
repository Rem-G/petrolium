from django.shortcuts import render
from django.http import JsonResponse

from .utils import Petrol
p = Petrol()


def home(request):
    return render(request, 'map.html', locals())

def map(request):
    bbox = request.GET.get('in_bbox')
    return JsonResponse(p.get_petrol_data(bbox))

def station(request):
    bbox = request.GET.get('bbox')[:-1]
    petrol_type = request.GET.get('petrol_type')

    return JsonResponse(p.sortStations(bbox, petrol_type))


