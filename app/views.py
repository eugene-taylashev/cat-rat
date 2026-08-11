from django.http import HttpResponse                        #type: ignore
from django.shortcuts import render, get_object_or_404      #type: ignore
from django.contrib.auth.decorators import login_required   # type: ignore

@login_required
def app_index(request):
    #HttpResponse("<html><body><h1>This is Risk Assessment Tool</h1></body></html>")
    return render(request, "car/main.html")
    
