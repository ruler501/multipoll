from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest
import requests
from main.models import Polls, Votes, DistributedPoll, Block, Question, Response
from django.core.exceptions import ObjectDoesNotExist
from collections import defaultdict
import io
import random
from django.views.decorators.csrf import csrf_exempt
import os
import json
import math
import sys
reload(sys)
sys.setdefaultencoding('utf8')


client_id = "4676884434.375651972439"
client_secret = os.environ.get("SLACK_CLIENT_SECRET", "")


def add_poll(timestamp, channel, question, options):
    poll = Polls(timestamp=timestamp, channel=channel, question=question, options=json.dumps(options))
    poll.save()
    return poll


def latest_poll(channel):
    return Polls.objects.filter(channel=channel).latest('timestamp')


def timestamped_poll(timestamp):
    return Polls.objects.filter(timestamp=timestamp)[0]


def update_vote(poll, option, users):
    users = json.dumps(users)
    try:
        vote = Votes.objects.get(poll=poll, option=option)
        vote.users = users
    except ObjectDoesNotExist:
        vote = Votes(poll=poll, option=option, users=users)
    vote.save()
    return vote


def get_all_votes(poll):
    return Votes.objects.filter(poll=poll)


name_cache = {}


def parse_message(message):
    global name_cache
    options = []
    for attachment in message['attachments']:
        for opt in attachment['actions']:
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
                    "token": client_secret,
                    "user": name
                }
                response_data = requests.get(methodUrl, params=methodParams)
                response = response_data.json()
                print response
                res = name
                if "user" in response and "name" in response["user"]:
                    res = '@' + response["user"]["name"]
                vote_list.append(res)
                name_cache[name] = res
        votes[options[i-2]] = vote_list
        
    print [message['text']]
    print votes
    
    question = message['text'].split('*')[1]
    
    return question, options, votes


def check_token(request):
    verifier = os.environ.get("SLACK_POLL_VERIFIER", "")
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
        toAdd = '(' + str(len(votes[options[option]])) + ") " + options[option]
        toAdd += ', '.join(votes[options[option]])
        # Add count + condorcet score here
        text += unicode(toAdd + '\n')
    return text


def format_attachments(options, options_name="option", include_add_more=True):
    actions = []
    for option in options:
        attach = { "name": options_name, "text": option, "type": "button", "value": option }
        actions.append(attach)
    if include_add_more:
        actions.append({ "name": "addMore", "text": "Add More", "type": "button", "value": "Add More" })
    attachments = []
    for i in range(int(math.ceil(len(actions) / 5.0))):
        attachment = { "text": "", "callback_id": options_name + "s", "attachment_type": "default", "actions": actions[5*i: 5*i + 5] }
        attachments.append(attachment)
    
    return json.dumps(attachments)


def create_dialog(payload):
    methodUrl = 'https://slack.com/api/dialog.open'
    methodParams = {
        "token": client_secret,
        "trigger_id": payload['trigger_id'],
        "dialog": {
            "title": "Add an option",
            "state": payload['original_message']['ts'],
            "callback_id": "newOption",
            "elements": [{
                "type": "text",
                "label": "New Option",
                "name": "new_option"
            }]
        }
    }
    methodParams['dialog'] = json.dumps(methodParams['dialog'])
    print "Params", methodParams
    response_data = requests.post(methodUrl, params=methodParams)
    print "Dialog response", response_data.json()


