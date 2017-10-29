"""
Views - should mostly be thin functions for formatting the input / output,
with actual business logic being performed in aam_interaction.py.
"""


from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout
from django.utils import timezone
from django.utils import encoding
import os
from models import Employee, Work, Submission, Project
import aam_interaction as aami
from view_helpers import admin_check

from django.conf import settings


__author__ = 'Fabian Svara'


@login_required
def home_view(request):
    """
    Returns active, completed work and available tasks to home view.

    Function receives a HttpRequest object which has the logged in user as
    attribute. Work objects of this user which are not final as well as the
    ones that are final are filtered out and collected. All active Tasks
    of the users task category are grouped.

    Parameters:
    ----------

    request: HttpRequest
    """

    employee = Employee.objects.get(user=request.user)

    active_work = aami.get_active_work(employee)
    completed_work = aami.get_completed_work(employee)
    available_tasks_by_cat, availabe_tasks = aami.get_available_tasks(employee)

    request.session['is_admin'] = admin_check(request.user)

    context = {'firstname': request.user.first_name,
               'employee': employee,
               'active_work': active_work,
               'available_tasks': available_tasks_by_cat,
               'completed_work': completed_work, }

    return render(request, 'knossos_aam_backend/home.html', context)


@login_required
def workdetails_view(request, work_id):
    w = get_object_or_404(Work, pk=work_id)
    submissions = w.submission_set.order_by('date')
    worktime_overview = aami.get_monthly_worktime_for_work(w)

    context = {'submissions': submissions,
               'work': w,
               'date': timezone.now(),
               'time_by_year': worktime_overview['by_month_totals'], }

    return render(request, 'knossos_aam_backend/workdetails.html', context)


@login_required
@user_passes_test(admin_check)
def reset_task_view(request):
    if not 'username' in request.POST:
        return render(request, 'knossos_aam_backend/reset_task.html', {})

    try:
        aami.reset_task(request.POST['task'], request.POST['username'])
        return render(
            request, 'knossos_aam_backend/reset_task_performed.html', {'success': True})
    except:
        return render(
            request, 'knossos_aam_backend/reset_task_performed.html', {'success': False})


@login_required
@user_passes_test(admin_check)
def cancel_task_view(request):
    if not 'username' in request.POST:
        return render(request, 'knossos_aam_backend/cancel_task.html', {})

    try:
        aami.cancel_task(request.POST['task'], request.POST['username'])
        return render(
            request, 'knossos_aam_backend/cancel_task_performed.html', {
                'success': True, 'reason': None})
    except Exception, e:
        return render(
            request, 'knossos_aam_backend/cancel_task_performed.html', {
                'success': False, 'reason': str(e)})


@login_required
def changetask_view(request):
    employee = Employee.objects.get(user=request.user)

    if 'reopen_work_id' in request.POST:
        aami.unfinalize_work(employee, request.POST['reopen_work_id'])

    elif 'delete_sub_id' in request.POST:
        sub = Submission.objects.get(pk=request.POST['delete_sub_id'])
        work = Work.objects.get(pk=sub.work_id)
        aami.delete_submission(sub)

        return HttpResponseRedirect(
            reverse('knossos_aam_backend:workdetails', args=(work.id, )))

    return HttpResponseRedirect(reverse('knossos_aam_backend:home'))


@login_required
def usertime_view(request):
    e = get_object_or_404(Employee, user=request.user)
    s = Submission.objects.filter(employee=e)
    worktime_overview = aami.get_monthly_worktime_for_submissions(s)

    context = {'employee': e,
               'totals': worktime_overview['by_month_totals'],
               'per_task': worktime_overview['by_month_per_task']}

    return render(request, 'knossos_aam_backend/usertime.html', context)


@login_required
@user_passes_test(admin_check)
def monthoverview_view(request, year, month):
    timeoverview_totals = {}
    timeoverview_details = {}

    for e in Employee.objects.all():
        timeoverview_totals[e] = {}
        timeoverview_details[e] = {}

        subs = Submission.objects.filter(
            employee=e,
            date__year=year,
            date__month=month, )

        worktime_overview = aami.get_monthly_worktime_for_submissions(subs)

        timeoverview_totals[e] = worktime_overview['by_month_totals']
        timeoverview_details[e] = worktime_overview['by_month_per_task']

    context = {'year': year,
               'month': month,
               'totals': timeoverview_totals,
               'per_task': timeoverview_details, }

    return render(request, 'knossos_aam_backend/monthoverview.html', context)


@login_required
@user_passes_test(admin_check)
def monthoverview_sort_by_project_view(request, year, month):
    timeoverview_project_totals = {}
    timeoverview_project_details = {}

    for p in Project.objects.all():
        timeoverview_employee_totals = {}
        timeoverview_employee_details = {}

        for e in p.employee_set.all():
            timeoverview_employee_totals[e] = {}
            timeoverview_employee_details[e] = {}

            subs = Submission.objects.filter(
                employee=e,
                date__year=year,
                date__month=month, )
 
            worktime_overview = aami.get_monthly_worktime_for_submissions(subs)

            timeoverview_employee_totals[e] = \
                worktime_overview['by_month_totals']
            timeoverview_employee_details[e] = \
                worktime_overview['by_month_per_task']

        timeoverview_project_totals[p] = timeoverview_employee_totals
        timeoverview_project_details[p] = timeoverview_employee_details

    context = {'year': year,
               'month': month,
               'totals': timeoverview_project_totals,
               'per_task': timeoverview_project_details, }

    return render(request, 'knossos_aam_backend/monthoverview_projects.html', context)


