"""
Set of functions for interacting (reading / writing) with the AAM. Business
logic goes here.
"""

__author__ = 'Fabian Svara'

import re
import zipfile
from cStringIO import StringIO

from django.db import transaction
from django.utils import timezone
from general_utilities.versions import compare_version
from knossos_utils.skeleton import Skeleton

import checks
import models
import view_helpers


class NonEmptyWork(Exception):
    pass


def delete_submission(s):
    if s.worktime:
        s.work.worktime = s.work.worktime - s.worktime

    s.work.save()
    s.delete()


def get_active_work(em):
    """
    Return active works for employee em.

    Parameters
    ----------

    em : Employee instance

    Returns
    -------

    active_work : list of Work instances
    """

    active_work = models.Work.objects.filter(
        employee=em,
        is_final=False,
    )

    active_work = list(active_work)
    active_work = sorted(active_work, key=lambda x: x.pk)

    return active_work


def get_completed_work(em):
    """
    Return completed works for employee em.

    Parameters
    ----------

    em : Employee instance

    Returns
    -------

    completed_work : list of Work instances
    """

    completed_work = models.Work.objects.filter(
        employee=em,
        is_final=True,
    )

    completed_work = list(completed_work)

    return completed_work


def get_available_tasks(em, count=1):
    """
    Return available tasks for employee em.

    Parameters
    ----------

    em : Employee instance

    count : int
        Number of Tasks per category to return

    Returns
    -------

    available_tasks_by_cat : dict of str -> list Task instances
        Maps category name to list of Tasks available in that category
        for employee em, where the tasks within the same category are sorted by
        primary key

    available_tasks : list of Task instances
        Task instances sorted by primary key
    """

    available_tasks_by_cat = {}
    available_tasks = []

    if em.project is None:
        return None, None

    for curCategory in em.project.taskcategory_set.all():
        cur_tasks = curCategory.task_set.filter(
            is_active=True, priority__gt=-1).exclude(employee=em)

        if len(cur_tasks) > 0:
            cur_tasks = list(cur_tasks)
            cur_tasks = sorted(
                cur_tasks, key=lambda x: x.priority, reverse=True)
            available_tasks_by_cat[curCategory] = cur_tasks[0:count]
            available_tasks.extend(cur_tasks)

    available_tasks = sorted(
        available_tasks, key=lambda x: x.priority, reverse=True)

    return available_tasks_by_cat, available_tasks


def reset_task(task, username):
    s = models.Submission.objects.filter(
        employee__user__username=username,
        work__task__name=task)
    s.delete()
    w = models.Work.objects.get(employee__user__username__exact=username,
                                task__name=task)
    w.worktime = 0.
    w.is_final = False
    w.latestsubmit = None
    w.last_submission = None
    w.save()


def unfinalize_work(work_id):
    w = models.Work.objects.get(pk=work_id)

    w.is_final = False
    w.save()


def cancel_task(task, username):
    w = models.Work.objects.get(
        task__name=task,
        employee__user__username=username, )

    if not w.submission_set.all():
        w.delete()
    else:
        raise NonEmptyWork('Submissions exist for this Work. Not deleting.')


def choose_task(employee, task_id):
    active_work = models.Work.objects.filter(
        employee=employee, is_final=False)
    if not len(active_work) == 0:
        raise view_helpers.TooManyActiveTasks()

    task = models.Task.objects.get(pk=task_id)
    if task.target_coverage > task.current_coverage:
        models.Work.objects.create(
            started=timezone.now(),
            task=models.Task.objects.get(pk=task_id),
            employee=employee,
            is_final=False, )
    else:
        raise view_helpers.UserRace()

    return


