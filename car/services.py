from django.http import HttpResponseRedirect, HttpResponse              # type: ignore
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404    # type: ignore
from django.db.models import Count, Q       # type: ignore
from django.contrib import messages
from django.db import transaction

from .models import *
from .forms import *

logger = logging.getLogger(__name__)

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
        ptitle = "CAR: Create Assessment"
    else:
        ptitle = "CAR: Edit Assessment " + assessment.assessment_code

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
        ptitle = "CAR: Progress for new Assessment"
    else:
        ptitle = "CAR: Progress for Assessment " + assessment.assessment_code

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


    