def load_distributed_poll_file(name, lines):
    poll = DistributedPoll()
    poll.name = name
    if poll.name.endswith('.txt'):
        poll.name = poll.name[:-4]
    blocks = []
    questions = []
    current_block = None
    current_question = None
    current_options = []
    on_options = False
    for line in lines:
        line = line.strip()
        if line.startswith("[[Block:"):
            if current_block is not None:
                blocks.append(current_block)
                on_options = False
                if current_question is not None:
                    questions.append(current_question)
                current_question = None
                current_options = []
            line = line[8:-2]
            line = line.strip()
            current_block = Block()
            current_block.name = line
            current_block.poll = poll
        elif len(line) == 0:
            if on_options:
                current_question.options = '\t'.join(current_options)
                questions.append(current_question)
                current_question = None
                current_options = []
                on_options = False
            elif current_question is not None:
                on_options = True
        elif current_question is None:
            if current_block is None:
                raise Exception("Tried to start a question outside of a block\n" + line)
            current_question = Question()
            current_question.question = line
            current_question.block = current_block
        elif on_options:
            current_options.append(line)
    if current_block is not None:
        blocks.append(current_block)
    poll.save()
    print(blocks)
    for block in blocks:
        block.save()
    print(questions)
    for question in questions:
        question.save()
    return poll, blocks, questions


def collapse_lists(lists):
    if len(lists) == 0:
        return lists
    result = [['' for _ in lists[0]]]
    for l in lists:
        for i, item in enumerate(l):
            for res in result:
                if res[i] == '':
                    res[i] = item
                    break
            else:
                result.append(['' for _ in lists[0]])
    return result


def post_message(channel, message, attachments):
    post_message_url = "https://slack.com/api/chat.postMessage"
    post_message_params = {
        "token": client_secret,
        "text": message,
        "channel": channel,
        "icon_url": "https://simplepoll.rocks/static/main/simplepolllogo-colors.png",
        "attachments": attachments
    }
    text_response = requests.post(post_message_url, params=post_message_params)
    print 'response text', text_response.json()


def post_question(channel, question):
    options = question.options.split('\t')
    attachments = format_attachments(options, "qo_"+question.id, False)
    text = format_text(question.question, options, {})
    post_message(channel, text, attachments)


