from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
import requests
from main.models import Teams, Polls, Votes
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from collections import defaultdict
from datetime import datetime
import string
import random
from django.views.decorators.csrf import csrf_exempt
import os
import time
import json
import urllib

# Create your views here.

numbers = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "keycap_ten"]

def add_poll(timestamp, channel, question, options):
    print timestamp
    poll = Polls(timestamp=datetime.fromtimestamp(float(timestamp)), channel=channel, question=question, options=json.dumps(options))
    poll.save()
    return poll

def latest_poll(channel):
    return Polls.objects.filter(channel=channel).latest('timestamp')

def update_vote(poll, user, content):
    content = json.dumps(content)
    try:
        vote = Votes.objects.get(poll=poll, user=user)
        vote.content = content
    except ObjectDoesNotExist:
        vote = Votes(poll=poll, user=user, content=content)
    vote.save()
    return vote

def get_all_votes(poll):
    return Votes.objects.filter(poll=poll)

name_cache = {}
def parse_message(message):
    global name_cache
    options = []
    for opt in message['attachments'][0]['actions']:
        if opt['name'] != 'addMore':
            options.append(opt['text'])
    
    votes = defaultdict(list)
    for i, line in enumerate(message['text'].split('\n')):
        if i < 2 or i - 2 >= len(options):
            continue
        print i, line
        names = options[i-2].join(line.split(options[i-2])[1:]).replace('<@', '').replace('>', '').split(', ')
        if '' in names:
            names.remove('')
        vote_list = []
        for name in names:
            if name in name_cache:
                vote_list.append(name_cache[name])
            else:
                methodUrl = 'https://slack.com/api/users.info'
                methodParams = {
                    "token": "xoxp-295024425040-295165594001-427015731286-44189cac96fe454bbfe6d1daabb584a1",
                    "user": name
                }
                response_data = requests.get(methodUrl, params=methodParams)
                response = response_data.json()
                res = '@' + response["user"]["name"]
                vote_list.append(res)
                name_cache[name] = res
        votes[options[i-2]] = vote_list
        
    print [message['text']]
    print votes
    
    question = message['text'].split('*')[1]
    
    return question, options, votes
    
def index(request):
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(36))
    context = {"state": state}
    # TODO: track and verify state in cookie
    return render(request, "main/index.html", context)


client_id = "4676884434.375651972439"
client_secret = os.environ.get("SLACK_CLIENT_SECRET", "xoxp-295024425040-295165594001-427015731286-44189cac96fe454bbfe6d1daabb584a1")


def oauthcallback(request):
    if "error" in request.GET:
        status = "Oauth authentication failed. You aborted the Authentication process. Redirecting back to the homepage..."
        context = {"status": status}
        return render(request, "main/oauthcallback.html", context)

    code = request.GET["code"]

    url = "https://slack.com/api/oauth.access"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
    }

    r = requests.get(url, params=data)
    query_result = r.json()
    if query_result["ok"]:
        access_token = query_result["access_token"]
        team_name = query_result["team_name"]
        team_id = query_result["team_id"]

        try:
            team = Teams.objects.get(team_id=team_id)
        except ObjectDoesNotExist:
            # new Team (yay!)
            new_team = Teams(access_token=access_token, team_name=team_name, team_id=team_id, last_changed=timezone.now())
            new_team.save()
        else:
            team.access_token = access_token
            team.team_name = team_name
            team.save()

    else:
        status = "Oauth authentication failed. Redirecting back to the homepage..."
        context = {"status": status}
        return render(request, "main/oauthcallback.html", context)

    status = "Oauth authentication successful! You can now start using /poll. Redirecting back to the homepage..."
    context = {"status": status}
    return render(request, "main/oauthcallback.html", context)


def check_token(request):
    verifier = os.environ.get("SLACK_POLL_VERIFIER", "gcoZ4rfrvaEeCCC6tcYByUVX")
    if request.method != "POST":
        return HttpResponseBadRequest("400 Request should be of type POST.")
    sent_token = ""
    if "token" in request.POST:
        sent_token = request.POST["token"]
    elif "payload" in request.POST and "token" in json.loads(request.POST["payload"]):
        sent_token = json.loads(request.POST["payload"])["token"]
    else:
        return HttpResponseBadRequest("400 Request is not signed!")

    if verifier != sent_token:
        return HttpResponseBadRequest("400 Request is not signed correctly!")
    return None

def format_text(question, options, votes):
    text = ""
    text = "*" + question + "*\n\n"
    for option in range(0, len(options)):
        toAdd = ":" + numbers[option] + ": " + options[option]
        toAdd += ', '.join(votes[options[option]])
        # Add count + condorcet score here
        text += unicode(toAdd + '\n')
    return text

def format_attachments(question, options):
    actions = []
    for option in options:
        attach = { "name": "option", "text": option, "type": "button", "value": option }
        actions.append(attach)
    actions.append({ "name": "addMore", "text": "Add More", "type": "button", "value": "Add More" })
    attachments = [{ "text": "Options", "callback_id": "options", "attachment_type": "default", "actions": actions }]
    
    return json.dumps(attachments)


