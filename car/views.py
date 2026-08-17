from django.http import HttpResponseRedirect, HttpResponse              # type: ignore
from django.views.decorators.http import require_POST              # type: ignore
from django.shortcuts import render, Http404, redirect, get_object_or_404    # type: ignore
from django.db.models import Count, Q       # type: ignore
from django.contrib.auth.decorators import login_required   # type: ignore
from django.contrib import messages
from django.db import transaction
import logging


from .models import *
from .forms import *

logger = logging.getLogger(__name__)

@login_required
#==============================================================================
def main(request):
    '''
    Placeholder for the main page
        input: request
        output: rendered HTML page
    '''
    return render(request, "car/main.html")




#==============================================================================
def owner_list(request):
    '''
    Display list of owners specific for the user, who requested
        input: request
        output: rendered HTML page
    '''
    owner_list = Owner.objects.all()
    context = {"owner_list": owner_list, "ptitle": "Your owners"}
    logger.debug("owner_list: accessing by %s", request.user)
    return render(request, "car/owner_list.html", context)



#==============================================================================
def owner_edit(request, pk=0):
    '''
    View/edit one owner by ID/pk or create new with pk=0
        input: request, primary_key
        output: rendered HTML page
    '''

    is_new = pk == 0
    # ---------------------------------------------------------
    # CREATE new Owner
    # ---------------------------------------------------------
    if is_new:
        owner = Owner()
        logger.debug("owner_edit: creating new owner by %s", request.user)

    # ---------------------------------------------------------
    # EDIT existing Owner
    # ---------------------------------------------------------
    else:
        owner = get_object_or_404(Owner, pk=pk)

    # ---------------------------------------------------------
    # POST
    # ---------------------------------------------------------
    if request.method == "POST":
        form = OwnerForm(request.POST, instance=owner)
        # For both new and existing Owner
        formset = OwnerMembershipFormSet(request.POST,instance=owner)
        logger.debug("owner_edit: updating owner pk=%s by %s", owner.pk, request.user)

        if form.is_valid() and formset.is_valid():

            with transaction.atomic():

                # Save Owner first.
                # This creates the PK if this is a new Owner.
                owner = form.save(commit=False)

                owner.save(user=request.user)

                # Now owner.pk exists.
                formset.instance = owner

                # Save OwnerMembership records.
                formset.save()

            messages.success(
                request,
                "Owner saved successfully."
            )

            return redirect("owner_edit",pk=owner.pk)

        else:
            # Validation failed.
            # Do not redirect or recreate the forms.
            # Keep the submitted forms so their errors are displayed.
            pass

    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------
    else:

        form = OwnerForm(instance=owner)
        formset = OwnerMembershipFormSet(instance=owner)
        logger.debug("owner_edit: accessing owner pk=%s by %s", owner.pk, request.user)


    context = {"owner": owner, "form": form, "formset": formset, "is_new": is_new, "ptitle": "Owner: %s" % owner.name}
    return render(request, "car/owner_edit.html", context)


#==============================================================================
def build_asset_tree(user,parent=None, level=0):
    '''
    prepare list of Assets in hierarchical order    
    '''
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
    logger.debug("asset_list: accessing by %s", request.user)
    return render(request, "car/asset_list.html", context)


#==============================================================================
def asset_edit(request, pk=0):
    '''
    View/edit one asset by ID/pk or create new with pk=0
        input: request, primary_key
        output: rendered HTML page
    '''
    if pk == 0:
        asset = Asset()
        #ownermembership__is_primary=True,
        asset.owner = Owner.objects.filter(
            ownermembership__user=request.user,
            ).first()
        logger.debug("asset_edit: creating new asset by %s", request.user)
    else:
        asset = get_object_or_404(Asset, pk=pk)
        #can_edit = can_edit_asset(request.user, asset)

    if request.method == 'POST':
        form = AssetForm(request.POST, instance=asset)
        logger.debug("asset_edit: updating asset pk=%s by %s", asset.pk, request.user)
        if form.is_valid():
            asset.save(user=request.user)  # Saves to the Asset model
            return HttpResponseRedirect( f"/car/asset/", preserve_request=False)
    else:
        form = AssetForm(instance=asset)
        logger.debug("asset_edit: accessing asset pk=%s by %s", asset.pk, request.user)

    context = {"asset": asset, "form": form, "ptitle": "Asset: %s" % asset.name} #, "can_edit": can_edit
    return render(request, "car/asset_edit.html", context)


#==============================================================================
def control_list(request):
    '''
    Display list of controls specific for the user, who requested
        input: request
        output: rendered HTML page
    '''
    control_list = Control.objects.filter(owner__users=request.user).order_by("control_label")
    logger.debug("control_list: accessing by %s", request.user)
    context = {"control_list": control_list, "ptitle": "Your controls"}
    return render(request, "car/control_list.html", context)


#==============================================================================
def control_edit(request, pk=0):
    '''
    View/edit one control by ID/pk or create new with pk=0
        input: request, primary_key
        output: rendered HTML page
    '''
    if pk == 0:
        control = Control()
        #ownermembership__is_primary=True,
        control.owner = Owner.objects.filter(
            ownermembership__user=request.user,
            ).first()
        logger.debug("control_edit: creating new control by %s", request.user)
    else:
        control = get_object_or_404(Control, pk=pk)

    if request.method == 'POST':
        form = ControlForm(request.POST, instance=control, user=request.user)
        logger.debug("control_edit: updating control pk=%s by %s", control.pk, request.user)
        if form.is_valid():
            control.save(user=request.user)  # Saves to the Control model
            return HttpResponseRedirect( f"/car/control/", preserve_request=False)
    else:
        form = ControlForm(instance=control, user=request.user)
        logger.debug("control_edit: accessing control pk=%s by %s", control.pk, request.user)

    context = {"control": control, "form": form}
    return render(request, "car/control_edit.html", context)


#==============================================================================
def control_history(request, pk):
    '''
    View history of one control by ID/pk
        input: request, primary_key
        output: rendered HTML page
    '''
    control = get_object_or_404(Control, pk=pk)
    
    records = list(
        control.history
        .select_related("history_user")
        .order_by("-history_date")
    )

    logger.debug("control_history: accessing control history pk=%s by %s", control.pk, request.user)
    history_rows = []

    for index, record in enumerate(records):

        changes = []

        if index + 1 < len(records):
            previous = records[index + 1]

            delta = record.diff_against(previous)
            #print("DEBUG: delta|",delta)

            changes = delta.changes

        history_rows.append({
            "record": record,
            "changes": changes,
        })

    return render(
        request,
        "car/control_history.html",
        {
            "control": control,
            "history_rows": history_rows,
        },
    )


#==============================================================================
def control_delete(request, pk):
    '''
    Display confirmation modal to delete a control
        input: request, primary_key
        output: rendered HTML page
    '''
    control = get_object_or_404(Control, pk=pk)
    #control = Control.objects.annotate(
    #    activity_count=Count('activity')
    #    ).get(id=pk)
    return render(request, "car/parts/control_delite_modal.html", {"control": control})
    #return HttpResponseRedirect( f"/car/control/", preserve_request=False)


#==============================================================================
@require_POST  # ensures it only deletes via POST (for safety)
def control_delete_confirmed(request, pk):
    '''
    Delete a control and redirect to list of controls
        input: request, audit_id
        output: redirect to control list
    '''
    if request.method != "POST":
        return HttpResponse(
            "Method Not Allowed",
            status=405,
        )
    control = get_object_or_404(Control, pk=pk)
    control.delete()
    return redirect('control_list')  




    