@csrf_exempt
def interactive_button(request):
    errorcode = check_token(request)
    if errorcode is not None:
        return errorcode
    payload = json.loads(request.POST['payload'])
    print payload.items()
    question = ""
    options = []
    votes = defaultdict(list)
    ts = ""
    if payload["callback_id"] == "newOption":
        ts = payload['state']
        poll = timestamped_poll(payload['state'])
        question = poll.question
        options = json.loads(poll.options)
        votes_obj = get_all_votes(poll)
        for vote in votes_obj:
            votes[vote.option] = json.loads(vote.users)
        options.append(payload['submission']['new_option'])
        poll.options = json.dumps(options)
        poll.save()
    elif payload['callback_id'] == "options":
        if payload["actions"][0]["name"] == "addMore":
            ts = payload['original_message']['ts']
            question, options, votes = parse_message(payload['original_message'])
            create_dialog(payload)
        elif payload['actions'][0]["name"] == "option":
            ts = payload['original_message']['ts']
            question, options, votes = parse_message(payload['original_message'])
            lst = votes[payload["actions"][0]["value"]]
            if "@" + payload['user']['name'] in lst:
                votes[payload["actions"][0]["value"]].remove("@" + payload['user']['name'])
            else:
                votes[payload['actions'][0]['value']].append("@" + payload["user"]["name"])
            poll = timestamped_poll(payload['original_message']['ts'])
            update_vote(poll, payload['actions'][0]['value'], votes[payload['actions'][0]['value']])
        text = format_text(question, options, votes)
        attachments = format_attachments(options)
        methodUrl = 'https://slack.com/api/chat.update'
        updateMessage = {
            "token": client_secret,
            "channel": payload['channel']['id'],
            "ts": ts,
            "text": text,
            "attachments": attachments,
            "parse": "full"
        }
        text_response = requests.post(methodUrl, params=updateMessage)
        print 'response text', text_response.json()
    elif payload['callback_id'].startswith('qo_'):
        if payload['actions'][0]['name'].startswith('qo_'):
            question_id = payload['actions'][0]['name'][3:]
            questions = Question.objects.filter(id=question_id)
            if len(questions) != 0:
                users = User.objects.filter(id=payload['user']['name'])
                user = None
                if len(users) == 0:
                    user = User()
                    user.name = payload['user']['name']
                    user.id = payload['user']['name']
                    user.save()
                else:
                    user = users[0]
                question = questions[0]
                response = Response()
                response.option = payload['actions'][0]['text']
                response.question = question
                response.user = user
                response.save()
                options = question.options.split('\t')
                attachments = format_attachments(options, "qo_" + question.id, False)
                text = format_text(question.question, options, {response.option: ['@' + payload['user']['name']]})
                ts = payload['original_message']['ts']
                methodUrl = 'https://slack.com/api/chat.update'
                updateMessage = {
                    "token": client_secret,
                    "channel": payload['channel']['id'],
                    "ts": ts,
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

        attach_string = format_attachments(options)
        postMessage_url = "https://slack.com/api/chat.postMessage"
        postMessage_params = {
            "token": client_secret,
            "text": text,
            "channel": channel,
            "icon_url": "https://simplepoll.rocks/static/main/simplepolllogo-colors.png",
            "attachments": attach_string
        }
        text_response = requests.post(postMessage_url, params=postMessage_params)
        print 'response text', text_response.json()
        return text_response.json()["ts"]  # return message timestamp

    timestamp = sendPollMessage()
    print timestamp
    print add_poll(timestamp, channel, question, options).timestamp

    return HttpResponse()  # Empty 200 HTTP response, to not display any additional content in Slack


@csrf_exempt
def event_handling(request):
    print "Request:", request.body
    request.POST = json.loads(request.body)
    error_code = check_token(request)
    if error_code is not None:
        return error_code

    if request.POST["type"] == "url_verification":
        return HttpResponse(request.POST["challenge"])

    if request.POST["type"] == "event_callback":
        if request.POST["event"]["text"].lower() == "create distributed poll":
            post_message(request.POST["event"]["channel"], "Acknowledged", None)
        if 'files' in request.POST["event"] and len(request.POST["event"]["files"]) > 0:
            response = requests.get(request.POST["event"]["files"][0]["url_private_download"])
            file_like_obj = io.StringIO(response.text)
            lines = file_like_obj.readlines()
            poll, _, _ = load_distributed_poll_file(request.POST["event"]["files"][0]["title"], lines)
            post_message(request.POST["event"]["channel"], "Distributed Poll Created: " + poll.name, None)
        if request.POST["event"]["text"].lower().startswith("dpoll"):
            name = ' '.join(request.POST["event"]["text"].split(' ')[1:])
            polls = DistributedPoll.objects.filter(name=name)
            if len(polls) == 0:
                print("Poll not found")
                post_message(request.POST["event"]["channel"], "Poll not found: " + name, None)
            else:
                poll = polls[0]
                blocks = poll.block_set.all()
                random.shuffle(blocks)
                blocks = blocks[:5]
                for block in blocks:
                    post_message(request.POST["event"]["channel"], '*' + block.name + '*', None)
                    print(block.name)
                    for question in block.question_set.all():
                        print(question.question)
                        post_question(request.POST["event"]["channel"], question)

    return HttpResponse()


@csrf_exempt
def poll_responses(_, poll_name):
    poll = DistributedPoll.objects.filter(name=poll_name)
    blocks = poll.block_set.all()
    questions = []
    for block in blocks:
        questions += block.question_set.all()
    responses = defaultdict(list)
    users = {}
    for i, question in enumerate(questions):
        for response in question.response_se.allt():
            response_list = ['' for _ in questions]
            response_list[i] = response.option
            responses[response.user.id].append(response_list)
            users[response.user.id] = response.user.name
    responses = {key: collapse_lists(value) for key, value in responses.items()}
    results = [','.join([users[key]] + values) for id, values in responses]
    return HttpResponse('\n'.join(results))


@csrf_exempt
def delete_distributedpoll(request, poll_name):
    if request.method != "DELETE":
        return HttpResponseBadRequest()

    poll = get_object_or_404(DistributedPoll, name=poll_name)

    poll.delete()

    return HttpResponse()