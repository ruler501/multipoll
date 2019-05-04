"""simpleslackpoll URL Configuration

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
from main import views

urlpatterns = [
    url(r'^$', views.index, name="index"),
    url(r'^oauthcallback/', views.oauthcallback, name="oauthcallback"),
    url(r'^interactive_button/', views.interactive_button, name="interactive_button"),
    url(r'^poll/', views.poll, name="poll"),
    url(r'^privacy-policy/', views.privacy_policy, name="privacy-policy"),
    url(r'^event_handling/', views.event_handling, name="event_handling"),
    url(r'^(?P<event_name>\w+)/responses$', views.event_responses,)
]
