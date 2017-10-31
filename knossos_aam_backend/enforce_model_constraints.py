"""
Signal-based actions to enforce model constraints, connected to their
respective models in models.py. Function names start with sender model name.
"""

import os
from inspect import getmembers
from inspect import isfunction

import models as mdl
from helpers import get_filefield_abspath

__author__ = 'Fabian Svara'


#
# Pre-save actions
#


def task_name_without_dashes(sender, instance, **kwargs):
    instance.name = instance.name.replace('-', '_')


def task_category_name_combination(sender, instance, **kwargs):
    instance.category_name_combination = '{0}_{1}'.format(instance.category.name, instance.name)


def task_ensure_valid_path(sender, instance, **kwargs):
    abs_dir = os.path.dirname(get_filefield_abspath(instance.task_file))
    if not os.path.exists(abs_dir):
        os.makedirs(abs_dir)


def submission_ensure_valid_path(sender, instance, **kwargs):
    abs_dir = os.path.dirname(get_filefield_abspath(instance.datafile))
    if not os.path.exists(abs_dir):
        os.makedirs(abs_dir)


def submission_work_enforce_frozen(sender, instance, **kwargs):
    if isinstance(instance, mdl.Work):
        w = instance
    if isinstance(instance, mdl.Submission):
        w = instance.work

    if w._frozen:
        raise Exception('Cannot modify frozen work!')

    if w.frozen:
        w._frozen = True


#
# Post-save actions
#


def task_validate_checks(sender, instance, created, **kwargs):
    if created:
        from knossos_aam_backend import checks
        available_checks_list = []
        for x in [i for i in getmembers(checks) if isfunction(i[1])]:
            available_checks_list.append(x[0])
        user_checks_list = instance.checks.replace(',', ' ').split()
        for cur_check in user_checks_list:
            if cur_check not in available_checks_list:
                raise Exception('Check {0} is not available. Please try again.'.format(cur_check))


def task_update_post_work_creation(sender, instance, created, **kwargs):
    if created:
        instance.task.current_coverage += 1
        if instance.task.current_coverage >= instance.task.target_coverage:
            instance.task.is_active = False
        instance.task.save()


def work_update_post_submission(sender, instance, created, **kwargs):
    if created:
        instance.work.is_final = instance.is_final
        instance.work.last_submission = instance
        instance.work.save()


def task_category_name_without_dashes(sender, instance, created, **kwargs):
    if created:
        instance.name = instance.name.replace('-', '_')
        instance.save()


def user_create_employee(sender, instance, created, **kwargs):
    if created:
        profile, created = mdl.Employee.objects.get_or_create(user=instance)


def project_name_without_dashes(sender, instance, created, **kwargs):
    if created:
        instance.name = instance.name.replace('-', '_')
        instance.save()


def user_username_without_dashes(sender, instance, created, **kwargs):
    if created:
        instance.username = instance.username.replace('-', '_')
        instance.save()


#
# Post-delete actions
#


def task_update_post_work_deletion(sender, instance, **kwargs):
    instance.task.current_coverage -= 1
    if instance.task.current_coverage < instance.task.target_coverage:
        instance.task.is_active = True
    instance.task.save()
