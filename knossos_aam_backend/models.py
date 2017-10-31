from inspect import getmembers, isfunction

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save, post_delete, pre_save
from django.utils.text import get_valid_filename

import checks
import enforce_model_constraints as emc

__author__ = 'Fabian Svara'


def submission_filename(self, filename):
    finalstring = ""
    if self.is_final:
        finalstring = "final"

    # if filename.endswith('.nml'):
    #    extension = '.nml'
    # elif filename.endswith('.k.zip'):

    # no files other than k.zips should ever be submitted
    extension = '.k.zip'

    # else:
    #    extension = '.unknown'

    fname = '-'.join([self.work.task.category.name,
                      self.work.task.name,
                      self.employee.user.username,
                      self.date.strftime('%Y%m%d-%H%M%S')
                         , ])
    fname += "-" + finalstring + extension if self.is_final else extension
    abs_fname = '{0}/{1}/{2}'.format(self.work.task.category.project.name, self.work.task.category.name, fname)

    return abs_fname


def task_filename(self, filename):
    if not filename.lower().endswith('.k.zip'):
        raise Exception('Only task file with extension .k.zip allowed')

    extension = '.k.zip'
    # elif filename.lower().endswith('.nml'):
    #    extension = '.nml'
    # else:
    #    extension = '.nml'

    fname = '-'.join([self.category.name, self.name]) + extension
    fname = get_valid_filename(fname)
    fname = 'task-files/{0}/{1}/{2}'.format(self.category.project.name, self.category.name, fname)

    return fname


class Project(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=1000)
    comment = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class Employee(models.Model):
    user = models.OneToOneField(User)

    project = models.ForeignKey(Project, null=True, blank=True)
    task = models.ManyToManyField('Task', through='Work')
    comment = models.TextField(blank=True, null=True)
    is_admin = models.BooleanField(default=False)

    def __unicode__(self):
        return "Employee: %s %s (%s)" % (
            self.user.first_name, self.user.last_name, self.user.username)


class TaskCategory(models.Model):
    name = models.CharField(max_length=200)
    project = models.ForeignKey(Project)
    description = models.TextField()
    comment = models.TextField(blank=True)

    def __unicode__(self):
        return "Task Category " + self.name


class Task(models.Model):
    category = models.ForeignKey(TaskCategory)
    name = models.CharField(max_length=100)
    # Used to enforce uniqueness of category / name together
    category_name_combination = models.CharField(max_length=1000, unique=True, blank=True, null=False)
    date_added = models.DateTimeField('Date added', auto_now_add=True)
    # How many times to hand this task out to a different annotator
    target_coverage = models.IntegerField(default=3)
    current_coverage = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    # This is used to sort tasks for display to users, high integer here means high priority.
    priority = models.IntegerField(default=1)
    comment = models.TextField(blank=True)
    # Check names need to be entered manually by name
    # How long to wait after a final submission before setting the
    # corresponding Work frozen. 0 means never freeze automatically.
    # In days.
    freeze_delay = models.FloatField(default=0., blank=False, null=False)
    task_file = models.FileField(default=False, upload_to=task_filename, null=True, blank=True)

    def checks_available():
        # Checks are functions that can run on a submission to ensure that it
        # fulfills certain criteria.
        checks_list = []
        for x in [i for i in getmembers(checks) if isfunction(i[1])]:
            checks_list.append(x[0])
        return ' '.join(checks_list)

    checks = models.CharField(max_length=400, blank=True, help_text=checks_available())

    def latest_submissions(self):
        return [xx.last_submission for xx in self.work_set.all()
                if xx.last_submission is not None]

    def oldest_submission(self):
        all_submissions = []

        for cur_w in self.work_set.all():
            for cur_s in cur_w.submission_set.all():
                all_submissions.append(cur_s)

        all_submissions_sorted = sorted(all_submissions, key=lambda x: x.date)

        if all_submissions_sorted:
            return all_submissions_sorted[0]
        else:
            return None

    def __unicode__(self):
        return "Task: " + " / ".join([self.category.project.name, self.category.name, self.name])


class Work(models.Model):
    """
    A work instance represents a Task assigned to a specific Employee.
    Submissions are then assigned to the corresponding Work.
    """

    started = models.DateTimeField('Work started', auto_now_add=True)
    task = models.ForeignKey(Task)
    employee = models.ForeignKey(Employee)
    last_submission = models.ForeignKey(
        'Submission', blank=True, null=True, default=None,
        related_name="last_submission")
    is_final = models.BooleanField(default=False)
    comment = models.TextField(blank=True)

    # Whether to allow changes
    frozen = models.BooleanField(default=False)
    _frozen = models.BooleanField(default=False)

    # Current total work time. This should not be used to check
    # tracer work time, since it is not bound to a specific
    # month. Only the Submission can be used for that.
    worktime = models.FloatField(default=0)

    def __unicode__(self):
        return "Work unit: " + " / ".join([
            self.employee.user.username,
            self.task.category.project.name,
            self.task.category.name,
            self.task.name, ])


class Submission(models.Model):
    employee = models.ForeignKey(Employee)
    date = models.DateTimeField('Submission time / date')
    work = models.ForeignKey(Work)

    comment = models.TextField(blank=True)
    is_final = models.BooleanField(default=False)
    original_filename = models.CharField(max_length=200)

    # The following fields are automatically extracted
    # Work time in milliseconds
    # Null / None worktime means the work time was not
    # extracted automatically and should be set manually.
    worktime = models.FloatField(default=0, null=True, blank=True)

    def worktime_string(self):
        return str(self.worktime)

    datafile = models.FileField(upload_to=submission_filename, max_length=400)

    def __unicode__(self):
        submissiontype = "Submission:"

        if self.is_final:
            submissiontype = "Final Submission:"

        return submissiontype + " / ".join([
            self.work.task.category.project.name,
            self.work.task.category.name,
            self.work.task.name,
            self.employee.user.username,
            str(self.date), ])


pre_save.connect(emc.submission_work_enforce_frozen, sender=Submission)
pre_save.connect(emc.submission_ensure_valid_path, sender=Submission)
post_save.connect(emc.work_update_post_submission, sender=Submission)

post_save.connect(emc.user_username_without_dashes, sender=User)
post_save.connect(emc.user_create_employee, sender=User)

pre_save.connect(emc.submission_work_enforce_frozen, sender=Work)
post_save.connect(emc.task_update_post_work_creation, sender=Work)
post_delete.connect(emc.task_update_post_work_deletion, sender=Work)

post_save.connect(emc.project_name_without_dashes, sender=Project)

post_save.connect(emc.task_category_name_without_dashes, sender=TaskCategory)

pre_save.connect(emc.task_name_without_dashes, sender=Task)
pre_save.connect(emc.task_category_name_combination, sender=Task)
pre_save.connect(emc.task_ensure_valid_path, sender=Task)
post_save.connect(emc.task_validate_checks, sender=Task)
