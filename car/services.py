from django.http import HttpResponseRedirect, HttpResponse              # type: ignore
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404    # type: ignore
from django.db.models import Count, Q       # type: ignore
from django.contrib import messages
from django.db import transaction
from django.utils import timezone

from .models import *
from .forms import *

logger = logging.getLogger(__name__)

#==============================================================================
def user_in_group(user, group_name):
    '''
    Checks if user is member of group_name
    Usage: 
        @user_passes_test(
            lambda u: user_in_group(u, "Admin")
        )
    '''
    return user.groups.filter(name=group_name).exists()

#==============================================================================
@transaction.atomic
def initialize_assessment(assessment):
    logger.debug("initialize_assessment: identify proper type")

    if assessment.assessment_type == AssessmentType.RISK:
        return initialize_risk_assessment(assessment)

    if assessment.assessment_type == AssessmentType.CONTROL:
        return initialize_control_assessment(assessment)

    if assessment.assessment_type == AssessmentType.AUDIT:
        return initialize_control_audit(assessment)

    return 0

#==============================================================================
def initialize_risk_assessment(assessment):
    logger.debug("initialize_risk_assessment: start")

    items = assessment.items.count()

    if items > 0:
        logger.debug("initialize_risk_assessment: ERROR: Already %s items", items,)
        return 1
        
    risks = Risk.objects.exclude(status=RiskStatus.CLOSED)

    for risk in risks:

        item = AssessmentItem.objects.create(
            assessment=assessment,
            item_type=AssessmentItemType.RISK,
            risk=risk,
            owner=risk.owner,
            assigned_at=timezone.now(),
            status=AssessmentItemStatus.ASSIGNED,
        )

        RiskAssessment.objects.create(
            assessment_item=item,
            risk=risk,
            assessment_type=RiskAssessmentType.PERIODIC,
        )
    return 0

#==============================================================================
def initialize_control_assessment(assessment):
    '''
    Create AssessmentItem for all ACTIVE controls
    ToDo: Prevent re-creation of AssessmentItem for same control
    '''
    logger.debug("initialize_control_assessment: start")
    
    items = assessment.items.count()

    if items > 0:
        logger.debug("initialize_control_assessment: ERROR: Already %s items", items,)
        return 1
        
    controls = Control.objects.filter(status=ControlStatus.ACTIVE)
    for control in controls:
        
        logger.debug("initialize_control_assessment: %s", control,)

        item = AssessmentItem.objects.create(
            assessment=assessment,
            item_type=AssessmentItemType.CONTROL_MATURITY,
            control=control,
            owner=control.owner,
            assigned_at=timezone.now(),
            status=AssessmentItemStatus.ASSIGNED,
        )

        ControlMaturityAssessment.objects.create(
            assessment_item=item,
        )    

    return 0


#==============================================================================
def initialize_control_audit(assessment):
    logger.debug("initialize_control_audit: start")

    items = assessment.items.count()

    if items > 0:
        logger.debug("initialize_control_audit: ERROR: Already %s items", items,)
        return 1
        
    controls = Control.objects.filter(status=ControlStatus.ACTIVE)
    for control in controls:
        
        logger.debug("initialize_control_audit: %s", control,)

        item = AssessmentItem.objects.create(
            assessment=assessment,
            item_type=AssessmentItemType.CONTROL_TEST,
            control=control,
            owner=control.owner,
            assigned_at=timezone.now(),
            status=AssessmentItemStatus.ASSIGNED,
        )

        ControlTest.objects.create(
            assessment_item=item,
        )    

    return 0


#==============================================================================
def assessment_out_main(request, assessment, tab, template):
    '''
    Prepare data to output Scope tab for Assessment
    '''
    logger.debug("assessment_out_main: out for assessment.pk=%s", assessment.pk,)
    settings = AppSettings.get()        #-- Get App settings

    form = AssessmentForm(instance=assessment)

    #-- Record history shows who and when created/updated the record 
    rec_history = { 
        "created_by": assessment.created_by,
        "created_at": assessment.created_at,
        "updated_by": assessment.updated_by,
        "updated_at": assessment.updated_at,
    }

    if assessment.is_new:
        ptitle = "Edit new Assessment"
    else:
        ptitle = "Edit Assessment " + assessment.assessment_code

    context = {"assessment": assessment, "form": form, "tab": tab, "rec_history": 
        rec_history, "ptitle": ptitle, "settings": settings,  }
    
    if request.headers.get("HX-Request"):
        return render(request, template, context)

    return render(request, "car/assessment_edit.html", context)


