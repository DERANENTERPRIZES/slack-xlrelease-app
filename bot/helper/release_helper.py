import json
import logging

from bot.dialogs.release_dialog import get_release_dialog
from bot.helper import Helper
from bot.messages.create_release_input import get_user_input_message
from bot.messages.release_created import get_release_created_message
from bot.messages.show_templates import get_templates_message


class ReleaseHelper(Helper):

    def __init__(self, slack_client=None, db_client=None, vault_client=None):
        self.logger = logging.getLogger(__name__)
        super(ReleaseHelper, self).__init__(slack_client=slack_client, db_client=db_client, vault_client=vault_client)

    def show_templates(self, user_id=None, channel_id=None):
        """
        A method to get all templates from XL Release instance and
        show as list on slack
        """
        xl_release = super(ReleaseHelper, self).get_xl_release(user_id=user_id)
        message = get_templates_message(templates=xl_release.get_templates())
        message['token'] = self.vault_client.get_secret(path="bot_token")
        message['channel'] = channel_id
        if "text" not in message:
            message['text'] = "template list"
        self.logger.info("show_templates -> message = %s" % json.dumps(message, indent=4, sort_keys=True))
        return self.slack_client.post_message(message=message)

    def show_template(self, user=None, channel=None, template_id=None, trigger_id=None, ts=None):
        """
        A method to show dialog to create release for selected template
        """

        template_meta = {
            "message_ts": ts,
            "template_id": template_id
        }
        self.db_client.insert_template_meta(user_id=user["id"],
                                            channel_id=channel["id"],
                                            template_meta=template_meta)

        xl_release = super(ReleaseHelper, self).get_xl_release(user_id=user["id"])
        template = xl_release.get_template(template_id)
        dialog = get_release_dialog(template=template)
        self.slack_client.open_dialog(trigger_id=trigger_id,
                                      dialog=dialog)

        message = get_user_input_message(username=user["name"])
        message['channel'] = channel["id"]
        message["ts"] = ts
        self.slack_client.update_message(message=message)

    def create_release(self, user=None, channel=None, data=None):
        """
        A method to create release with all input information
        """
        xl_release = super(ReleaseHelper, self).get_xl_release(user_id=user["id"])
        template_meta = self.db_client.get_template_meta(user_id=user["id"],
                                                         channel_id=channel["id"])
        self.logger.info("template_meta = %s" % template_meta)
        config_meta = self.db_client.get_xl_release_config(user_id=user["id"])
        self.logger.info("config_meta = %s" % config_meta)

        self.db_client.delete_template_meta(user_id=user["id"],
                                            channel_id=channel["id"])

        template_id = template_meta["template_id"]
        base_url = config_meta["xl_release_url"]

        request_body = {}
        release_variables = {}
        for key, value in data.items():
            if key == "release_title":
                request_body["releaseTitle"] = value
            else:
                release_variables[key] = value

        request_body["variables"] = release_variables
        request_body["autoStart"] = True

        release = xl_release.create_release(template_id=template_id,
                                            request_body=json.dumps(request_body))

        token = self.vault_client.get_secret(path="bot_token")
        user_profile = self.slack_client.get_user_profile(token=token, user_id=user["id"])
        message = get_release_created_message(username=user["name"],
                                              base_url=base_url,
                                              response=release,
                                              profile=user_profile)
        self.logger.info("message = %s" % message)
        self.logger.info("message type is %s" % type(message))
        msg = {}
        #msg = message
        msg['attachments'] = message['attachments']
        msg['channel'] = channel["id"]
        msg['token'] = token
        if "text" not in msg:
            msg["text"] = "Release Created"
        self.logger.info("msg = %s" % msg)
        slack_response = self.slack_client.post_message(message=msg)
        if release.status_code == 200:
            release_data = release.json()
            release_meta = {
                "user": json.dumps(user),
                "channel": json.dumps(channel),
                "status": release_data["status"],
                "ts": slack_response["ts"],
                "message": json.dumps(message)
            }
            self.db_client.insert_release_meta(release_id=release_data["id"], release_meta=release_meta)
        return release
