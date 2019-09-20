import datetime
import logging
import os

from typing import Dict, Optional, List

import requests

from django.core.exceptions import PermissionDenied

logger = logging.getLogger(__name__)

_client_secret = os.environ.get('MPOLLS_SLACK_SECRET', '')
_bot_secret = os.environ.get('MPOLLS_SLACK_BOT_SECRET', '')


def _get_token(use_client_secret: bool = True):
    if use_client_secret:
        secret = _client_secret
    else:
        secret = _bot_secret

    if secret:
        return secret
    else:
        raise PermissionDenied()


def _create_headers(use_client_secret: bool = True):
    # Set the Content-Type so we can be sure charset gets set
    return {"Authorization": f"Bearer {_get_token(use_client_secret)}",
            "Content-Type": "application/json; charset=utf-8"}


def create_dialog(trigger_id: str, title: str, state: str, callback_id: str, elements: List[Dict[str, str]],
                  use_client_secret: bool = True) -> None:
    method_url = 'https://slack.com/api/dialog.open'
    method_params = {
        "trigger_id": trigger_id,
        "dialog": {
            "title": title,
            "state": state,
            "callback_id": callback_id,
            "elements": elements
        }
    }
    logger.info(f"Dialog Params at {datetime.datetime.utcnow().timestamp():.6f}: {method_params}")
    response_data = requests.post(method_url, json=method_params, headers=_create_headers(use_client_secret))
    logger.info(f"Dialog Response Status({response_data.status_code}) at {datetime.datetime.utcnow().timestamp():.6f} Body: {response_data.content}")
    response_data.raise_for_status()


def post_message(channel: str, message: str, attachments: Optional[str] = None, use_client_secret: bool = True) -> str:
    post_message_url = "https://slack.com/api/chat.postMessage"
    body_dict = {
        "text": message,
        "channel": channel,
        "icon_url": "https://simplepoll.rocks/static/main/simplepolllogo-colors.png",
        "attachments": attachments
    }
    logger.debug(f'Post Params: {body_dict}')
    text_response = requests.post(post_message_url, headers=_create_headers(use_client_secret), json=body_dict)
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
    logger.info(f"Update Params: {body_dict}")
    text_response = requests.post(method_url, headers=_create_headers(use_client_secret), json=body_dict)
    logger.info("Update Response Body: %s", text_response.content)
    text_response.raise_for_status()
