import io
import json
import logging
import math
import os
import random
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import requests
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from main.models import Block, DistributedPoll, Polls, Question, Response, User, Votes

logger = logging.getLogger(__name__)


def set_log_level(key: str = 'SIMPLEPOLL_LOGLEVEL', default: int = logging.INFO) -> None:
    default_string = logging.getLevelName(default)
    log_level_name = os.environ.get(key, default_string)
    log_levels = {
        'NOTSET': logging.NOTSET,
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'WARN': logging.WARN,
        'ERROR': logging.ERROR,
        'FATAL': logging.FATAL,
        'CRITICAL': logging.CRITICAL
    }
    try:
        log_level = log_levels[log_level_name]
        logging.basicConfig(level=log_level)
        logger.setLevel(log_level)
    except KeyError:
        logging.basicConfig(level=logging.NOTSET)
        logger.setLevel(logging.NOTSET)
        logger.error("Could not find the appropriate log level", exc_info=True)


set_log_level()

client_id = "4676884434.375651972439"
client_secret = os.environ.get("SLACK_CLIENT_SECRET", "")
bot_secret = os.environ.get("SLACK_BOT_SECRET", "")


def add_poll(timestamp: str, channel: str, question: str, options: List[str]) -> Polls:
    poll = Polls(timestamp=timestamp, channel=channel, question=question, options=json.dumps(options))
    poll.save()
    return poll


def timestamped_poll(timestamp: str) -> Polls:
    return Polls.objects.filter(timestamp=timestamp)[0]


def update_vote(poll: Polls, option: str, users: List[str]) -> Votes:
    users_str = json.dumps(users)
    try:
        vote = Votes.objects.get(poll=poll, option=option)
        vote.users = users_str
    except ObjectDoesNotExist:
        vote = Votes(poll=poll, option=option, users=users_str)
    vote.save()
    return vote


def get_all_votes(poll: Polls) -> List[Votes]:
    return poll.votes_set.all()


name_cache: Dict[str, str] = {}


def parse_message(message: Dict) -> Tuple[str, List[str], Dict[str, List[str]]]:
    global name_cache
    options: List[str] = []
    for attachment in message['attachments']:
        for opt in attachment['actions']:
            if opt['name'] != 'addMore':
                options.append(opt['text'])

    votes: Dict[str, List[str]] = defaultdict(list)
    for i, line in enumerate(message['text'].split('\n')):
        if i < 2 or i - 2 >= len(options):
            continue
        logger.debug("%s:\t%s", i, line)
        names = options[i - 2].join(line.split(options[i - 2])[1:]).replace('<@', '').replace('>', '').split(', ')
        if '' in names:
            names.remove('')
        vote_list = []
        for name in names:
            if name in name_cache:
                vote_list.append(name_cache[name])
            else:
                method_url = 'https://slack.com/api/users.info'
                method_params = {
                    "token": client_secret,
                    "user": name
                }
                response_data = requests.get(method_url, params=method_params)
                response = response_data.json()
                logger.info(str(response))
                res = name
                if "user" in response and "name" in response["user"]:
                    res = '@' + response["user"]["name"]
                vote_list.append(res)
                name_cache[name] = res
        votes[options[i - 2]] = vote_list

    logger.info(message['text'])
    logger.info(str(votes))

    question = message['text'].split('*')[1]

    return question, options, votes


def format_text(question: str, options: List[str], votes: Dict[str, List[str]]) -> str:
    text = "*" + question + "*\n\n"
    for option in range(0, len(options)):
        to_add = '(' + str(len(votes[options[option]])) + ") " + options[option]
        to_add += ' ' + ', '.join(votes[options[option]])
        # Add count + condorcet score here
        text += to_add + '\n'
    return text


def format_attachments(options: List[str], options_name: str = "option", include_add_more: bool = True) -> str:
    actions = []
    for option in options:
        attach = {"name": options_name, "text": option, "type": "button", "value": option}
        actions.append(attach)
    if include_add_more:
        actions.append({"name": "addMore", "text": "Add More", "type": "button", "value": "Add More"})
    attachments = []
    for i in range(int(math.ceil(len(actions) / 5.0))):
        attachment = {"text": "", "callback_id": options_name + "s",
                      "attachment_type": "default", "actions": actions[5 * i: 5 * i + 5]}
        attachments.append(attachment)

    return json.dumps(attachments)


