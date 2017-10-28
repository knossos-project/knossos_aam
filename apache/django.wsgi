import os
import sys

UPGRADING=False

upgrade_file = '/path/to/knossos_aam/knossos_aam_backend/static/upgrade.html'

os.environ['DJANGO_SETTINGS_MODULE'] = 'knossos_aam.settings'

def upgrade_in_progress(environ, start_response):
    if os.path.exists(upgrade_file):
        response_headers = [('Content-type','text/html')]
        response = open(upgrade_file).read()
    else:
        response_headers = [('Content-type','text/plain')]
        response = 'Application upgrade in progress...please check back soon.'
    
    if environ['REQUEST_METHOD'] == 'GET':
        status = '503 Service Unavailable'
    else:
        status = '405 Method Not Allowed'
    start_response(status, response_headers)
    return [response]

if UPGRADING:
    application = upgrade_in_progress
else:
    import django.core.handlers.wsgi
    application = django.core.handlers.wsgi.WSGIHandler()
