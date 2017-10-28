"""External functions to perform tests on submitted nmls.

Functions in this file can be changed while the aam server 
is running. 

Functions:
----------

    automatic_worktime: calculates the time spent working on the 
                        submission
    check_simple: checks if there is only one skeleton and raises an
                  error if there is more than one tree
    check_seed_contained: checks if the seed point is contained in
                          the skeleton
    check_connected_component: checks if all nodes in the skeleton are
                               connected 

Parameters:
----------

    skeleton: Skeleton object
        skeleton that is analyzed
    work: Work object
        work connected to skeleton
    employee: Employee object
        Employee who is submitting this work
    submit_file: file object
        file can be parsed and read
    submit_is_final: boolean
        true for final submission

"""

__author__ = 'Fabian Svara'


from django.http import Http404

import re
from knossos_utils.skeleton import Skeleton
from knossos_utils.skeleton_utils import get_the_nonempty_annotation
from knossos_utils.skeleton_utils import split_by_connected_component
from knossos_utils.skeleton_utils import get_nodes_with_comment
from knossos_utils.skeleton_utils import iter_nodes_dfs
from knossos_utils.skeleton_utils import get_annotations_with_comment
from knossos_utils.skeleton_utils import get_nodes_with_token
from general_utilities.mailer import Mailer


class InvalidSubmission(Exception):
    pass


def automatic_worktime(**kwargs):
    """Calculates worktime of submission.

    The time the user spent working on this skeleton during this 
    submission is calculated.

    The work is updated by this worktime.

    Returns:
    ----------

    incremental_worktime: float
        time spent on this submission

    Raises:
    ----------

    InvalidSubmission:
    
    if the submissions worktime is too low
    
    """

    # to unpack the keyword arguments
    #
  
    skeleton = kwargs['skeleton']
    work = kwargs['work']

    worktime = ((skeleton.getSkeletonTime() - skeleton.getIdleTime())
                                                   / 1000.0 / 3600.0)
    if worktime < 0:
        worktime = 0.
    if work.worktime > worktime:
        return ("The work time for this submission "
                "is lower than a previous submission.")

    incremental_worktime = worktime - work.worktime

    return incremental_worktime


def check_simple(**kwargs):
    """Checks if there is only one tree in the skeleton.

    Uses is_simple_skeleton from skeleton_utils.

    Raises:
    ----------

    InvalidSubmission:

    if there is more than one tree in the file    

    """
  
    skeleton = kwargs['skeleton']

    from knossos_utils.skeleton_utils import is_simple_skeleton
    if not is_simple_skeleton(skeleton):
        return ("This skeleton file contains more than one tree. "
                "Please correct the problem and resubmit.")


def check_seed_contained(**kwargs):
    """Checks if the initial seed points are contained in the skeleton.

    Raises:
    ----------

    InvalidSubmission:

    if the seed node is not contained in the skeleton    

    """

    (skeleton, work) = (kwargs['skeleton'], kwargs['work'])

    if not work.task.task_file:
        if not skeleton.has_node([work.task.x, work.task.y, work.task.z]):
            return ("This skeleton does not contain a node at the position "
                    "of the seed point (%d, %d, %d). Please correct the "
                    "problem and resubmit. Hint: If you need to move a node "
                    "only slightly, you can click it with the middle mouse "
                    "button and drag the node." 
                    % (work.task.x, work.task.y, work.task.z))                


def check_connected_component(**kwargs):
    """Checks if all nodes are connected in the skeleton.

    Uses is_singly_connected function from skeleton_utils.

    Raises:
    ----------

    InvalidSubmission:

    if not all nodes are connected in the skeleton.

    """
    
    skeleton = kwargs['skeleton']

    from knossos_utils.seleton_utils import is_singly_connected
    from knossos_utils.seleton_utils import get_the_nonempty_annotation
    from knossos_utils.seleton_utils import NonSimpleNML
    
    try:
        anno = get_the_nonempty_annotation(skeleton)
    except NonSimpleNML:
        return ('This skeleton file contains more than one non-empty trees. '
               'Please correct that problem and resubmit.')

    if not is_singly_connected(anno):
        return ("This skeleton file contains a tree that contains unconnected "
                "parts. Please make sure there are no gaps in the tree and resubmit.")


def email_on_submission(**kwargs):
    """
    Send e-mail on submission.

    The parsed nml can be find attached to the e-mail.
    """

    (work, submit_is_final, submit_file, nml_string) = (kwargs['work'],
        kwargs['submit_is_final'], kwargs['submit_file'],
        kwargs['submit_file_as_string'])

    if submit_is_final:
        is_final_string = 'Final '
    else:
        is_final_string = ''

    submit_file = kwargs['submit_file']

    skeletonFileAsString = submit_file.read()
    ma = Mailer('mail_host',
                use_auth=True,
                use_smtps=True,
                smtp_user='smtp_user',
                smtp_pass='smtp_pass',
                port=465)
    ma.open_session()

    subject = 'New %sSubmission Notification: %s by %s' % (
        is_final_string, work.task.name, work.employee.user.username, )

    ma.send_mail('sender@example.com',
                 ['recipient@example.com'],
                 subject,
                 'Subject',
                 attachments=[(nml_string, submit_file.name)],
                 reply_to=work.employee.user.email)

    ma.close_session()
