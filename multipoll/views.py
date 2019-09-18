import json
import logging
import os
from typing import Optional

from django.core import serializers
from django.db import models
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from multipoll import utils, slack
from multipoll.forms import NameAndSecretForm, FullApprovalVoteForm
from multipoll.models import ApprovalPoll, User
from multipoll.models.approvalpoll import FullApprovalVote, PartialApprovalVote

logger = logging.getLogger(__name__)


def check_token(request: HttpRequest) -> Optional[HttpResponse]:
    verifier = os.environ.get("POLLS_SLACK_VERIFIER", "")
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


def normalize_post(request: HttpRequest) -> None:
    if getattr(request, "POST") is None:
        request.POST = json.loads(request.body)
    logger.info(f'Request: {request.POST}')


@csrf_exempt
def server_status(request: HttpRequest) -> HttpResponse:
    return HttpResponse()


@csrf_exempt
def interactive_button(request: HttpRequest) -> HttpResponse:
    normalize_post(request)
    
    error_code = check_token(request)
    if error_code is not None:
        return error_code
    
    payload = json.loads(request.POST['payload'])
    logger.info(f'Payload: {payload}')
    if payload["callback_id"] == "newOption":
        poll = ApprovalPoll.timestamped(payload['state'])
        poll.options.append(payload['submission']['new_option'])
        poll.options = utils.unique_list(poll.options)
        poll.save()
        # update_poll(payload['channel']['id'], poll)
    elif payload['callback_id'] == "options":
        if payload["actions"][0]["name"] == "addMore":
            slack.create_dialog(payload)
        elif payload['actions'][0]["name"] == "option":
            poll = ApprovalPoll.timestamped(payload['original_message']['ts'])
            voted_index = poll.options.index(payload["actions"][0]["value"])
            user = User.find_or_create('@' + payload['user'])
            vote = PartialApprovalVote.objects.find_or_create(poll=poll, option=voted_index, user=user)
            vote.weight = not vote.weight
            vote.save()
    return HttpResponse()


@csrf_exempt
def slash_poll(request: HttpRequest) -> HttpResponse:
    normalize_post(request)
    
    error_code = check_token(request)
    if error_code is not None:
        return error_code
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
    options = utils.unique_list(options)
    # all data ready for initial message at this point
    logger.debug("Options: %s", options)

    ApprovalPoll.add(channel, question, options)

    return HttpResponse()  # Empty 200 HTTP response, to not display any additional content in Slack


# noinspection PyPep8Naming
def JsonModelResponse(model: models.Model, status_code: int = 200, location: str = None, request: HttpRequest = None) \
        -> HttpResponse:
    serialized = serializers.serialize('json', [model])
    response = HttpResponse(serialized[1:-1])
    response.status_code = status_code
    if location:
        if request:
            response["Location"] = request.build_absolute_uri(location)
        else:
            response["Location"] = location
    return response


def create_poll(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        poll_data = json.loads(request.body)
        if 'timestamp' in poll_data or 'question' not in poll_data or 'options' not in poll_data:
            return HttpResponseBadRequest()
        question = poll_data['question']
        options = poll_data['options']
        channel = poll_data.get('channel', os.environ.get('POLLS_DEFAULT_CHANNEL', ''))
        poll = ApprovalPoll.add(question=question, options=options, channel=channel)
        poll.save()
        return JsonModelResponse(poll, 201, f'/polls/{poll.timestamp_str}/', request)
    else:
        return HttpResponseBadRequest()


def view_poll(request: HttpRequest, poll_timestamp: str) -> HttpResponse:
    if request.method == "GET":
        poll = ApprovalPoll.timestamped(poll_timestamp)
        form = NameAndSecretForm()
        # noinspection PyUnresolvedReferences
        return render(request, 'nameandsecret.html',
                      {'form': form, 'poll': poll})
    else:
        return HttpResponseBadRequest()


def vote_on_poll(request: HttpRequest, poll_timestamp: str) -> HttpResponse:
    if request.method == "GET":
        submitted_form = NameAndSecretForm(request.GET)
        if submitted_form.is_valid():
            poll = ApprovalPoll.timestamped(poll_timestamp)
            vote = FullApprovalVote.find_or_create_verified(poll,
                                                            submitted_form.cleaned_data['user_name'],
                                                            submitted_form.cleaned_data['user_secret'])
            form = FullApprovalVoteForm(instance=vote)
            # noinspection PyUnresolvedReferences
            return render(request, "voteonpoll.html",
                          {'form': form, 'path': request.get_full_path(force_append_slash=True)})
        else:
            return HttpResponseBadRequest()
    elif request.method == 'POST':
        poll = ApprovalPoll.timestamped(poll_timestamp)
        if request.POST['_method'] == "addvote":
            option = request.POST['option']
            if option in poll.options:
                return HttpResponseBadRequest()
            else:
                poll.options.append(option)
                poll.save()
                return redirect(request.POST['next'])
        elif request.POST['_method'] == 'vote':
            submitted_form = FullApprovalVoteForm(request.POST)
            if submitted_form.is_valid() \
                    and submitted_form.cleaned_data['poll'].timestamp_str == poll_timestamp:
                FullApprovalVote.validate_and_find_existing(submitted_form.cleaned_data['poll'],
                                                            submitted_form.cleaned_data['user'],
                                                            submitted_form.cleaned_data['user_secret'])
                submitted_form.save()
                return redirect(f"/polls/{poll_timestamp}/results")
            else:
                print(submitted_form)
                print(submitted_form.errors)
                print(submitted_form.cleaned_data['poll'].timestamp_str)
                return HttpResponseBadRequest()
        else:
            return HttpResponseBadRequest()
    else:
        return HttpResponseBadRequest()


def poll_results(request: HttpRequest, poll_timestamp: str) -> HttpResponse:
    if request.method == "GET":
        poll = ApprovalPoll.timestamped(poll_timestamp)
        # noinspection PyUnresolvedReferences
        return render(request, "pollresults.html",
                      {'poll': poll})