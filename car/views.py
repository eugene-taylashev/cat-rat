from django.http import HttpResponseRedirect, HttpResponse              # type: ignore
from django.views.decorators.http import require_POST              # type: ignore
from django.views import View            # type: ignore
from django.views.generic import DeleteView                 # type: ignore
from django.urls import reverse_lazy        # type: ignore
from django.shortcuts import render, Http404, redirect, get_object_or_404    # type: ignore
from django.db.models import Count, Q       # type: ignore
from django.contrib.auth.decorators import login_required   # type: ignore


#from .models import *
#from .forms import *

@login_required
#==============================================================================
def index(request):
    return render(request, "car/main.html")


