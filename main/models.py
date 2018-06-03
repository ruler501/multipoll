from django.db import models
import json

# Create your models here.


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
    timestamp = models.DateTimeField(primary_key=True, unique=True)
    channel = models.CharField(max_length=1000)
    question = models.CharField(max_length=1000)
    options = models.CharField(max_length=1000)

class Votes(models.Model):
    vote_id = models.AutoField(primary_key=True)
    poll = models.ForeignKey(Polls)
    user = models.CharField(max_length=1000)
    content = models.CharField(max_length=1000)



# def get_votes(poll):
#   options = Polls.objects.get(poll_id=poll).json()
#   votes = Votes.objects.filter(poll_id=poll)