def create_dialog(payload):
    methodUrl = 'https://slack.com/api/dialog.open'
    methodParams = {
        "token": "xoxp-295024425040-295165594001-427015731286-44189cac96fe454bbfe6d1daabb584a1",
        "trigger_id": payload['trigger_id'],
        "dialog": {
            "title": "Add an option",
            "submit_label": "CreateOption",
            "notify_on_cancel": False,
            "state": "Limo",
            "callback_id": "newOption",
            elements: [{
                "type": "text",
                "label": "New Option",
                "name": "new_option"
            }]
        }
    }
    response_data = requests.post(methodUrl, params=methodParams)
    print response_data.json()
        
    
@csrf_exempt
def interactive_button(request):
    errorcode = check_token(request)
    if errorcode is not None:
        return errorcode
    payload = json.loads(request.POST['payload'])
    print payload.items()
    question, options, votes = parse_message(payload['original_message'])
    if payload["callback_id"] == "newOption":
        options.append(payload['submission']['new_option'])
    elif payload["actions"][0]["value"] == "addMore":
        create_dialog(payload)
    elif payload['actions'][0]["value"] == "option":
        lst = votes[payload["actions"][0]["value"]]
        if "@" + payload['user']['name'] in lst:
            votes[payload["actions"][0]["value"]].remove("@" + payload['user']['name'])
        else:
            votes[payload['actions'][0]['value']].append("@" + payload["user"]["name"])
    text = format_text(question, options, votes)
    attachments = format_attachments(question, options)
    methodUrl = 'https://slack.com/api/chat.update'
    updateMessage = {
        "token": "xoxp-295024425040-295165594001-427015731286-44189cac96fe454bbfe6d1daabb584a1",
        "channel": payload['channel']['id'],
        "ts": payload['original_message']['ts'],
        "text": text,
        "attachments": attachments,
        "parse": "full"
    }
    text_response = requests.post(methodUrl, params=updateMessage)
    print 'response text', text_response.json()
    return HttpResponse()

@csrf_exempt
def poll(request):
    errorcode = check_token(request)
    if errorcode is not None:
        return errorcode
    print request.POST.items()
    channel = request.POST["channel_id"]
    data = request.POST["text"]

    data = data.replace(u'\u201C', '"')
    data = data.replace(u'\u201D', '"')

    items = data.split('"')

    question = items[1]
    options = []
    for i in range(1, len(items)+1):
        if i % 2 == 0 and i > 2:
            options.append(items[i-1])
    # all data ready for initial message at this point
    print 'options', options

    def sendPollMessage():
        text = format_text(question, options, votes=defaultdict(list))

        attach_string = format_attachments(question, options)
        print attach_string
        print urllib.quote(attach_string)
        postMessage_url = "https://slack.com/api/chat.postMessage"
        postMessage_params = {
            "token": "xoxp-295024425040-295165594001-427015731286-44189cac96fe454bbfe6d1daabb584a1",
            "text": text,
            "channel": channel,
            "icon_url": "https://simplepoll.rocks/static/main/simplepolllogo-colors.png",
            "attachments": attach_string
        }
        text_response = requests.post(postMessage_url, params=postMessage_params)
        print 'response text', text_response.json()
        return text_response.json()["ts"]  # return message timestamp

    class ChannelDoesNotExist(Exception):
        def __init__(self, *args, **kwargs):
            Exception.__init__(self, *args, **kwargs)


    timestamp = sendPollMessage()
    print timestamp
    print add_poll(timestamp, channel, question, options).timestamp

    return HttpResponse()  # Empty 200 HTTP response, to not display any additional content in Slack

@csrf_exempt
def vote(request):
    errorcode = check_token(request)
    if errorcode is not None:
        return errorcode
    print request.POST.items()
    data = request.POST["text"].split(' ')
    channel = request.POST["channel_id"]
    user = request.POST["user_name"]

    poll = latest_poll(channel)
    timestamp = poll.timestamp
    options = json.loads(poll.options)
    print poll, timestamp, options
    votes = [int(x) for x in data][:len(options)]

    vote = update_vote(poll, user, votes)
    all_votes = get_all_votes(timestamp)
    

    def updatePollMessage():
        text = format_text(poll.question, options, votes=all_votes)
        str_time = unicode('%.6f' % (time.mktime(timestamp.timetuple()) + timestamp.microsecond/1000000.))
        print str_time

        postMessage_url = "https://slack.com/api/chat.update"
        postMessage_params = {
            "token": "xoxp-295024425040-295165594001-427015731286-44189cac96fe454bbfe6d1daabb584a1",
            "channel": channel,
            "text": text,
            "timestamp": str_time,

        }
        print postMessage_params
        text_response = requests.post(postMessage_url, params=postMessage_params)
        print 'sending text', text_response
        return text_response.json()

    result = updatePollMessage()
    print result
    if 'error' in result:
        raise Exception("Failed to update the message")
    return HttpResponse()  # Empty 200 HTTP response, to not display any additional content in Slack


def privacy_policy(request):
    return render(request, "main/privacy-policy.html")
