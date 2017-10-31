from django.http import HttpResponse
from general_utilities.mailer import Mailer

from models import Employee

__author__ = 'Fabian Svara'


class ParseError(Exception):
    pass


class InvalidSubmission(Exception):
    pass


class UserRace(Exception):
    pass


class TooManyActiveTasks(Exception):
    pass


class KnossosIntegrationError(Exception):
    pass


def mail_notify(to, subject, body, attachments=None, reply_to=None):
    ma = Mailer('mail',
                use_auth=True,
                use_smtps=True,
                smtp_user='username',
                smtp_pass='password',
                port=465)
    ma.open_session()

    ma.send_mail('sender@example.com',
                 ['recipient@example.com'],
                 subject,
                 body,
                 attachments=attachments,
                 reply_to=reply_to)

    ma.close_session()


def login_required_403(fn):
    """
    Decorator for views like login_required from django, instead that this
    one returns HTTP 403 if the user is not logged in.
    """

    def decorator(request, *args, **kwargs):
        if not request.user.is_authenticated():
            return HttpResponse(
                "You are not authenticated. Permission denied.", status=403)
        return fn(request, *args, **kwargs)

    return decorator


def admin_check(user):
    e = Employee.objects.get(user=user)
    return e.is_admin
