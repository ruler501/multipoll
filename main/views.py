import io
import json
import logging
import math
import os
import random
import time
from collections import defaultdict
from datetime import timezone
from typing import Dict, List, Optional, Tuple

import requests
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from main.models import Block, DistributedPoll, Poll, Question, Response, User, Vote

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


def add_poll(timestamp: str, channel: str, question: str, options: List[str]) -> Poll:
    poll = Poll(timestamp=timestamp, channel=channel, question=question, options=options)
    poll.save()
    return poll


def timestamped_poll(timestamp: str) -> Poll:
    return get_object_or_404(Poll, timestamp=timestamp)


def get_all_votes(poll: Poll) -> List[Vote]:
    return poll.vote_set.all()


def find_or_create_user(user: Dict) -> User:
    return User.objects.get_or_create(name=user['name'])[0]


def order_options(options: List[str], votes: List[List[str]]) -> Tuple[List[str], List[List[str]]]:
    pairs = [(option, vote) for option, vote in zip(options, votes)]
    pairs.sort(key=lambda x: len(x[1]))
    return tuple(zip(*pairs))


def format_text(question: str, options: List[str], votes: List[List[str]]) -> str:
    text = "*" + question + "*\n\n"
    for index, option in enumerate(options):
        to_add = '(' + str(len(votes[index])) + ") " + option
        to_add += ' ' + ', '.join([f'@{username}' for username in votes[index]])
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
    logger.info("Dialog Response Body: %s", response_data.content)
    response_data.raise_for_status()


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
                current_question.options = current_options  # noqa: T484
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
    if current_question is not None and on_options:
        current_question.options = current_options  # noqa: T484
        questions.append(current_question)
        current_question.save()  # noqa: T484
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
    body_dict = {
        "text": message,
        "channel": channel,
        "icon_url": "https://simplepoll.rocks/static/main/simplepolllogo-colors.png",
        "attachments": attachments
    }
    headers = {"Authorization": f"Bearer {client_secret if use_client_secret else bot_secret}"}
    text_response = requests.post(post_message_url, headers=headers, json=body_dict)
    logger.info('Post Response Body: %s', text_response.content)
    text_response.raise_for_status()
    text_response_dict = text_response.json()
    return text_response_dict['ts']


def update_message(channel: str, timestamp: str, text: str, attachments: Optional[str] = None,
                   use_client_secret: bool = True) -> None:
    method_url = 'https://slack.com/api/chat.update'
    body_dict = {
        "channel": channel,
        "ts": timestamp,
        "text": text,
        "attachments": attachments,
        "parse": "full"
    }
    # Content-type is automatically set since we use the json parameter
    headers = {"Authorization": f"Bearer {client_secret if use_client_secret else bot_secret}"}
    text_response = requests.post(method_url, headers=headers, json=body_dict)
    logger.info("Update Response Body: %s", text_response.content)
    text_response.raise_for_status()


def post_question(channel: str, question: Question) -> None:
    attachments = format_attachments(question.options, "qo_" + question.id, False)
    responses = question.responses
    text = format_text(question.question, question.options, responses)
    post_message(channel, text, attachments, False)


def poll_to_slack_timestamp(poll: Poll) -> str:
    timestamp_datetime = poll.timestamp
    logger.info("Timestamp: (%s) - %s", ts_ts, type(ts_ts))
    try:
        timestamp_float = timestamp_datetime.replace(tzinfo=timezone.utc).timestamp()
        timestamp = f"{timestamp_float:17.6f}"
        logger.info("Timestamp Corrected: (%s) - %s", timestamp, type(timestamp))
    except:
        logger.error("ts_ts was not a datetime as expected.", exc_info=True)
        timestamp = timestamp_datetime

    return timestamp


def post_poll(channel: str, poll: Poll) -> str:
    text = format_text(poll.question, poll.options, poll.votes)
    attachments = format_attachments(poll.options)
    return post_message(channel, text, attachments)


def update_poll(channel: str, poll: Poll) -> None:
    options, votes = order_options(poll.options, poll.votes)
    text = format_text(poll.question, options, votes)
    attachments = format_attachments(options)
    timestamp = poll_to_slack_timestamp(poll)
    update_message(channel, timestamp, text, attachments)


def check_token(request: HttpRequest) -> Optional[HttpResponse]:
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


def unique_iter(seq, idfun=None):
    """ Originally proposed by Andrew Dalke """
    seen = set()
    if idfun is None:
        for x in seq:
            if x not in seen:
                seen.add(x)
                yield x
    else:
        for x in seq:
            x = idfun(x)
            if x not in seen:
                seen.add(x)
                yield x


