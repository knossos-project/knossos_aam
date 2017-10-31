from django.conf.urls import include, url

from django.contrib import admin

admin.autodiscover()

urlpatterns = [
    url(r'^', include('knossos_aam_backend.urls', namespace="knossos_aam_backend")),
    url(r'^admin/?', include(admin.site.urls)),
]
