"""
Views to be accessed through Knossi instead of the web frontend.
"""

from django.conf import settings

from django.http import HttpResponse
from django.http import JsonResponse
from django.contrib.auth import logout
from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import encoding
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import ensure_csrf_cookie
import xml.etree.ElementTree as et
from xml.parsers.expat import ExpatError
import os

from models import Employee
from models import Work

from base64 import b64encode

from aam_interaction import get_active_work
from aam_interaction import get_available_tasks
from aam_interaction import choose_task
from aam_interaction import submit

from view_helpers import ParseError
from view_helpers import InvalidSubmission
from view_helpers import login_required_403
from view_helpers import admin_check
import re
import json


__author__ = 'Fabian Svara'


@csrf_exempt
@ensure_csrf_cookie
def login_api_view(request):
    """
    POST to login
    """

    try:
        xml = et.fromstring(request.body)
    except ParseError:
        return HttpResponse("parseError. This was sent: " + str(request.body), status=400)
    name = xml.find("username")
    if name.text is None:
        return HttpResponse("Please enter a username.", status=400)
    passwd = xml.find("password")
    if passwd.text is None:
        return HttpResponse("Please enter a password.", status=400)

    user = authenticate(username=name.text, password=passwd.text)
    if user is None:
        return HttpResponse("Username and password did not match.", status=400)
    elif not user.is_active:
        return HttpResponse("Username and password did not match.", status=400)

    login(request, user)

    return HttpResponse('Logged in successfully', status=200)


@login_required_403
def logout_api_view(request):
    """
    GET to logout
    """

    logout(request)
    return HttpResponse("Logged out successfully", status=200)


@login_required_403
def session_api_view(request):
    """
    GET: Display current state, i.e. if there is an active task or not.
    Return json formatted reply.
    """

    if not request.user.is_authenticated():
        return HttpResponse("Please login.", status=400)

    emp = Employee.objects.get(user=request.user)
    user = emp.user

    pks = [x.pk for x in Work.objects.filter(employee=emp, is_final=False)]
    if len(pks) > 0:
        work = Work.objects.get(pk=min(pks))

        response = {
            'username': request.user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'task_name': work.task.name,
            'task_comment': work.task.comment.encode('utf-8'),
            'task_category_name': work.task.category.name,
            'task_category_description':
                work.task.category.description.encode('utf-8'),
        }
    else:
        response = {
            'username': request.user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }

    response_str = json.dumps(response, indent=4)

    return HttpResponse(
        response_str, content_type='application/json', status=200)


@login_required_403
def current_file_api_view(request):
    emp = Employee.objects.get(user=request.user)

    active_work = get_active_work(emp)
    if not active_work:
        return HttpResponse(
            "Please start a new task first.", status=400)

    work = active_work[0]
    if work.last_submission is None:
        # no submit yet. send the task file instead.
        filename = work.task.task_file.name
        path_to_file = work.task.task_file.path

        with open(path_to_file, 'r') as f:
            task_file = f.read()

        response = HttpResponse(task_file, content_type='application/nml')
        response['Content-Length'] = os.path.getsize(path_to_file)
        response['Content-Disposition'] = \
            'attachment; filename=%s; taskname=%s / %s;' % (
                encoding.smart_str(os.path.basename(filename)),
                work.task.category.name,
                work.task.name, )
    else:
        latest_submission = work.last_submission
        filename = latest_submission.datafile.name
        path_to_file = latest_submission.datafile.path
        with open(path_to_file, 'r') as f:
            task_file = f.read()

        response = HttpResponse(task_file, content_type='application/nml')
        response['Content-Length'] = os.path.getsize(path_to_file)
        response['Content-Disposition'] = \
            'attachment; filename=%s;' % (encoding.smart_str(
                os.path.basename(filename)), )

    return response


@login_required_403
def new_task_api_view(request):
    emp = Employee.objects.get(user=request.user)

    active_work = get_active_work(emp)

    if active_work:
        return HttpResponse(
            "Please finish your current task first.",
            status=400)

    available_tasks_by_cat, available_tasks = get_available_tasks(emp)

    if not available_tasks:
        return HttpResponse("No new tasks available at the moment.", status=400)

    task = available_tasks[0]
    choose_task(emp, task.pk)

    filename = task.task_file.name
    path_to_file = task.task_file.path

    with open(path_to_file, 'r') as f:
        task_file = f.read()

    response = HttpResponse(task_file, content_type='application/nml')
    response['Content-Length'] = os.path.getsize(path_to_file)
    response['Content-Disposition'] = (
        'attachment; filename=%s; taskname=%s / %s; description=%s; '
        'comment=%s;' % (encoding.smart_str(os.path.basename(filename)),
                         task.category.name,
                         task.name,
                         b64encode(task.category.description.encode('utf-8')),
                         b64encode(task.comment.encode('utf-8')), ))

    return response


@login_required_403
def submit_api_view(request):
    """
    POST: Submit a work result to currently active task
    """

    try:
        emp = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return HttpResponse(
            "Employee " + request.user.username + " could not be found",
            status=500)

    submitFile = request.FILES.get("submit_work_file", False)
    if not submitFile:
        return HttpResponse("No file uploaded.", status=400)

    comment = request.POST.get('submit_comment', '')

    if request.POST.get('submit_work_is_final', "False") == "True":
        final = True
    else:
        final = False

    active_work = get_active_work(emp)
    if not active_work:
        return HttpResponse(
            'You don\'t have any active task to submit to. Please start a '
            'new task first.', status=400)
    task = active_work[0]

    try:
        submit(emp, submitFile, comment, final, task.pk)
    except (ParseError):
        return HttpResponse(
            'Error parsing file. The file may be corrupt. Please contact '
            'the admin team for assistance.',
            status=400)
    except InvalidSubmission, e:
        return HttpResponse("Invalid submission: " + str(e), status=400)
    except Work.DoesNotExist:
        return HttpResponse("Could not find corresponding Work item.",
            status=400)

    return HttpResponse("Submitted task successfully.", status=201)


def obsolete_api_view(request):
    return HttpResponse('You are using an incompatible version of Knossos.'
                        'Please upgrade to the newest version.', status=400)


@login_required_403
def submit_test_api_view(request):
    """
    POST: Submit data for speed test
    """

    try:
        Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return HttpResponse(
            "Employee " + request.user.username + " could not be found",
            status=500)

    submitFile = request.FILES.get("submit_test_file", False)
    if not submitFile:
        return HttpResponse("No file uploaded.", status=400)

    return HttpResponse("Submitted task successfully.", status=201)
