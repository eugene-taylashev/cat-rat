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
    Dashboard for a user with the concept:
    Show me everything that belongs to my Owner groups and requires my attention.
        input: request
        output: rendered HTML page
    '''
    owners = Owner.objects.filter( ownermembership__user=request.user ).distinct()

    assets = Asset.objects.filter( owner__in=owners )
    controls = Control.objects.filter( owner__in=owners ) 
    risks = Risk.objects.filter( owner__in=owners )
    actions = Action.objects.filter( owner__in=owners )

    action_status = (
        actions.values("status")
        .annotate(total=Count("id"))
        .order_by("status")
    )

    context = {
        "owners": owners,

        "asset_count": assets.count(),
        "control_count": controls.count(),
        "risk_count": risks.count(),

        "action_count": actions.count(),

        "planned_actions":
            actions.filter(
                status=ActionStatus.PLANNED
            ).count(),

        "in_progress_actions":
            actions.filter(
                status=ActionStatus.IN_PROGRESS
            ).count(),

        "completed_actions":
            actions.filter(
                status=ActionStatus.COMPLETED
            ).count(),

        #"overdue_actions":
        #    sum(
        #        1 for a in actions
        #        if a.is_overdue()
        #    ),

        "recent_actions":
            actions.order_by(
                "-updated_at"
            )[:10],

        "high_risks":
            risks.filter(
                residual_level__gte=3
            ).order_by(
                "-residual_level"
            )[:10],

        "action_status": list(action_status),
    }

    return render(request, "car/main.html", context,)




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
    logger.debug(
        "owner_edit: request=%s method=%s pk=%s user=%s",
        request, request.method, pk, request.user, )

    is_new = pk == 0
    if is_new:
    # ---------------------------------------------------------
    # CREATE new Owner
    # ---------------------------------------------------------
        owner = Owner()
        logger.debug("owner_edit: creating new owner by %s", request.user)

    else:
    # ---------------------------------------------------------
    # EDIT existing Owner
    # ---------------------------------------------------------
        owner = get_object_or_404(Owner, pk=pk)
        logger.debug( "owner_edit: found object for owner pk=%s", owner.pk)

    if request.method == "POST":
    # ---------------------------------------------------------
    # POST
    # ---------------------------------------------------------
        logger.debug( "POST data: %s", request.POST )

        form = OwnerForm(request.POST, instance=owner)
        # For both new and existing Owner
        formset = OwnerMembershipFormSet(request.POST,instance=owner)
        logger.debug("owner_edit: updating owner pk=%s by %s", owner.pk, request.user)

        if form.is_valid() and formset.is_valid():
            logger.debug( "OwnerForm and OwnerMembershipFormSet valid. OwnerForm.cleaned_data=%s\nOwnerMembershipFormSet.cleaned_data=%s", form.cleaned_data, formset.cleaned_data, )

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
                request, "Owner created successfully."
                if is_new
                else "Owner updated successfully."
            )

            #return redirect("owner_edit",pk=owner.pk)
            return HttpResponseRedirect( f"/car/owner/", preserve_request=False)

        else:
            logger.error( "OwnerForm or OwnerMembershipFormSet validation failed")
            logger.error( "Form errors: %s", form.errors)
            logger.error( "Form errors as JSON: %s", form.errors.as_json() )
            logger.error( "Non-field errors: %s", form.non_field_errors())
            logger.error( "FormSet errors: %s", formset.errors)
            logger.error( "FormSet errors as JSON: %s", formset.errors.as_json() )
            logger.error( "Non-field errors: %s", formset.non_field_errors())


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
    View/edit one asset by PK or create new with pk=0
        input: request, primary_key
        output: rendered HTML page
    '''
    logger.debug(
        "asset_edit: request=%s method=%s pk=%s user=%s",
        request, request.method, pk, request.user, )

    is_new = pk == 0

    if is_new:
    # ---------------------------------------------------------
    # CREATE new Asset
    # ---------------------------------------------------------
        asset = Asset()
        #ownermembership__is_primary=True,
        asset.owner = Owner.objects.filter(
            ownermembership__user=request.user,
            ).first()
        logger.debug("asset_edit: creating new asset by %s", request.user)

    else:
    # ---------------------------------------------------------
    # EDIT existing Asset
    # ---------------------------------------------------------
        asset = get_object_or_404(Asset, pk=pk)
        logger.debug( "asset_edit: found object for asset pk=%s", asset.pk)
        #can_edit = can_edit_asset(request.user, asset)

    if request.method == 'POST':
    # ---------------------------------------------------------
    # POST
    # ---------------------------------------------------------
        logger.debug( "POST data: %s", request.POST )
        
        form = AssetForm(request.POST, instance=asset)
        logger.debug("asset_edit: updating asset pk=%s by %s", asset.pk, request.user)

        if form.is_valid():
            logger.debug( "AssetForm valid. cleaned_data=%s", form.cleaned_data )
            asset.save(user=request.user)  # Saves to the Asset model
            logger.debug( "Asset saved: %s", asset )

            messages.success(
                request, "Asset created successfully."
                if is_new
                else "Asset updated successfully."
            )

            return HttpResponseRedirect( f"/car/asset/", preserve_request=False)

        else:
            logger.error( "AssetForm validation failed")
            logger.error( "Form errors: %s", form.errors)
            logger.error( "Form errors as JSON: %s", form.errors.as_json() )
            logger.error( "Non-field errors: %s", form.non_field_errors())

    else:
    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------
        form = AssetForm(instance=asset)

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
def control_detail(request, pk):
    '''
    View/edit one control by ID/pk or create new with pk=0
        input: request, primary_key
        output: rendered HTML page
    '''
    logger.debug(
        "control_detail: request=%s method=%s pk=%s user=%s",
        request, request.method, pk, request.user, )

    settings = AppSettings.get()        #-- Get App settings
    control = get_object_or_404(Control, pk=pk)
    
    tab = request.GET.get("tab", "overview")

    allowed_tabs = {
        "overview": "car/parts/control_tab_overview.html",
        "maturity": "car/parts/control_tab_maturity.html",
        "testing": "car/parts/control_tab_testing.html",
        "assessments": "car/parts/control_tab_assessments.html",
        "history": "car/parts/control_tab_history.html",
    }

    template = allowed_tabs.get(tab)

    if template is None:
        tab = "overview"
        template = allowed_tabs[tab]

    logger.debug(
        "control_detail: tab to show=%s; %s",
        tab, template)

    context = {"control": control, "settings": settings, "tab": tab,}
    
    if request.headers.get("HX-Request"):
        return render(request, template, context)

    return render(request, "car/control_detail.html", context)



