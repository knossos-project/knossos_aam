"""
Functions for import of tasks into the knossos_aam. Can only be executed on the
server where the Django knossos_aam application is running.

* todo: Add task category and task name automatically to kzips, to make
        sure that knossos does not complain anymore.

Example usage from an ipython shell that can import Django:

import generic_task_importer as gti

git.import_tasks(path_to_csv_descriptor, False, False, False, True, 0., '')


"""

from django.core.files import File
from django.db import transaction
from knossos_utils.skeleton_utils import skeleton_from_single_coordinate

from knossos_aam_backend.models import Task, TaskCategory

AUTO_GENERATED_NML_DIR = 'auto_generated_nml'


@transaction.atomic
def import_tasks(
        csv_input,
        check_simple=True,
        check_seed_contained=True,
        check_connected_component=True,
        automatic_worktime=True,
        freeze_delay=0.,
        comment=''):
    """
    Script to create new tasks in amm that are  kzip based task files
    that can be downloaded.
    """

    matched_names = {}

    with open(csv_input, 'r') as f:
        for cur_line in f.readlines():
            cur_task = [x for x in cur_line.split('\t') if not x.isspace()]
            cur_task = [x.strip() for x in cur_task if x != '']
            print('Importing: {0}'.format(cur_task))

            # fix problems with empty lines at end etc
            if len(cur_task) == 0:
                continue

            if len(cur_task) == 4:
                category = cur_task[0]
                task_id = cur_task[1]
                task_filepath = cur_task[2]
                target_coverage = int(cur_task[3])
                x = 0
                y = 0
                z = 0
            elif len(cur_task) == 6:
                category = cur_task[0]
                task_id = cur_task[1]
                x = int(cur_task[2])
                y = int(cur_task[3])
                z = int(cur_task[4])
                target_coverage = int(cur_task[5])

                s = skeleton_from_single_coordinate(
                    [x, y, z], comment='First Node', branchpoint=True)
                task_filepath = '%s/%s_%s.nml' % (
                    AUTO_GENERATED_NML_DIR,
                    category,
                    task_id,)
                s.toNml(task_filepath)
            elif len(cur_task) == 7:
                category = cur_task[0]
                task_id = cur_task[1]
                x = int(cur_task[2])
                y = int(cur_task[3])
                z = int(cur_task[4])
                target_coverage = int(cur_task[5])
                tree_comment = cur_task[6].strip()

                s = skeleton_from_single_coordinate(
                    [x, y, z], comment='First Node', branchpoint=True)
                for cur_a in s.getAnnotations():
                    cur_a.comment = tree_comment
                task_filepath = '%s/%s_%s.nml' % (
                    AUTO_GENERATED_NML_DIR,
                    category,
                    task_id,)
                s.toNml(task_filepath)

            else:
                raise Exception('Unknown format.')

            try:
                with open(task_filepath):
                    pass
            except IOError:
                raise Exception(
                    'Task path in csv file could not be matched to an '
                    'actual task file: ' + task_filepath)

            cat = TaskCategory.objects.get(name=category)
            taskfileobj = file(task_filepath)

            checks = []
            if check_simple:
                checks.append('check_simple')
            if check_connected_component:
                checks.append('check_connected_component')
            if check_seed_contained:
                checks.append('check_seed_contained')
            if automatic_worktime:
                checks.append('automatic_worktime')

            checks = ' '.join(checks)

            t = Task.objects.create(name=str(task_id),
                                    target_coverage=target_coverage,
                                    category=cat,
                                    checks=checks,
                                    comment=comment,
                                    freeze_delay=freeze_delay,
                                    task_file=File(taskfileobj))

            t.save()
            taskfileobj.close()


# settings hints:

# for focused annotation seeds:
# use freeze delay of 7.
# use check simple
# use check seed contained
# use check connectec component


if __name__ == '__main__':
    import_tasks(
        'xxx.csv',
        freeze_delay=7.,
        check_simple=False,
        check_seed_contained=False,
        check_connected_component=False,
        automatic_worktime=True)
