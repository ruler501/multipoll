"""
multipoll URL Configuration.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/

Examples:
    Function views
        1. Add an import:  from my_app import views
        2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
    Class-based views
        1. Add an import:  from other_app.views import Home
        2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
    Including another URLconf
        1. Add an import:  from blog import urls as blog_urls
        2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import url

from multipoll import views

urlpatterns = [
    url(r'^status', views.server_status, name="status"),
    url(r'^slack/interactive', views.interactive_button, name="interactive_button"),
    url(r'^slack/slash', views.slash_poll, name="poll"),
    url(r'^polls/(?P<poll_timestamp>\d+(\.\d+)?)/results/visualize',
        views.poll_results_visualization),
    url(r'^polls/(?P<poll_timestamp>\d+(\.\d+)?)/results', views.poll_results),
    url(r'^polls/(?P<poll_timestamp>\d+(\.\d+)?)/vote', views.vote_on_poll),
    url(r'^polls/(?P<poll_timestamp>\d+(\.\d+)?)/', views.view_poll),
    url(r'^polls', views.create_poll),
]
