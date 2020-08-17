from django.shortcuts import render
from django.http import JsonResponse


from .utils import Petrol

def home(request):
    return render(request, 'map.html', locals())

def map(request):
    p = Petrol()
    return JsonResponse(p.get_petrol_data())
