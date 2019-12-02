import datetime
import inspect
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Union

from django.core import serializers
from django.core.exceptions import SuspiciousOperation
from django.db import models
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from multipoll import slack, utils
from multipoll.forms import FullApprovalVoteForm, FullMultiVoteForm, NameAndSecretForm
from multipoll.models import ApprovalPoll, MultiPoll, PollBase, User

logger = logging.getLogger(__name__)


def check_token(request: HttpRequest) -> Optional[HttpResponse]:
    verifier = os.environ.get("MPOLLS_SLACK_VERIFIER", "")
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
    logger.info(f'Request to {inspect.stack()[1].function} at '
                + f'{datetime.datetime.utcnow().timestamp():.6f}: {request.POST}')


@csrf_exempt
def server_status(request: HttpRequest) -> HttpResponse:
    return HttpResponse()


@csrf_exempt
def interactive_button(request: HttpRequest) -> HttpResponse:
    normalize_post(request)

    error_code = check_token(request)
    if error_code is not None:
        return error_code
    divider = "_"
    payload = json.loads(request.POST['payload'])
    if payload["callback_id"] == "newOption":
        poll = PollBase.timestamped(payload['state'])
        poll.options.append(payload['submission']['new_option'])
        poll.options = utils.unique_list(poll.options)
        poll.save()
    elif payload['callback_id'] == 'int_vote':
        ts, ind_str = payload['state'].split(divider)
        poll = PollBase.timestamped(ts)
        user = User.find_or_create("@" + payload['user']["name"])
        vote = poll.PartialVoteType.find_or_create(poll=poll, user=user, option=int(ind_str))
        vote.weight = payload['submission']['weight']
        vote.save()
    elif payload['callback_id'] == "options":
        event = payload["actions"][0]
        if event["name"] == "addMore":
            elements: List[Dict[str, Union[bool, str]]] = [{
                "type": "text",
                "label": "New Option",
                "name": "new_option"
            }]
            slack.create_dialog(payload['trigger_id'], "Add an Option",
                                payload['original_message']['ts'], "newOption", elements)
        elif event["name"] == "bool_option":
            poll = PollBase.timestamped(payload['original_message']['ts'])
            voted_index = int(event['value'])
            user = User.find_or_create('@' + payload['user']["name"])
            vote = poll.PartialVoteType.find_or_create(poll=poll, option=voted_index, user=user)
            if vote.weight is None:
                vote.weight = False
            vote.weight = not vote.weight
            vote.save()
        elif event['name'] == "int_option":
            poll = PollBase.timestamped(payload['original_message']['ts'])
            ind = int(event['value'])
            option = poll.options[ind]
            state = f"{payload['original_message']['ts']}{divider}{ind}"
            elements = [{
                "type": "text",
                "subtype": "number",
                "label": option,
                "optional": True,
                "name": "weight"
            }]
            user = User.find_or_create("@" + payload['user']['name'])
            existing = poll.PartialVoteType.objects.filter(poll=poll, user=user, option=ind)
            if existing:
                elements[0]["value"] = existing[0].weight
            slack.create_dialog(payload['trigger_id'], "Respond to Poll:", state, 'int_vote',
                                elements)
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

    if request.POST["command"] == "/apoll":
        cls = ApprovalPoll
    elif request.POST["command"] == "/mpoll":
        cls = MultiPoll
    else:
        return HttpResponseBadRequest()
    cls.add(channel, question, options)

    return HttpResponse()  # Empty 200 HTTP response, to not display any additional content in Slack


def JsonModelResponse(model: models.Model, status_code: int = 200,  # noqa: N802
                      location: Optional[str] = None,
                      request: Optional[HttpRequest] = None) -> HttpResponse:
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
        channel = poll_data.get('channel', os.environ.get('MPOLLS_DEFAULT_CHANNEL', ''))
        poll_type = poll_data.get('poll_type', 'approval')
        if poll_type == "approval":
            cls = ApprovalPoll
        elif poll_type == "multi":
            cls = MultiPoll
        else:
            return HttpResponseBadRequest()
        poll = cls.add(question=question, options=options, channel=channel)
        poll.save()
        return JsonModelResponse(poll, 201, poll.get_absolute_url())
    else:
        return HttpResponseBadRequest()


def view_poll(request: HttpRequest, poll_timestamp: str) -> HttpResponse:
    if request.method == "GET":
        poll = PollBase.timestamped(poll_timestamp)
        form = NameAndSecretForm()
        return render(request, 'name_and_secret.html',
                      {'form': form, 'poll': poll})
    else:
        return HttpResponseBadRequest()