def create_dialog(payload: Dict) -> None:
    method_url = 'https://slack.com/api/dialog.open'
    method_params = {
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
    method_params['dialog'] = json.dumps(method_params['dialog'])
    logger.info("Params: %s", method_params)
    response_data = requests.post(method_url, params=method_params)
    logger.info("Dialog Response: %s", response_data.json())


def load_distributed_poll_file(name: str, lines: List[str]) -> Tuple[DistributedPoll, List[Block], List[Question]]:
    poll = DistributedPoll()
    poll.name = name
    if poll.name.endswith('.txt'):
        poll.name = poll.name[:-4]
    poll.save()
    blocks: List[Block] = []
    questions: List[Question] = []
    current_block: Optional[Block] = None
    current_question: Optional[Question] = None
    current_options: List[str] = []
    on_options = False
    for line in lines:
        line = line.strip()
        if line.startswith("[[Block:"):
            if current_block is not None:
                blocks.append(current_block)
                on_options = False
                if current_question is not None:
                    current_question.save()  # noqa: T484
                    questions.append(current_question)
                current_question = None
                current_options = []
            line = line[8:-2]
            line = line.strip()
            current_block = Block()
            current_block.name = line
            current_block.poll = poll
            current_block.save()
        elif len(line) == 0:
            if on_options:
                current_question.options = '\t'.join(current_options)  # noqa: T484
                questions.append(current_question)
                current_question.save()  # noqa: T484
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
    return poll, blocks, questions


def collapse_lists(lists: List[List[str]]) -> List[List[str]]:
    if len(lists) == 0:
        return lists
    result = [['' for _ in lists[0]]]
    for l in lists:
        for i, item in enumerate(l):
            for res in result:
                if res[i] == '' and res[0] == l[0]:
                    res[i] = item
                    break
            else:
                result.append(['' for _ in lists[0]])
                result[-1][0] = l[0]
                result[-1][i] = item
    return result


def post_message(channel: str, message: str, attachments: Optional[str] = None, use_client_secret: bool = True) -> str:
    post_message_url = "https://slack.com/api/chat.postMessage"
    post_message_params = {
        "token": client_secret if use_client_secret else bot_secret,
        "text": message,
        "channel": channel,
        "icon_url": "https://simplepoll.rocks/static/main/simplepolllogo-colors.png",
        "attachments": attachments
    }
    text_response = requests.post(post_message_url, params=post_message_params)
    text_response_dict = text_response.json()
    logger.info('Response Text: %s', text_response_dict)
    return text_response_dict['ts']


def update_message(channel: str, ts: str, text: str, attachments: Optional[str] = None,
                   use_client_secret: bool = True) -> None:
    method_url = 'https://slack.com/api/chat.update'
    method_params = {
        "token": client_secret if use_client_secret else bot_secret,
        "channel": channel,
        "ts": ts,
        "text": text,
        "attachments": attachments,
        "parse": "full"
    }
    text_response = requests.post(method_url, params=method_params)
    logger.info("Response Text: %s", text_response.json())


def post_question(channel: str, question: Question) -> None:
    options = question.options.split('\t')
    attachments = format_attachments(options, "qo_" + question.id, False)
    text = format_text(question.question, options, defaultdict(list))
    post_message(channel, text, attachments, False)


def check_token(request: HttpRequest) -> HttpResponse:
    verifier = os.environ.get("SLACK_POLL_VERIFIER", "")
    if request.method != "POST":
        return HttpResponseBadRequest("400 Request should be of type POST.")
    if "token" in request.POST:
        sent_token = request.POST["token"]
    elif "payload" in request.POST and "token" in json.loads(request.POST["payload"]):
        sent_token = json.loads(request.POST["payload"])["token"]
    else:
        return HttpResponseBadRequest("400 Request is not signed!")
    if verifier != sent_token:
        return HttpResponseBadRequest("400 Request is not signed correctly!")
    return None


@csrf_exempt
def interactive_button(request: HttpRequest) -> HttpResponse:
    error_code = check_token(request)
    if error_code is not None:
        return error_code
    payload = json.loads(request.POST['payload'])
    logger.info(str(payload))
    ts = ""
    if payload["callback_id"] == "newOption":
        votes: Dict[str, List[str]] = defaultdict(list)
        poll = timestamped_poll(payload['state'])
        options: List[str] = json.loads(poll.options)
        votes_obj = get_all_votes(poll)
        for vote in votes_obj:
            votes[vote.option] = json.loads(vote.users)
        options.append(payload['submission']['new_option'])
        poll.options = json.dumps(options)
        poll.save()
    elif payload['callback_id'] == "options":
        question = ""
        options = []
        votes = defaultdict(list)
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
        update_message(payload['channel']['id'], ts, text, attachments)
    elif payload['callback_id'].startswith('qo_'):
        if payload['actions'][0]['name'].startswith('qo_'):
            question_id = payload['actions'][0]['name'][3:]
            questions = Question.objects.filter(id=question_id)
            if len(questions) != 0:
                users = User.objects.filter(id=payload['user']['name'])
                if len(users) == 0:
                    user = User()
                    user.name = payload['user']['name']
                    user.id = payload['user']['name']
                    user.save()
                else:
                    user = users[0]
                question_obj = questions[0]
                response = Response()
                response.option = payload['actions'][0]['value']
                response.question = question_obj
                response.user = user
                response.save()
                # TODO: Load all responses to this question by this user and populate votes with that
                options = question_obj.options.split('\t')
                attachments = format_attachments(options, "qo_" + question_obj.id, False)
                votes = defaultdict(list)
                votes[response.option] = [payload['user']['name']]
                text = format_text(question_obj.question, options, votes)
                ts = payload['original_message']['ts']
                update_message(payload['channel']['id'], ts, text, attachments, False)

    return HttpResponse()


@csrf_exempt
def slash_poll(request: HttpRequest) -> HttpResponse:
    error_code = check_token(request)
    if error_code is not None:
        return error_code
    logger.info(str(request.POST))
    channel = request.POST["channel_id"]
    data = request.POST["text"]

    data = data.replace(u'\u201C', '"')
    data = data.replace(u'\u201D', '"')

    items = data.split('"')

    question = items[1]
    options = []
    for i in range(1, len(items) + 1):
        if i % 2 == 0 and i > 2:
            options.append(items[i - 1])
    # all data ready for initial message at this point
    logger.debug("Options: %s", options)

    text = format_text(question, options, votes=defaultdict(list))
    attachments = format_attachments(options)
    timestamp = post_message(channel, text, attachments)
    add_poll(timestamp, channel, question, options)

    return HttpResponse()  # Empty 200 HTTP response, to not display any additional content in Slack


@csrf_exempt
def event_handling(request: HttpRequest) -> HttpResponse:
    logger.info("Request: %s", request.body)
    request.POST = json.loads(request.body)
    error_code = check_token(request)
    if error_code is not None:
        return error_code

    if request.POST["type"] == "url_verification":
        return HttpResponse(request.POST["challenge"])
    elif request.POST["type"] == "event_callback":
        if request.POST["event"]["type"] == "file_shared":
            file_id = request.POST["event"]["file"]["id"]
            file_response = requests.get("https://slack.com/api/files.info?token=" + client_secret + "&file=" + file_id)
            file_response_dict: Dict = file_response.json()
            logger.info("File Response: %s", file_response_dict)
            response = requests.get(file_response_dict['file']['url_private_download'],
                                    headers={"Authorization": "Bearer " + client_secret})
            file_like_obj = io.StringIO(response.text)
            lines = file_like_obj.readlines()
            try:
                poll, _, _ = load_distributed_poll_file(file_response_dict['file']["title"], lines)
                post_message(request.POST["event"]["channel_id"], "Distributed Poll Created: " + poll.name, None, True)
            except IntegrityError:
                logger.info("Poll already existed.", exc_info=True)
                post_message(request.POST["event"]["channel_id"],
                             "Could not create distributed poll a poll with name \""
                             + file_response_dict['file']['title'] + "\" already exists.", None, False)
        elif request.POST["event"]["type"] == 'message' and request.POST["event"]["text"].lower().startswith("dpoll"):
            name = ' '.join(request.POST["event"]["text"].split(' ')[1:])
            polls = DistributedPoll.objects.filter(name=name)
            if len(polls) == 0:
                logger.info("Poll not found")
                post_message(request.POST["event"]["channel"], "Poll not found: " + name, None, False)
            else:
                poll = polls[0]
                blocks = list(poll.block_set.all())
                random.shuffle(blocks)
                blocks = blocks[:2]
                for block in blocks:
                    post_message(request.POST["event"]["channel"], '*' + block.name + '*', None, False)
                    for question in block.question_set.all():
                        post_question(request.POST["event"]["channel"], question)

    return HttpResponse()


@csrf_exempt
def poll_responses(request: HttpRequest, poll_name: str) -> HttpResponse:
    if request.method != "GET":
        return HttpResponseBadRequest()

    poll = get_object_or_404(DistributedPoll, name=poll_name)
    blocks = poll.block_set.all()
    questions: List[Question] = []
    for block in blocks:
        questions += block.question_set.all()
    responses: Dict[str, List[List[str]]] = defaultdict(list)
    users = {}
    headers = ["Username"]
    for i, question in enumerate(questions):
        headers.append(question.question)
        for response in question.response_set.all():
            response_list = ['' for _ in questions]
            response_list[i] = response.option
            responses[response.user.id].append(response_list)
            users[response.user.id] = response.user.name
    responses = {key: collapse_lists(value) for key, value in responses.items()}
    logger.debug("Collapsed responses: %s", responses.values())
    results = [users[userid] + '\t' + '\t'.join(l) for userid, values in responses.items() for l in values]
    results = ['\t'.join(headers)] + results
    return HttpResponse('\n'.join(results))


@csrf_exempt
def delete_distributedpoll(request: HttpRequest, poll_name: str) -> HttpResponse:
    if request.method != "DELETE":
        return HttpResponseBadRequest()

    poll = get_object_or_404(DistributedPoll, name=poll_name)

    poll.delete()

    return HttpResponse()
