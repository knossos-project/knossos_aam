"""
Functions for interacting with the knossos_aam HTTP API through python. Example
session shown in main().
"""


import requests
import re
from zipfile import ZipFile
import os
import json


class AAMError(Exception):
    pass


class AAMUnfinishedTaskException(Exception):
    pass


class AAMApi(object):
    def __init__(self, server):
        _actions = {
            'logout': 'api/2/logout',
            'login': 'api/2/login',
            # api/2/session returns XML. We prefer json for convenience.
            # 'session_state': 'api/2/session',
            'session_state': 'api/2/session_json/',
            'submit': 'api/2/submit',
            'current_file': 'api/2/current_file',
            'new_task': 'api/2/new_task',
        }

        self.session = requests.Session()
        self.server = server
        self.urls = {xx : '%s/%s' % (server, yy)
                     for xx, yy in _actions.iteritems()}

    def login(self, username, password):
        post_txt = '<login><username>%s</username>' \
                   '<password>%s</password></login>' % (
            username, password, )

        r = self.session.post(self.urls['login'], post_txt)
        if r.status_code != 200:
            raise AAMError('Login not successful. %s' % (r.content, ))

    def logout(self):
        r = self.session.get(self.urls['logout'])
        if r.status_code != 200:
            raise AAMError('Logout not successful. %s' % (r.content, ))

    def session_state(self):
        r = self.session.get(self.urls['session_state'])
        if r.status_code != 200:
            raise AAMError('State request not successful. %s' % (r.content, ))

        session_status = json.loads(r.content)
        return session_status

    def submit(self, filename, comment='', is_final=False):
        files = {
            'submit_work_file': open(filename, 'rb'), }
        post_text = {
            'filename': os.path.basename(filename),
            'submit_comment': comment,
            'submit_work_is_final': is_final,
            'csrfmiddlewaretoken': self.session.cookies['csrftoken'], }
        r = self.session.post(self.urls['submit'], post_text, files=files)

        if r.status_code != 201:
            raise AAMError('Submission not successful. %s' % (r.content, ))

    def _get_file_from_response(self, r):
        """
        Extract filename and file contents from AAM response
        """

        fname_ex = 'filename=([^;]+);'
        m = re.search(fname_ex, r.headers['content-disposition'])

        return m.groups()[0], r.content

    def download_current_file(self, out_dir):
        r = self.session.get(self.urls['current_file'])
        if r.status_code != 200:
            raise AAMError('Download not successful. %s' % (r.content, ))

        fname, file_contents = self._get_file_from_response(r)
        out_fname = '%s/%s' % (out_dir, fname, )

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        with open(out_fname, 'wb') as fp:
            fp.write(file_contents)

        return out_fname

    def start_new_task(self, out_dir):
        r = self.session.get(self.urls['new_task'])

        if r.status_code != 200:
            if r.content == 'Please finish your current task first.':
                raise AAMUnfinishedTaskException(
                    'Starting new task not successful. Have unfinished task.')
            else:
                raise AAMError('Starting new task not successful. %s' % (
                    r.content, ))

        fname, file_contents = self._get_file_from_response(r)
        out_fname = '%s/%s' % (out_dir, fname, )

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        with open(out_fname, 'wb') as fp:
            fp.write(file_contents)

        return out_fname


def create_temporary_submission_file(fname='example.k.zip'):
    example_nml = """<?xml version="1.0" encoding="UTF-8"?>
<things>
    <parameters>
        <experiment name=""/>
        <lastsavedin version="4.1.2"/>
        <createdin version="3.2"/>
        <time ms="0" checksum="df3f619804a92fdb4057192dc43dd748ea778adc52bc498ce80524c014b81119"/>
        <scale x="1" y="1" z="1"/>
    </parameters>
</things>
    """
    with open('annotation.xml', 'w') as fp:
        fp.write(example_nml)

    with ZipFile(fname, 'w') as zipfp:
        zipfp.write('annotation.xml')

    return [fname, 'annotation.xml']


def pretty_print_session_status(session_status):
    if 'task_name' in session_status:
        # Have an active task
        pretty_str = u'Active user: {username} ({first_name} {last_name}). ' \
                     'Active Task: {task_name} (Comment: {task_comment}) in ' \
                     'category {task_category_name} (Description: ' \
                     '{task_category_description}).'.format(**session_status)
        print(pretty_str)
    else:
        pretty_str = u'Active user: {username} ({first_name} {last_name}).'.\
            format(**session_status)
        print(pretty_str)


def test_aam_api():
    """
    Test core AAM API functionality. The following things are done:
    This changes the AAM DB state and may legitimately fail if e.g. no new
    tasks are available or some submission checks fail.
    """

    tmp_files = create_temporary_submission_file()

    a = AAMApi('http://127.0.0.1:8000')
    a.login('user', 'password')
    session_status = a.session_state()
    pretty_print_session_status(session_status)
    try:
        a.start_new_task('./tmp')
    except AAMUnfinishedTaskException:
        a.submit('example.k.zip', is_final=True)
        a.start_new_task('./tmp')
    a.submit('example.k.zip', 'some comment')
    a.download_current_file('./tmp')
    session_status = a.session_state()
    pretty_print_session_status(session_status)
    a.submit('example.k.zip', is_final=True)
    session_status = a.session_state()
    pretty_print_session_status(session_status)

    a.logout()

    for cur_f in tmp_files:
        os.remove(cur_f)


if __name__ == '__main__':
    test_aam_api()