import datetime

from django.utils import timezone

from knossos_aam_backend.models import Work


def freeze_delay_reached(cur_work):
    """
    True if cur_work has a final submission, has a freeze delay specified
    and its due date has been reached. False otherwise.

    Parameters
    ----------

    cur_work : Work instance
    """

    now = timezone.now()

    if cur_work.latestsubmit == None:
        return False

    if not cur_work.is_final:
        return False

    if cur_work.task.freeze_delay == 0.:
        return False

    freeze_delay = datetime.timedelta(cur_work.task.freeze_delay)
    cur_work_freeze_deadline = (
        cur_work.latestsubmit + freeze_delay)

    if cur_work_freeze_deadline < now:
        return True
    else:
        return False


def is_complete_frozen_task(task):
    """
    True if task is inactive (its coverage has been reached) and all associated
    Works are frozen. False otherwise.

    Parameters
    ----------

    task : Task instance
    """

    if task.is_active:
        return False

    for cur_w in task.work_set.all():
        if not cur_w.frozen:
            return False

    return True


def get_stale_work(max_age, in_cat=None):
    """
    Get stale work objects, i.e. Work objects with no submissions
    that were created a longer time than age ago, or Work objects
    where the most recent submission is older than age.

    Parameters
    ----------

    max_age : float
        In days

    in_cat : list of str
    """

    now = timezone.now()
    td = datetime.timedelta(max_age)

    age_cutoff = now - td

    if in_cat:
        no_submission_stale_works = Work.objects.filter(
            started__lt=age_cutoff,
            latestsubmit=None,
            task__category__name__in=in_cat,
            is_final=False, )
        submitted_stale_works = Work.objects.filter(
            latestsubmit__lt=age_cutoff,
            task__category__name__in=in_cat,
            is_final=False, )
    else:
        no_submission_stale_works = Work.objects.filter(
            started__lt=age_cutoff,
            latestsubmit=None,
            is_final=False, )
        submitted_stale_works = Work.objects.filter(
            latestsubmit__lt=age_cutoff,
            is_final=False, )

    stale_works = list(no_submission_stale_works) + list(submitted_stale_works)

    return stale_works
