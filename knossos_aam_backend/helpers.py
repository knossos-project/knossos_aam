import os

from django.conf import settings


def get_filefield_abspath(filefield):
    pth = '{0}/{1}'.format(settings.MEDIA_ROOT, filefield.name)

    return os.path.normpath(pth)
