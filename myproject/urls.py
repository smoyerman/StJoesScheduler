"""myproject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from myproject.views import generate_schedule, homepage, update_pto, request_day, remove_day
from django.conf.urls import include

urlpatterns = [
    url(r'^$', homepage),
    url(r'^admin/', admin.site.urls),
    url('^', include('django.contrib.auth.urls')),
    url(r'^schedule/(\d{4})/(\d{1,2})/$', generate_schedule),
    url(r'^pto/(\d{4})/(\d{1,2})/$', update_pto),
    url(r'^request/(\d{1,2})/(\d{4})/(\d{1,2})/(\d{1,2})/$', request_day),
    url(r'^remove/(\d{1,2})/(\d{4})/(\d{1,2})/(\d{1,2})/$', remove_day),
]
