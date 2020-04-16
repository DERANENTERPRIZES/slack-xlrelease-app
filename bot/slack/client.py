#from slackclient import SlackClient
import os
import slack
import logging
import json

class Client(object):

    def __init__(self, access_token=None, bot_token=None):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("New Client access_token = %s" % access_token)
        self.logger.debug("New Client bot_token    = %s" % bot_token)
        self.user_client = slack.WebClient(token=access_token)
        self.bot_client  = slack.WebClient(token=bot_token)

    def open_dialog(self, trigger_id=None, dialog=None):
        msg = {}
        msg['trigger_id'] = trigger_id
        msg['dialog'] = dialog
        self.logger.info("open_dialog -> %s" % json.dumps(msg, indent=4, sort_keys=True))
        return self.bot_client.api_call("dialog.open", json=msg)

    def post_message(self, message=None):
        self.logger.debug("post_message -> %s" % json.dumps(message, indent=4, sort_keys=True))
        if "attachments" not in message:
            message['attachments'] = []
        return self.bot_client.chat_postMessage(token=message['token'],
                                                channel=message['channel'],
                                                text=message['text'],
                                                attachments=message['attachments'])

    def update_message(self, message=None):
        self.logger.debug("update_message -> %s" % json.dumps(message, indent=4, sort_keys=True))
        return self.bot_client.api_call("chat.update", json=message)

    def delete_message(self, channel=None, ts=None, token=None):
        msg = {}
        msg["channel"] = channel
        msg["ts"] = ts
        msg["token"] = token
        self.logger.debug("delete_message -> %s" % json.dumps(msg, indent=4, sort_keys=True))
        return self.bot_client.api_call(
            "chat.delete", json=msg)

    def post_ephemeral(self, message=None):
        self.logger.debug("post_ephemeral -> %s" % json.dumps(message, indent=4, sort_keys=True))
        return self.bot_client.api_call(
            "chat.postEphemeral",
            json=message
        )

    def oauth_access(self, client_id=None, client_secret=None, code=None):
        msg = {}
        msg['client_id'] = client_id
        msg['client_secret'] = client_secret
        msg['code'] = code
        self.logger.debug("oauth_access -> %s" % json.dumps(msg, indent=4, sort_keys=True))
        return self.bot_client.api_call("oauth.access", params=msg)

    def get_user_profile(self, token=None, user_id=None):
        msg = {}
        msg['token'] = token
        msg['user'] = user_id
        self.logger.debug("get_user_profile -> %s" % json.dumps(msg, indent=4, sort_keys=True))
        return self.user_client.api_call("users.profile.get", json=msg)
