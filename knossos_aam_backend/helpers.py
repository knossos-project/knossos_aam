import os

from django.conf import settings


def get_filefield_abspath(filefield):
    pth = '%s/%s' % (settings.MEDIA_ROOT, filefield.name,)

    return os.path.normpath(pth)