#==============================================================================
def assessment_out_scope(request, assessment, tab, template):
    '''
    Prepare data to output Scope tab for Assessment
    '''
    logger.debug("assessment_out_scope: out for assessment.pk=%s", assessment.pk,)
    settings = AppSettings.get()        #-- Get App settings

    if assessment.assessment_type in [
        AssessmentType.CONTROL,
        AssessmentType.AUDIT,
    ]:
        scope = ( AssessmentControlScope.objects
            .filter(assessment=assessment)
            .first()
        )

        scope_form = AssessmentControlScopeForm( instance=scope, )
        total_items = Control.objects.filter(status=ControlStatus.ACTIVE).count()
        logger.debug("assessment_out_scope: scope CONTROL, total items %s", total_items)

    elif assessment.assessment_type == AssessmentType.RISK:
        scope = ( AssessmentRiskScope.objects
            .filter(assessment=assessment)
            .first()
        )

        scope_form = AssessmentRiskScopeForm( instance=scope, )
        total_items = Risk.objects.exclude(status=RiskStatus.CLOSED).count()
        logger.debug("assessment_out_scope: scope RISK, total items %s", total_items)

    else:
        scope_form = None
        logger.debug("assessment_out_scope: scope OTHER")

    #-- count number of scope items
    current_items = assessment.items.count()
    logger.debug("assessment_out_scope: total items=%s, current_items=%s", total_items, current_items, )

    #-- Format title
    if assessment.is_new:
        ptitle = "CAR: Define scope for new Assessment"
    else:
        ptitle = "CAR: Edit scope for Assessment " + assessment.assessment_code

    context = {"assessment": assessment, "scope_form": scope_form, 
        "current_items": current_items, "total_items": total_items,
        "tab": tab, "ptitle": ptitle, "settings": settings, }
    
    if request.headers.get("HX-Request"):
        return render(request, template, context)
    else:
        return redirect("car:assessment_edit",pk=assessment.pk)
        #url = reverse("car:assessment_edit",kwargs={"pk": assessment.pk},)
        #return redirect(f"{url}?tab={tab}")
        #return HttpResponseRedirect( f"{url}?tab={tab}", preserve_request=False)
    
    
#==============================================================================
def assessment_out_progress(request, assessment, tab, template):
    '''
    Prepare data to output Progress tab with AssessmentItems for Assessment
    '''
    logger.debug("assessment_out_progress: out for assessment.pk=%s", assessment.pk,)
    settings = AppSettings.get()        #-- Get App settings

    #-- AssessmentItems
    items = (
        assessment.items
        .select_related(
            "owner",
        )
        .order_by(
            "status",
            "owner__name",
        )
    )
    
    #-- Progress Summary / Chart
    total_items = items.count()

    progress_chart = {
        "Completed_Items": items.filter(status=AssessmentItemStatus.COMPLETED).count(),
        "In_Progress_Items": items.filter(status=AssessmentItemStatus.IN_PROGRESS).count(),
        "Not_Started_Items": items.filter(status=AssessmentItemStatus.NOT_STARTED).count(),
    }

    if assessment.is_new:
        ptitle = "Progress for new Assessment"
    else:
        ptitle = "Progress for Assessment " + assessment.assessment_code

    context = {"assessment": assessment, "items": items, "total_items": total_items, 
        "progress_chart": progress_chart, "tab": tab, "ptitle": ptitle, "settings": settings,  }
    
    if request.headers.get("HX-Request"):
        return render(request, template, context)
    else:
        return redirect("car:assessment_edit",pk=assessment.pk)


#==============================================================================
def assessment_out_history(request, assessment, tab, template):
    '''
    Prepare data to output History tab for Assessment
    '''
    logger.debug("assessment_out_history: out for assessment.pk=%s", assessment.pk,)
    settings = AppSettings.get()        #-- Get App settings

    records = list(
        assessment.history
        .select_related("history_user")
        .order_by("-history_date")
    )

    history_rows = []

    for index, record in enumerate(records):

        changes = []

        if index + 1 < len(records):
            previous = records[index + 1]

            delta = record.diff_against(previous)

            changes = delta.changes

        history_rows.append({
            "record": record,
            "changes": changes,
        })

    if assessment.is_new:
        ptitle = "CAR: Change history for new Assessment"
    else:
        ptitle = "CAR: Change history for Assessment " + assessment.assessment_code

    context = {"assessment": assessment, "history_rows": history_rows, "tab": tab, "ptitle": ptitle, "settings": settings,  }

    if request.headers.get("HX-Request"):
        return render(request, template, context)
    else:
        return redirect("car:assessment_edit",pk=assessment.pk)


