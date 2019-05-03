from django.db import models
import json


class Teams(models.Model):
    access_token = models.CharField(max_length=1000)
    team_name = models.CharField(max_length=1000)
    team_id = models.CharField(primary_key=True, max_length=1000)
    incoming_webhook_url = models.CharField(max_length=1000)
    incoming_webhook_configuration_url = models.CharField(max_length=1000)
    last_changed = models.DateTimeField(auto_now = True, auto_now_add = False)
    created = models.DateTimeField(auto_now = False, auto_now_add = True, editable=False)

    def __unicode__(self):
        return str(self.unique_uuid)


class Polls(models.Model):
    timestamp = models.CharField(max_length=100, primary_key=True, unique=True)
    channel = models.CharField(max_length=1000)
    question = models.CharField(max_length=1000)
    options = models.CharField(max_length=1000)


class Votes(models.Model):
    vote_id = models.AutoField(primary_key=True)
    poll = models.ForeignKey(Polls)
    option = models.CharField(max_length=100)
    users = models.CharField(max_length=1000)


class DistributedPoll(models.Model):
    name = models.CharField(max_length=50, unique=True)


class Block(models.Model):
    name = models.CharField(max_length=100)
    poll = models.ForeignKey(DistributedPoll)


class Question(models.Model):
    block = models.ForeignKey(Block)
    question = models.CharField(max_length=1000)
    options = models.CharField(max_length=1000)


class Response(models.Model):
    question = models.ForeignKey(Question)
    option = models.CharField(max_length=100)
    user = models.CharField(max_length=100)