@login_required
@user_passes_test(admin_check)
def sort_by_project_view(request):
    """View to handle the sorting of displayed user data by project.

    Requests:
    ----------

    sort_by_project_month: form button in monthoverview.html
        returns year and month to monthoverview_sort_by_project_view

    sort_by_name_month: form button in monthoverview_projects.html
        returns year and month to monthoverview_view

    sort_by_projects_stats_month: form button in statistics.html
        returns year and month to statistics_sort_by_project_view

    sort_by_name_stats_month: form button in statistics_projects.html
        returns year and month to statistics_view

    """

    if 'sort_by_project_month' in request.POST:
        return HttpResponseRedirect(
            reverse('knossos_aam_backend:monthoverview_sort_by_project',
                    args=(request.POST['sort_by_project_year'],
                          request.POST['sort_by_project_month'], )))
    elif 'sort_by_name_month' in request.POST:
        return HttpResponseRedirect(
            reverse('knossos_aam_backend:monthoverview',
                    args=(request.POST['sort_by_name_year'],
                          request.POST['sort_by_name_month'], )))
    elif 'sort_by_project_stats_month' in request.POST:
        return HttpResponseRedirect(
            reverse('knossos_aam_backend:statistics_sort_by_project',
                    args=(request.POST['sort_by_project_stats_year'],
                          request.POST['sort_by_project_stats_month'], )))
    elif 'sort_by_name_stats_month' in request.POST:
        return HttpResponseRedirect(
            reverse('knossos_aam_backend:statistics',
                    args=(request.POST['sort_by_name_stats_year'],
                          request.POST['sort_by_name_stats_month'], )))


@login_required
@user_passes_test(admin_check)
def timeoverview_view(request):
    timeoverview_totals = {}
    timeoverview_details = {}

    for e in Employee.objects.all():
        timeoverview_totals[e] = {}
        timeoverview_details[e] = {}

        worktime_overview = aami.get_monthly_worktime_for_submissions(e.submission_set)

        timeoverview_totals[e] = worktime_overview['by_month_totals']
        timeoverview_details[e] = worktime_overview['by_month_per_task']

    context = {'totals': timeoverview_totals,
               'per_task': timeoverview_details, }

    return render(request, 'knossos_aam_backend/timeoverview.html', context)


@login_required
@user_passes_test(admin_check)
def timeoverview_sort_by_project_view(request):
    timeoverview_project_totals = {}
    timeoverview_project_details = {}

    for p in Project.objects.all():
        timeoverview_employee_totals = {}
        timeoverview_employee_details = {}

        for e in p.employee_set.all():
            timeoverview_employee_totals[e] = {}
            timeoverview_employee_details[e] = {}
 
            worktime_overview = aami.get_monthly_worktime_for_submissions(
                e.submission_set)

            timeoverview_employee_totals[e] = \
                worktime_overview['by_month_totals']
            timeoverview_employee_details[e] = \
                worktime_overview['by_month_per_task']

        timeoverview_project_totals[p] = timeoverview_employee_totals
        timeoverview_project_details[p] = timeoverview_employee_details

    context = {'totals': timeoverview_project_totals,
               'per_task': timeoverview_project_details}

    return render(request, 'knossos_aam_backend/timeoverview_projects.html', context)

@login_required
@user_passes_test(admin_check)
def employee_work_overview(request):
    emp_set = aami.get_employees_current_work()
    context = { "employees": emp_set,
                "projects": Project.objects.all() }
    return render(request, "knossos_aam_backend/employees_current_work_view.html", context)

@login_required
@user_passes_test(admin_check)
def employee_project_overview(request):
    projects ={}
    for proj in Project.objects.all():
        projects[proj] = aami.get_employee_infos_in_project(proj)
    context = { "projects": projects }
    return render(request, "knossos_aam_backend/employee_project_overview.html", context)

@login_required
def error_view(request, error_string):
    return render(request, 'knossos_aam_backend/error.html', {'error_string': error_string})


@login_required
def download_task_file_view(request, filename):
    # potential security flaw here: by providing a malicious filename to
    # download arbitrary files..
    path_to_file = settings.MEDIA_ROOT + '/task-files/{0}'.format(
        filename).rstrip('\n')

    with open(path_to_file, 'r') as f:
        task_file = f.read()

    response = HttpResponse(task_file, content_type='application/nml')
    response['Content-Length'] = os.path.getsize(path_to_file)
    response['Content-Disposition'] = 'attachment; filename=%s' \
                                      % encoding.smart_str(filename)

    return response

    # using apache modxsendfile seems to be the "better way" because the file doesn't need
    # to be read by django into memory first. But this requires apache setup
    #response = HttpResponse(mimetype='application/force-download')
    #response['Content-Disposition'] = 'attachment; filename=%s' % encoding.smart_str(filename)
    #response['X-Sendfile'] = encoding.smart_str(path_to_file)
    #return response


def logout_view(request):
    logout(request)

    return HttpResponseRedirect(reverse('knossos_aam_backend:login'))