from django.http import HttpResponseRedirect, HttpResponse              # type: ignore
from django.views.decorators.http import require_POST              # type: ignore
from django.views import View            # type: ignore
from django.views.generic import DeleteView                 # type: ignore
from django.urls import reverse_lazy        # type: ignore
from django.shortcuts import render, Http404, redirect, get_object_or_404    # type: ignore
from django.db.models import Count, Q       # type: ignore
from django.contrib.auth.decorators import login_required   # type: ignore


from .models import *
#from .forms import *

@login_required
#==============================================================================
def main(request):
    return render(request, "car/main.html")


#==============================================================================
def build_asset_tree(user,parent=None, level=0):
    '''
    prepare list of Assets in hierarchical order    '''
    rows = []

    assets = Asset.objects.filter(owner__users=user,parent=parent).order_by("name")

    for asset in assets:
        asset.level = level          # for indentation
        asset.indent = asset.level * 30
        rows.append(asset)

        rows.extend(build_asset_tree(user,asset, level + 1))

    return rows


#==============================================================================
def asset_list(request):
    '''
    Display list of assets specific for the user, who requested
        input: request
        output: rendered HTML page
    '''
    asset_list = build_asset_tree(request.user)
    context = {"asset_list": asset_list, "ptitle": "Your assets"}
    return render(request, "car/asset_list.html", context)