def unique_list(seq, idfun=None):  # Order preserving
    return list(unique_iter(seq, idfun))


@csrf_exempt
def status(request: HttpRequest) -> HttpResponse:
    return HttpResponse()


@csrf_exempt
def interactive_button(request: HttpRequest) -> HttpResponse:
    error_code = check_token(request)
    if error_code is not None:
        return error_code
    payload = json.loads(request.POST['payload'])
    logger.info(str(payload))
    if payload["callback_id"] == "newOption":
        poll = timestamped_poll(payload['state'])
        poll.options.append(payload['submission']['new_option'])
        poll.options = unique_list(poll.options)
        poll.save()
        update_poll(payload['channel']['id'], poll)
    elif payload['callback_id'] == "options":
        if payload["actions"][0]["name"] == "addMore":
            create_dialog(payload)
        elif payload['actions'][0]["name"] == "option":
            poll = timestamped_poll(payload['original_message']['ts'])
            voted_index = poll.options.index(payload["actions"][0]["value"])
            user = find_or_create_user(payload['user'])
            vote = Vote.objects.filter(poll=poll, option=voted_index, user=user).first()
            if vote is not None:
                vote.delete()
            else:
                Vote.objects.create(poll=poll, option=voted_index, user=user)
            update_poll(payload['channel']['id'], poll)
    elif payload['callback_id'].startswith('qo_'):
        if payload['actions'][0]['name'].startswith('qo_'):
            question_id = payload['actions'][0]['name'][3:]
            question = get_object_or_404(Question, id=question_id)
            user = find_or_create_user(payload['user'])
            responses = Response.objects.filter(question=question, user=user)
            if len(responses) != 0:
                for response in responses:
                    response.delete()
            else:
                response_index = question.options.index(payload['actions'][0]['value'])
                Response.objects.create(option=response_index, question=question, user=user)
            attachments = format_attachments(question.options, "qo_" + question.id, False)
            text = format_text(question.question, question.options, question.responses)
            timestamp = payload['original_message']['ts']
            update_message(payload['channel']['id'], timestamp, text, attachments, False)

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
    options = unique_list(options)
    # all data ready for initial message at this point
    logger.debug("Options: %s", options)

    text = format_text(question, options, votes=[[] for _ in options])
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
            logger.info("File Response Body: %s", file_response.content)
            file_response.raise_for_status()
            file_response_dict: Dict = file_response.json()
            response = requests.get(file_response_dict['file']['url_private_download'],
                                    headers={"Authorization": "Bearer " + client_secret})
            response.raise_for_status()
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
        elif request.POST["event"]["type"] == 'message' \
                and "subtype" not in request.POST["event"]:
            if request.POST["event"]["text"].lower().startswith("dpoll"):
                name = ' '.join(request.POST["event"]["text"].split(' ')[1:]).strip()
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
                            time.sleep(0.5)
            elif request.POST["event"]["text"].lower().startswith("blocksearch"):
                text = request.POST["event"]["text"].replace('\u201c', '"').replace('\u201d', '"')
                name = text.split('"')[1].strip()
                query = text.split('"')[2].strip()
                polls = DistributedPoll.objects.filter(name=name)
                if len(polls) == 0:
                    logger.info("Poll not found")
                    post_message(request.POST["event"]["channel"], "Poll not found: " + name, None, False)
                else:
                    poll = polls[0]
                    blocks = poll.block_set.filter(name__icontains=query)
                    if len(blocks) == 0:
                        logger.info("No matching blocks found")
                        post_message(request.POST["event"]["channel"],
                                     f'No matching blocks found for query "{query}" in poll "{name}"',
                                     None, False)
                    for block in blocks:
                        post_message(request.POST["event"]["channel"], '*' + block.name + '*', None, False)
                        for question in block.question_set.all():
                            post_question(request.POST["event"]["channel"], question)
                            time.sleep(0.5)

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
    headers = ["Username"]
    for i, question in enumerate(questions):
        headers.append(question.question)
        for response in question.response_set.all():
            response_list = ['' for _ in questions]
            response_list[i] = str(response.option)
            responses[response.user.name].append(response_list)
    responses = {key: collapse_lists(value) for key, value in responses.items()}
    logger.debug(f"Collapsed responses: {responses}")
    results = ['\t'.join(headers)] + [name + '\t' + '\t'.join(l) for name, values in responses.items()
                                      for l in values]
    return HttpResponse('\n'.join(results))


@csrf_exempt
def delete_distributedpoll(request: HttpRequest, poll_name: str) -> HttpResponse:
    if request.method != "DELETE":
        return HttpResponseBadRequest()

    poll = get_object_or_404(DistributedPoll, name=poll_name)

    poll.delete()

    return HttpResponse()