def view_vote_on_poll_form(request: HttpRequest, poll_timestamp: str) -> HttpResponse:
    logger.info("vote_on_poll: Received a GET request")
    submitted_form = NameAndSecretForm(request.GET)
    if submitted_form.is_valid():
        poll = PollBase.timestamped(poll_timestamp)
        user_name = submitted_form.cleaned_data['user_name']
        user_secret = submitted_form.cleaned_data['user_secret']
        user = User.find_or_create(user_name)
        vote = poll.FullVoteType.find_and_validate_or_create_verified(poll, user,
                                                                      user_secret)
        form = vote.get_form()
        return render(request, "vote_on_poll.html",
                      {'form': form, 'path': request.get_full_path(force_append_slash=True)})
    else:
        return HttpResponseBadRequest()


def add_poll_option(request: HttpRequest, poll_timestamp: str) -> HttpResponse:
    logger.info("vote_on_poll: method is 'addoption'")
    poll = PollBase.timestamped(poll_timestamp)
    option = request.POST['option']
    if option is None:
        return HttpResponseBadRequest()
    else:
        option = option.strip()
        if option in poll.options or len(option) == 0:
            return HttpResponseBadRequest()
        else:
            poll.options.append(option)
            poll.save()
            return redirect(request.POST['next'])


def submit_vote_on_poll(request: HttpRequest, poll_timestamp: str) -> HttpResponse:
    logger.info("vote_on_poll: method is *vote")
    if request.POST['_method'] == 'approvalvote':
        cls = FullApprovalVoteForm
    elif request.POST['_method'] == 'multivote':
        cls = FullMultiVoteForm
    else:
        return HttpResponseBadRequest()
    submitted_form = cls(request.POST)
    if submitted_form.is_valid():
        logger.info("vote_on_poll: submitted_form is_valid")
        if submitted_form.cleaned_data['poll'].timestamp_str == poll_timestamp:
            logger.info("vote_on_poll: submitted_form has correct timestamp")
            poll = submitted_form.cleaned_data['poll']
            submitted_form.save()
            logger.info("vote_on_poll: submitted_form saved")
            return redirect(poll.get_absolute_url() + "/results")
        else:
            raise SuspiciousOperation("Poll timestamp did not match what was submitted"
                                      + "in the form.")
    else:
        logger.warning(f"Failed to clean submitted form: {submitted_form.cleaned_data} "
                       + f"had errors {submitted_form.errors}")
        return HttpResponseBadRequest()


def vote_on_poll(request: HttpRequest, poll_timestamp: str) -> HttpResponse:
    logger.info(f"In view controller vote_on_poll(<Request>, '{poll_timestamp}')")
    if request.method == "GET":
        return view_vote_on_poll_form(request, poll_timestamp)
    elif request.method == 'POST':
        logger.info("vote_on_poll: Received a POST request")
        if request.POST['_method'] == "addoption":
            return add_poll_option(request, poll_timestamp)
        elif request.POST['_method'].endswith('vote'):
            return submit_vote_on_poll(request, poll_timestamp)
        else:
            return HttpResponseBadRequest()
    else:
        return HttpResponseBadRequest()


LIST_SUFFIX = '_list'
RequestHandler = Callable[..., HttpResponse]


def query_dict_to_kwonlyargs(handler: RequestHandler) \
        -> RequestHandler:
    _, _, varkw, _, kwonlyargs, _, _ = inspect.getfullargspec(handler)

    def wrapped(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        query_dict = request.GET or request.POST
        if query_dict is not None:
            kwnames = kwonlyargs
            if varkw is not None:
                kwnames += request.GET.keys()
            for kwname in kwnames:
                if kwname in query_dict:
                    if kwname.endswith(LIST_SUFFIX):
                        kwargs[kwname] = query_dict.getlist(kwname[:-len(LIST_SUFFIX)])
                    else:
                        kwargs[kwname] = query_dict.get(kwname)
        return handler(request, *args, **kwargs)
    return wrapped


@query_dict_to_kwonlyargs
def poll_results(request: HttpRequest, poll_timestamp: str, *,
                 system: Optional[str] = None) -> HttpResponse:
    if request.method == "GET":
        poll = PollBase.timestamped(poll_timestamp)
        return render(request, "poll_results.html",
                      {'poll': poll, 'system': system})
    else:
        return HttpResponseBadRequest()


@query_dict_to_kwonlyargs
def poll_results_visualization(request: HttpRequest, poll_timestamp: str, *,
                               system: Optional[str] = None) -> HttpResponse:
    if request.method == "GET":
        poll = PollBase.timestamped(poll_timestamp)
        visualization = poll.visualized_results(system)
        if visualization is None:
            return HttpResponseNotFound()
        else:
            response = HttpResponse()
            response.write(visualization)
            response["Content-Type"] = "text/html"
            return response
    else:
        return HttpResponseBadRequest()
