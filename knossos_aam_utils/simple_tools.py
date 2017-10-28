from knossos_aam_backend.models import Task, Submission, Work
import os, shutil, random
from django.core.files import File

def reset_task(username, task, month=None, delete_work=False):
    for cur_task in task:
        if month is not None:
            s = Submission.objects.filter(
                date__month=month,
                employee__user__username=username,
                work__task__name=cur_task)
        else:
            s = Submission.objects.filter(
                employee__user__username=username,
                work__task__name=cur_task)
        s.delete()
        w = Work.objects.get(employee__user__username__exact=username,
	    task__name=cur_task)
        w.worktime = 0.
        w.is_final = False
        w.latestsubmit = None
        w.save()

        print 'Reset %s' % (w, )

        if delete_work:
            w.delete()
            print('Deleted %s' % (w, ))


def get_average_worktime(w):
    return sum([x.worktime for x in w]) / len(w)


def stats_for_task_set(t):
    stats = []

    for cur_t in t:
        avg_time = get_average_worktime(cur_t.work_set.all())
        fname = cur_t.task_file
        size = cur_t.task_file._get_size() / 1000.
        
        stats.append((fname, avg_time, size))

    return stats


def print_stats_for_task_set(t):
    for fname, avg_time, size in stats_for_task_set(t):
        print('%s\t%s\t%s' % (fname, avg_time, size,))


def copy_task(source_task, target_name, target_category):
    t = Task()
    t.category = target_category
    t.name = target_name
    t.target_coverage = source_task.target_coverage
    t.freeze_delay = source_task.freeze_delay
    t.checks = source_task.checks
    t.priority = source_task.priority
    t.comment = source_task.comment
    t.x = source_task.x
    t.y = source_task.y
    t.z = source_task.z
    t.is_productive = source_task.is_productive

    if source_task.task_file:
        fobj = file(source_task.task_file.path)
        t.task_file = File(fobj)
    
    t.save()


    return t


if __name__=='__main__':
    pass