#==============================================================================
def assess_risk_edit(request, item):

    logger.debug("assess_risk_edit: out for assessment_item.pk=%s", item.pk,)
    settings = AppSettings.get()        #-- Get App settings

    risk_assessment = get_object_or_404(
        RiskAssessment,
        assessment_item=item,
    )

    if request.method == "POST":
        form = RiskAssessmentForm(request.POST, instance=risk_assessment)

        if form.is_valid():
            form.save()

            item.status = AssessmentItemStatus.COMPLETED
            item.completed_at = timezone.now()
            item.save(update_fields=[
                "status",
                "completed_at",
            ])

            return redirect("car:assess_item_list")

    else:
        form = RiskAssessmentForm(instance=risk_assessment)
    
    ptitle = "Risk Assessment - assess_risk_edit"
    context = {"item": item, "risk_assessment": risk_assessment, "form": form, "ptitle": ptitle, "settings": settings,  }
    return render( request, "car/assess_risk_edit.html", context, )    


#==============================================================================
def assess_maturity_edit(request, item, status=''):

    logger.debug("assess_maturity_edit: out for assessment_item.pk=%s, status=%s", item.pk, status,)
    settings = AppSettings.get()        #-- Get App settings

    maturity = get_object_or_404(
        ControlMaturityAssessment,
        assessment_item=item,
    )

    if request.method == "POST":
        # ---------------------------------------------------------
        # POST
        # ---------------------------------------------------------
        logger.debug( "assess_maturity_edit: POST data is: %s", request.POST )

        form = ControlMaturityAssessmentForm(
            request.POST,
            instance=maturity,
        )

        # -------------------------------------
        # Validate
        # -------------------------------------
        if form.is_valid():
            logger.debug( "assess_maturity_edit: Form is valid. cleaned_data=%s", form.cleaned_data, )
            
            maturity = form.save(commit=False)
            maturity.assessment_item = item
            maturity.save()

            logger.debug( "assess_maturity_edit: Control maturity assessment saved successfully", )

            #-- Update status, if needed, from NOT_STARTED or ASSIGNED to IN_PROGRESS
            if status == "completed":
                item.status = AssessmentItemStatus.COMPLETED
                item.completed_at = timezone.now()
                item.completed_by = request.user
                item.save(update_fields=[
                    "status",
                    "completed_at",
                    "completed_by",
                ])
                logger.debug( "assess_maturity_edit: status COMPLETED updated successfully", )
                response = HttpResponse()
                response["HX-Redirect"] = reverse("car:assess_item_list")
                return response

            elif status == "not_applicable":
                item.status = AssessmentItemStatus.NOT_APPLICABLE
                item.completed_at = timezone.now()
                item.completed_by = request.user
                item.save(update_fields=[
                    "status",
                    "completed_at",
                    "completed_by",
                ])
                logger.debug( "assess_maturity_edit: status NOT_APPLICABLE updated successfully", )
                response = HttpResponse()
                response["HX-Redirect"] = reverse("car:assess_item_list")
                return response
            

            elif item.status in [
                AssessmentItemStatus.NOT_STARTED,
                AssessmentItemStatus.ASSIGNED,
            ]:
                item.status = AssessmentItemStatus.IN_PROGRESS
                item.save(update_fields=["status",])
                logger.debug( "assess_maturity_edit: AssessmentItem status updated successfully", )


            return redirect("car:assess_item_list")

        else:
            logger.error( "ControlMaturityAssessmentForm validation failed")
            logger.error( "Form errors: %s", form.errors)
            logger.error( "Form errors as JSON: %s", form.errors.as_json() )
            logger.error( "Non-field errors: %s", form.non_field_errors())
            return render(request, "car/error.html", {"error_message": f"Could not valideate the form: {form.errors}"},)
            messages.error(request,)

    else:
        form = ControlMaturityAssessmentForm(instance=maturity)

    ptitle = "Control Maturity Assessment"
    context = {"item": item, "maturity": maturity, "form": form, "ptitle": ptitle, "settings": settings,  }
    return render( request, "car/assess_control_maturity_edit.html", context, )    


#==============================================================================
def assess_control_test_edit(request, item):

    logger.debug("assess_control_test_edit: out for assessment_item.pk=%s", item.pk,)
    settings = AppSettings.get()        #-- Get App settings

    control_test = get_object_or_404(
        ControlTest,
        assessment_item=item,
    )

    if request.method == "POST":
        form = ControlTestForm(
            request.POST,
            instance=control_test,
        )

        if form.is_valid():
            control_test = form.save()

            item.status = AssessmentItemStatus.COMPLETED
            item.completed_at = timezone.now()
            item.save(update_fields=[
                "status",
                "completed_at",
            ])

            return redirect("car:assess_item_list")

    else:
        form = ControlTestForm(instance=control_test)

    ptitle = "Control Testing/Audit - assess_control_test_edit"
    context = {"item": item, "control_test": control_test, "form": form, "ptitle": ptitle, "settings": settings,  }
    return render( request, "car/assess_control_test_edit.html", context, )    