#==============================================================================
def control_edit(request, pk=0):
    '''
    View/edit one control by ID/pk or create new with pk=0
        input: request, primary_key
        output: rendered HTML page
    '''
    logger.debug(
        "control_edit: request=%s method=%s pk=%s user=%s",
        request, request.method, pk, request.user, )

    settings = AppSettings.get()        #-- Get App settings

    is_new = pk == 0

    if is_new:
    # ---------------------------------------------------------
    # CREATE new Control
    # ---------------------------------------------------------
        control = Control()
        control.owner = Owner.objects.filter(
            ownermembership__user=request.user,
            ).first()
        logger.debug("control_edit: creating new control by %s", request.user)

    else:
    # ---------------------------------------------------------
    # EDIT existing Control
    # ---------------------------------------------------------
        control = get_object_or_404(Control, pk=pk)
        logger.debug( "control_edit: found object for control pk=%s", control.pk)

    if request.method == 'POST':
    # ---------------------------------------------------------
    # POST
    # ---------------------------------------------------------
        logger.debug( "POST data: %s", request.POST )
        
        form = ControlForm(request.POST, instance=control, user=request.user)

        if form.is_valid():
            logger.debug( "ControlForm valid. cleaned_data=%s", form.cleaned_data )

            control.save(user=request.user)  # Saves to the Control model
            logger.debug( "Control saved: %s", control )

            messages.success(
                request, "Control created successfully."
                if is_new
                else "Control updated successfully."
            )

            return HttpResponseRedirect( f"/car/control/", preserve_request=False)

        else:
            logger.error( "ControlForm validation failed")
            logger.error( "Form errors: %s", form.errors)
            logger.error( "Form errors as JSON: %s", form.errors.as_json() )
            logger.error( "Non-field errors: %s", form.non_field_errors())

    else:
    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------
        form = ControlForm(instance=control, user=request.user)

    context = {"control": control, "form": form, "settings": settings}
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
        input: request, primary_key
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


#==============================================================================
@login_required
def risk_list(request):
    '''
    Display list of risks specific for the user, who requested
        input: request
        output: rendered HTML page
    '''
    risk_list = Risk.objects.filter(owner__users=request.user).order_by("risk_code")
    logger.debug("risk_list: accessing by %s", request.user)
    context = {"risk_list": risk_list, "ptitle": "Your risks"}
    return render(request, "car/risk_list.html", context)