def submit(employee, submit_file, submit_comment, submit_is_final,
           submit_work_id, skip_checks=False):
    """Parses the submitted file, extracts the worktime and tests the nml.

    For submissions which are done on worktime tasks, the submission
    is created without any file.

    For regular submissions, the file name is checked on length.

    It is checked if the nml file was saved and created in the
    current version of Knossos.

    Parameters:
    ----------

    employee: Employee object
        Employee related to the submission

    submit_file: file object
        submitted nml file

    submit comment: string
        comment which was submitted together with the submission

    submit_is_final: bool
        True for final submission

    submit_work_id: integer
        id of the work related to this submission

    Returns:
    ----------

    incremental_worktime: float
        calculated worktime on this submission

    work: Work object

    automatic_worktime: bool
        True if worktime should be calculated

    Raises:
    ----------

    InvalidSubmission:

    if the filename is longer than 200 characters
    if the file was created/saved in an old version of Knossos
    if the worktime is lower than the one of the previous submission

    ImportError:

    if a check could not be imported from the Checks file

    DoesNotExist:

    if the Work object is not found

    ParseError:

    if the file cannot be opened by the Skeleton class.

    """
    if len(submit_file.name) > 200:
        raise view_helpers.InvalidSubmission(
            'The maximal file name length for submissions is '
            '200 character.')

    work = models.Work.objects.get(pk=submit_work_id)

    # testing for .k.zip is problematic, just do zip - django itself removes
    # the k sometimes (e.g. when changing the filename of task files
    # on uploading them by adding random chars)
    if submit_file.name.endswith('.zip'):
        fp = StringIO(submit_file.read())
        zipper = zipfile.ZipFile(fp, 'r')

        if 'annotation.xml' not in zipper.namelist():
            raise Exception('k.zip broken.')

        skeleton_file_as_string = zipper.read('annotation.xml')
    else:
        skeleton_file_as_string = submit_file.read()

    checks_to_run = re.split('\W', work.task.checks)
    checks_to_run = [x for x in checks_to_run if x]
    if checks_to_run and not skip_checks:
        check_fns = dict()
        for cur_check in checks_to_run:
            exec ('from knossos_aam_backend.checks import {0}'.format(cur_check))
            cur_check_fn = locals()[cur_check]
            check_fns[cur_check] = cur_check_fn

        skeleton = Skeleton()
        skeleton.fromNmlString(skeleton_file_as_string,
                               use_file_scaling=True)

        # Keyword arguments for check functions
        #

        kwargs = {'skeleton': skeleton,
                  'work': work,
                  'employee': employee,
                  'submit_file': submit_file,
                  'submit_comment': submit_comment,
                  'submit_work_id': submit_work_id,
                  'submit_is_final': submit_is_final,
                  'submit_file_as_string': skeleton_file_as_string, }

        # Check whether the knossos version is high enough

        version = skeleton.get_version()

        # Has work time tracking
        if compare_version(version['saved'], (4, 1, 2)) == '<':
            raise view_helpers.InvalidSubmission(
                "This tracing was saved in a version "
                "of Knossos that is too old and incompatible with "
                "knossos_aam. Please upgrade to version 4.1.2, "
                "available "
                "from www.knossostool.org, save the file again in "
                "that version, and resubmit.")
        else:
            # All fine, newest version.
            pass

        if 'automatic_worktime' not in checks_to_run:
            incremental_worktime = None
            auto_worktime = False
            output = checks.automatic_worktime(**kwargs)
        else:
            auto_worktime = True
            output = checks.automatic_worktime(**kwargs)
            if type(output) == str:
                raise view_helpers.InvalidSubmission(output)
            else:
                incremental_worktime = output
            del check_fns['automatic_worktime']

        # Here is the part where the tests are done
        #
        for cur_check in check_fns:
            output = eval(cur_check)(**kwargs)
            if type(output) == str:
                raise view_helpers.InvalidSubmission(output)

        if 'automatic_worktime' in checks_to_run and incremental_worktime:
            work.worktime = work.worktime + incremental_worktime
            work.save()

    else:
        incremental_worktime = None
        auto_worktime = False

    # Send e-mail if comment is added to submission.

    if submit_comment:
        subject = 'Comment on Submission of Task {0} Task from {1}'.format(work.task.name, employee.user.username)
        attachments = [(skeleton_file_as_string, submit_file.name)]
        # todo get mailing to work again
        # mail_notify('to@example.com', subject, submit_comment,
        #            attachments=attachments, reply_to=work.employee.user.email)

    s = models.Submission.objects.create(
        employee=employee,
        date=timezone.now(),
        work=work,
        comment=submit_comment,
        is_final=submit_is_final,
        worktime=incremental_worktime,
        original_filename=submit_file.name[0:200],
        datafile=submit_file, )
    s.save()


def get_monthly_worktime_for_submissions(submission_set):
    """ Calculate how much of the work time has been spent in different months
    Parameters:
    ----------
    submission_set: QuerySet(Submission)

    Returns:
    ----------

    set {by_month_per_task, by_month_totals}

    by_month_per_task: { year: { month: { task: [worktime, is_final] } } }
    by_month_totals: { year: { month: [worktime, is_final] } }

    """

    by_month_per_task = {}
    by_month_totals = {}

    s = submission_set.order_by('date')

    for curs in s:
        year = curs.date.year
        month = curs.date.month
        task = curs.work.task

        incomplete_time = False

        if curs.worktime is None:
            cur_worktime = 0.
            incomplete_time = True
        else:
            cur_worktime = curs.worktime

        if year not in by_month_per_task:
            by_month_per_task[year] = {}
            by_month_totals[year] = {}
        if month not in by_month_per_task[year]:
            by_month_per_task[year][month] = {}
            # Second item in tuple indicates whether the worktime
            # is incomplete, i.e. work was performed on tasks
            # for which worktime is not automatically computed
            by_month_totals[year][month] = [0, False]
        if task not in by_month_per_task[year][month]:
            by_month_per_task[year][month][task] = [0, False]

        if incomplete_time:
            by_month_per_task[year][month][task][1] = True
            by_month_totals[year][month][1] = True

        by_month_per_task[year][month][task][0] = \
            by_month_per_task[year][month][task][0] + cur_worktime
        by_month_totals[year][month][0] = \
            by_month_totals[year][month][0] + cur_worktime

    return {'by_month_per_task': by_month_per_task,
            'by_month_totals': by_month_totals, }


def get_monthly_worktime_for_work(w):
    return get_monthly_worktime_for_submissions(w.submission_set)


def get_employee_info(emp):
    work = get_active_work(emp)
    info = {"name": " ".join([emp.user.first_name, emp.user.last_name]),
            "username": " ".join([emp.user.username]),
            "project": emp.project.name}
    if len(work) > 0:
        work = work[0]
        info["task_name"] = work.task.name
        info["work_time"] = work.worktime
        info["last_submit"] = work.last_submission.datafile
    return info


def get_employees_current_work():
    emp_set = {}
    for emp in models.Employee.objects.all():
        emp_set[emp] = get_employee_info(emp)
    return emp_set


def get_employee_infos_in_project(proj):
    employees = models.Employee.objects.filter(project=proj)
    emp_infos = []
    for emp in employees:
        emp_infos.append(get_employee_info(emp))
    return emp_infos


def move_employees_to_project(employees, new_project):
    with transaction.atomic():
        for employee in employees:
            employee.project = new_project
            employee.save()
