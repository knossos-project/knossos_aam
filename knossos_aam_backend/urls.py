from django.conf.urls import url
from django.contrib.auth.views import login
import views # webinterface views
import views_api # api views


__author__ = 'Fabian Svara'


urlpatterns = [
        url(r'^$',
            views.home_view,
            name='home'),
        url(r'^login/?$',
            login,
            {'template_name': 'knossos_aam_backend/login.html'},
            name='login'),
        url(r'^timeoverview/?$',
            views.timeoverview_view,
            name='timeoverview'),
        url(r'^timeoverview/projects/?$',
            views.timeoverview_sort_by_project_view,
            name='timeoverview_sort_by_project'),
        url(r'^monthoverview/(?P<year>\d+)/(?P<month>\d+)/?$',
            views.monthoverview_view,
            name='monthoverview'),
        url(r'^monthoverview/projects/(?P<year>\d+)/(?P<month>\d+)/?$',
            views.monthoverview_sort_by_project_view,
            name='monthoverview_sort_by_project'),
        url(r'^sort_by_project/?$',
            views.sort_by_project_view,
            name='sort_by_project'),
        url(r'^workdetails/(?P<work_id>\d+)/?$',
            views.workdetails_view,
            name='workdetails'),
        url(r'^usertime/?$',
            views.usertime_view,
            name='usertime'),
        url(r'^changetask/$',
            views.changetask_view,
            name='changetask'),
        url(r'^reset_task/?$',
            views.reset_task_view,
            name='reset_task'),
        url(r'^cancel_task/?$',
            views.cancel_task_view,
            name='cancel_task'),
        url(r'^task-files/(.*)$',
            views.download_task_file_view,
            name='download_task_file'),
        url(r'^logout/?$',
            views.logout_view,
            name='logout'),
        url(r"^employee_work_overview/?$", views.employee_work_overview, name="employee_work_overview"),
        url(r"^employee_project_overview/?$", views.employee_project_overview, name="employee_project_overview"),

        # for KNOSSOS
        url(r'api/2/session/?$', views_api.session_api_view),
        url(r'api/2/login/?$', views_api.login_api_view),
        url(r'api/2/logout/?$', views_api.logout_api_view),
        url(r'api/2/submit/?$', views_api.submit_api_view),
        url(r'api/2/submit_test/?$', views_api.submit_test_api_view),
        url(r'api/2/new_task/?$', views_api.new_task_api_view),
        url(r'api/2/current_file/?$', views_api.current_file_api_view),
        url(r'knossos/.*$', views_api.obsolete_api_view), # appears to not work the way it was intended, not sure why
]