#==============================================================================
def risk_edit(request, pk=0):
    '''
    View/edit one risk by PK or create new with pk=0
        input: request, primary_key
        output: rendered HTML page
    '''

    logger.debug(
        "risk_edit: request=%s method=%s pk=%s user=%s",
        request, request.method, pk, request.user, )

    is_new = pk == 0

    if is_new:
    # ---------------------------------------------------------
    # CREATE new Risk
    # ---------------------------------------------------------
        risk = Risk()
        risk.owner = Owner.objects.filter(
            ownermembership__user=request.user,
            ).first()

    else:
    # ---------------------------------------------------------
    # EDIT existing Risk
    # ---------------------------------------------------------
        risk = get_object_or_404( Risk, pk=pk )
        logger.debug( "risk_edit: found object for risk pk=%s", risk.pk)

    if request.method == "POST":
    # ---------------------------------------------------------
    # POST
    # ---------------------------------------------------------

        logger.debug( "POST data: %s", request.POST )
        form = RiskForm( request.POST, instance=risk )

        if form.is_valid():

            logger.debug( "RiskForm valid. cleaned_data=%s", form.cleaned_data )
            with transaction.atomic():

                risk = form.save( commit=False )

                logger.debug( "Risk before save: %s", risk )
                # Our TimestampedModel requires User
                risk.save( user=request.user )
                logger.info( "Risk saved: pk=%s", risk.pk )

                # Important because controls is ManyToMany
                form.save_m2m()

            messages.success(
                request, "Risk created successfully."
                if is_new
                else "Risk updated successfully."
            )

            return HttpResponseRedirect( f"/car/risk/", preserve_request=False)

        else:
            logger.error( "RiskForm validation failed")
            logger.error( "Form errors: %s", form.errors)
            logger.error( "Form errors as JSON: %s", form.errors.as_json() )
            logger.error( "Non-field errors: %s", form.non_field_errors())

    else:
    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------
        form = RiskForm( instance=risk )

    context = {"risk": risk, "form": form, "is_new": is_new,}
    return render(request, "car/risk_edit.html", context)


#==============================================================================
@require_POST  # ensures it only deletes via POST (for safety)
def risk_delete(request, pk):
    '''
    Delete a risk and redirect to list of risks
        input: request, risk_id
        output: redirect to risk list
    '''
    if request.method != "POST":
        return HttpResponse(
            "Method Not Allowed",
            status=405,
        )
    risk = get_object_or_404(Risk, pk=pk)
    risk.delete()
    return redirect('risk_list')  


#==============================================================================
@login_required
def action_edit(request, pk=0):
    '''
    View/edit one action by PK or create new with pk=0
        input: request, primary_key
        output: rendered HTML page
    '''

    logger.debug(
        "action_edit: request=%s method=%s pk=%s user=%s",
        request, request.method, pk, request.user, )
    
    is_new = pk == 0

    if is_new:
    # ---------------------------------------------------------
    # CREATE new Action
    # ---------------------------------------------------------
        action = Action()
        action.owner = Owner.objects.filter(
            ownermembership__user=request.user,
            ).first()
    else:
    # ---------------------------------------------------------
    # EDIT existing Action
    # ---------------------------------------------------------
        action = get_object_or_404( Action, pk=pk )
        logger.debug( "action_edit: found object for action pk=%s", action.pk)

    if request.method == "POST":
    # ---------------------------------------------------------
    # POST
    # ---------------------------------------------------------

        logger.debug( "POST data: %s", request.POST )
        form = ActionForm( request.POST, instance=action, )

        valid = form.is_valid()

        logger.debug(
            "form.is_valid() returned: %s",
            valid
        )

        if form.is_valid():

            logger.debug( "ActionForm valid. cleaned_data=%s", form.cleaned_data )

            with transaction.atomic():

                action = form.save( commit=False )
                logger.debug( "Action before save: %s", action )

                # Make absolutely sure a new action starts as PLANNED
                if action.pk is None:
                    action.status = ActionStatus.PLANNED

                action.save( user=request.user )
                logger.info( "Action saved: pk=%s", action.pk )

            messages.success( request, "Action created successfully."
                if is_new
                else "Action updated successfully."
            )

            #return redirect( "action_detail", pk=action.pk )
            return HttpResponseRedirect( f"/car/actions/", preserve_request=False)

        else:
            logger.error( "ActionForm validation failed")
            logger.error( "Form errors: %s", form.errors)
            logger.error( "Form errors as JSON: %s", form.errors.as_json() )
            logger.error( "Non-field errors: %s", form.non_field_errors())

    else:
    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------
        form = ActionForm( instance=action )

    context = {"action": action, "form": form, "is_new": is_new,}
    return render(request, "car/action_edit.html", context)


#==============================================================================
@login_required
def action_detail(request, pk):

    action = get_object_or_404(
        Action.objects.select_related(
            "owner",
            "completed_by",
        ),
        pk=pk
    )

    return render(
        request,
        "car/action_detail.html",
        {
            "action": action,
        }
    )    

#==============================================================================
@login_required
def action_list(request):

    actions = (
        Action.objects
        .select_related(
            "owner",
            "completed_by",
        )
        .order_by(
            "status",
            "due_date",
            "priority",
            "title",
        )
    )

    return render(
        request,
        "car/action_list.html",
        {
            "actions": actions,
        }
    )


