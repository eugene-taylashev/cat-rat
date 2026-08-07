from django.http import HttpResponseRedirect, HttpResponse              # type: ignore
from django.views.decorators.http import require_POST              # type: ignore
from django.views import View            # type: ignore
from django.views.generic import DeleteView                 # type: ignore
from django.urls import reverse_lazy        # type: ignore
from django.shortcuts import render, Http404, redirect, get_object_or_404    # type: ignore
from django.db.models import Count, Q       # type: ignore
from django.contrib.auth.decorators import login_required   # type: ignore


from .models import *
from .forms import *

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
def can_edit_asset(user,control):
    '''
    Verify that user can edit the table (control)
        input: user, control object
        output: true/false
    '''
    return OwnerMembership.objects.filter(
        owner=control.owner,
        user=user,
        role__in=["OWNER", "MANAGER", "MEMBER"]
    ).exists()


#==============================================================================
def asset_list(request):
    '''
    Display list of assets specific for the user, who requested
        input: request
        output: rendered HTML page
    '''
    asset_list = build_asset_tree(request.user)
    can_edit = can_edit_asset(request.user, asset_list[0]) if asset_list else False
    context = {"asset_list": asset_list, "ptitle": "Your assets", "can_edit": can_edit}
    return render(request, "car/asset_list.html", context)


#==============================================================================
def asset_form(request, pk=0):
    '''
    View/edit one asset by ID/pk or create new with pk=0
        input: request, asset_id
        output: rendered HTML page
    '''
    if pk == 0:
        asset = Asset()
    else:
        asset = get_object_or_404(Asset, pk=pk)
        #can_edit = can_edit_asset(request.user, asset)

    if request.method == 'POST':
        form = AssetForm(request.POST, instance=asset)
        if form.is_valid():
            asset.save(user=request.user)  # Saves to the Asset model
            return HttpResponseRedirect( f"/car/asset/", preserve_request=False)
    else:
        form = AssetForm(instance=asset)
        context = {"asset": asset, "form": form, "ptitle": "Asset: %s" % asset.name} #, "can_edit": can_edit
        return render(request, "car/asset_form.html", context)