#==============================================================================
@login_required
@require_POST
def action_start(request, pk):

    action = get_object_or_404(
        Action,
        pk=pk
    )

    if action.status == ActionStatus.PLANNED:

        action.start(
            user=request.user
        )

        messages.success(
            request,
            f"Action {action.action_code} started."
        )

    return redirect(
        "action_detail",
        pk=action.pk
    )


#==============================================================================
@login_required
@require_POST
def action_complete(request, pk):

    action = get_object_or_404(
        Action,
        pk=pk
    )

    if action.status != ActionStatus.COMPLETED:

        action.mark_done(
            user=request.user
        )

        messages.success(
            request,
            f"Action {action.action_code} completed."
        )

    return redirect(
        "action_detail",
        pk=action.pk
    )

#==============================================================================
@login_required
@require_POST
def action_reopen(request, pk):

    action = get_object_or_404(
        Action,
        pk=pk
    )

    if action.status == ActionStatus.COMPLETED:

        action.reopen(
            user=request.user
        )

        messages.success(
            request,
            f"Action {action.action_code} reopened."
        )

    return redirect(
        "action_detail",
        pk=action.pk
    )

@login_required
#==============================================================================
def dashboard(request):
    '''
    Dashboard with all KPIs for overall review:
        Risks
            Total Risks
            Open Risks
            High Risks
            Critical Risks
            Risks Reviewed This Year
            Overdue Reviews
        Actions
            Open Actions
            In Progress Actions
            Overdue Actions
            Completed Actions
        Assessments
            Planned Assessments
            In Progress Assessments
            Completed Assessments
            Completion %
        Controls
            Total Controls
            Active Controls
            Controls Without Owner
            Controls Not Assessed    

        input: request
        output: rendered HTML page
    '''

    #owners = Owner.objects.filter( ownermembership__user=request.user ).distinct()
    risks = Risk.objects      # .filter(owner__in=owners)
    actions = Action.objects  #.filter(owner__in=owners)

    #-- Risk KPIs
    total_risks = risks.count()
    high_risks = risks.filter(residual_level=RiskLevel.HIGH).count()
    critical_risks = risks.filter(residual_level=RiskLevel.CRITICAL).count()

    #-- Action KPIs
    open_actions = actions.exclude(status=ActionStatus.COMPLETED).count()
    completed_actions = actions.filter(status=ActionStatus.COMPLETED).count()
    #overdue_actions = sum(1 for a in actions if a.is_overdue())

    #-- Risk distribution chart
    risk_chart = {
        "Low": risks.filter(residual_level=RiskLevel.LOW).count(),
        "Medium": risks.filter(residual_level=RiskLevel.MEDIUM).count(),
        "High": risks.filter(residual_level=RiskLevel.HIGH).count(),
        "Critical": risks.filter(residual_level=RiskLevel.CRITICAL).count(),
    }

    #-- Acion status chart
    action_chart = {
        "Planned": actions.filter(status="planned").count(),
        "In_Progress": actions.filter(status="in_progress").count(),
        "Completed": actions.filter(status="completed").count(),
        "Cancelled": actions.filter(status="cancelled").count(),
    }    

    #=== Risk Heat Map
    risk_map = Risk.objects.filter(
        residual_likelihood__isnull=False,
        residual_impact__isnull=False,
    )

    # Create empty 5x5 matrix
    matrix = []
    
    for impact in range(5, 0, -1):
        row = []

        for likelihood in range(1, 6):

            score = likelihood * impact

            if score <= 4:
                level = "Low"
                css_class = "risk-low"

            elif score <= 9:
                level = "Medium"
                css_class = "risk-medium"

            elif score <= 16:
                level = "High"
                css_class = "risk-high"

            else:
                level = "Critical"
                css_class = "risk-critical"

            cell_risks = risk_map.filter(
                residual_likelihood=likelihood,
                residual_impact=impact,
            )

            row.append({
                "likelihood": likelihood,
                "impact": impact,
                "score": score,
                "level": level,
                "css_class": css_class,
                "risks": cell_risks,
                "count": cell_risks.count(),
            })

        matrix.append({
            "impact": ImpactLevel(impact).label,
            "cells": row,
        })
    
    context = {
        "total_risks": total_risks,
        "high_risks": high_risks,
        "critical_risks": critical_risks,

        "open_actions": open_actions,
        "completed_actions": completed_actions,
        #"overdue_actions": overdue_actions,

        "risk_chart": risk_chart,
        "action_chart": action_chart,

        "matrix": matrix,
        "risk_count": risk_map.count(),
        "likelihood": LikelihoodLevel.choices,
    }

    return render(request,"car/dashboard.html",context,)    