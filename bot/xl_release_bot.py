import json
import os
import threading
import logging
from bot.db.db_client import DBClient
from bot.db.vault_client import VaultClient
from bot.helper import get_random_string
from bot.helper.config_helper import ConfigHelper
from bot.helper.release_helper import ReleaseHelper
from bot.helper.release_tracker import ReleaseTracker
from bot.helper.task_helper import TaskHelper
from bot.messages.show_help import get_help, get_connect_help, get_general_error
from bot.messages.slack_installed import get_slack_installed
from bot.slack.client import Client


class XLReleaseBot(object):
    """ Instanciates a Bot object to handle Slack interactions."""

    def __init__(self):
        super(XLReleaseBot, self).__init__()
        self.logger = logging.getLogger(__name__)

        vault_token = os.environ.get("VAULT_TOKEN")
        vault_url = os.environ.get("VAULT_URL")
        self.vault_client = VaultClient(url=vault_url, token=vault_token)

        client_id = os.environ.get("CLIENT_ID")
        self.vault_client.set_secret(path="client_id", secret=client_id)
        self.logger.debug("CLIENT ID = %s" % client_id)

        client_secret = os.environ.get("CLIENT_SECRET")
        self.vault_client.set_secret(path="client_secret", secret=client_secret)
        self.logger.debug("Client Secret = %s" % client_secret)

        vault_token = os.environ.get("VAULT_TOKEN")
        self.vault_client.set_secret(path="vault_token", secret=vault_token)
        self.logger.debug("vault_token = %s" % vault_token)

        vault_url = os.environ.get("VAULT_URL")
        self.vault_client.set_secret(path="vault_url", secret=vault_url)
        self.logger.debug("vault_url = %s" % vault_url)

        redis_host = os.environ.get("REDIS_HOST")
        self.vault_client.set_secret(path="redis_host", secret=redis_host)
        self.logger.info("redis_host = %s" % redis_host)

        redis_port = os.environ.get("REDIS_PORT")
        self.vault_client.set_secret(path="redis_port", secret=redis_port)
        self.logger.info("redis_port = %s" % redis_port)

        redis_pass = os.environ.get("REDIS_PASSWORD")
        self.vault_client.set_secret(path="redis_pass", secret=redis_pass)

        self.polling_time = int(os.environ.get("POLLING_TIME"))
        self.verification = os.environ.get("SIGNING_SECRET")

        self.logger.info("polling_time = %s" % self.polling_time)

        self.oauth = {
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "bot,commands,chat:write:bot,channels:write,users.profile:read,team:read",
            "state": ""
        }


        self.release_channel_meta = {}
        self.xl_release_config = {}

        self.slack_client = Client(access_token="", bot_token="")
        self.db_client = DBClient(host=redis_host, port=redis_port, password=redis_pass)

        #self.vault_client.set_secret(path="access_token", secret=access_token)

    def testRedis(self):
        try:
            self.db_client.testClient()
            result = "SUCCESS"
        except Exception as ex:
            self.logger.error( ex )
            self.logger.error("REDIS Connection Test Failed!")
            result = "FAIL"
        self.logger.info("REDIS Connection Status = %s" % result)
        return result

    def new_state(self):
        self.oauth["state"] = get_random_string(string_length=30)
        self.logger.debug("new state -> new state = %s" % self.oauth["state"])
        return self.oauth["state"]

    def auth(self, code=None, state=None):
        """
        A method to exchange the temporary auth code for an OAuth token
        which is then saved it in memory on our Bot object for easier access.
        """
        ######
        #  ToDo:  I need to figure out what overwrites the "state" in oauth between the /install and /thanks
        #
        if state != self.oauth["state"]:
            self.logger.error("auth -> OAUTH FAIL state = %s/%s" % (state, self.oauth["state"]))
            return False

        self.logger.debug("auth -> Call oauth_access with client_id=%s and code=%s" % ( self.oauth['client_id'], code))
        auth_response = self.slack_client.oauth_access(client_id=self.oauth['client_id'],
                                                       client_secret=self.oauth['client_secret'],
                                                       code=code)
        self.logger.debug("auth-> oauth_access response = %s" % auth_response)
        self.slack_client = Client(access_token=auth_response["access_token"],
                                   bot_token=auth_response["bot"]["bot_access_token"])

        self.logger.debug("auth-> new Slack Client")
        self.vault_client.set_secret(path="access_token",
                                     secret=auth_response["access_token"])

        self.vault_client.set_secret(path="bot_token",
                                     secret=auth_response["bot"]["bot_access_token"])

        msg = get_slack_installed()
        self.logger.info("auth -> get slack installed message %s" % msg)
        msg['channel'] = auth_response["user_id"]
        msg['token'] = auth_response["bot"]["bot_access_token"]
        self.slack_client.post_message(message=msg)
        self.logger.info("auth -> Auth Done!!")
        return True

    def show_help(self, channel_id=None, user_id=None):
        """
        A method to show help!
        """
        msg = get_help()
        msg['token'] = self.vault_client.get_secret(path="bot_access_token")
        msg['channel'] = channel_id
        msg['user'] = user_id
        msg['attachments'] = []
        self.slack_client.post_ephemeral(message=msg)

    def handle_config_command(self, request_form=None):
        text = request_form.get('text')
        command_input = text.split()

        if len(command_input) != 4:
            msg = get_connect_help()
            msg['token'] = self.vault_client.get_secret(path="bot_access_token")
            msg['channel'] = request_form.get('channel_id')
            msg['user'] = request_form.get('user_id')
            msg['attachments'] = []
            self.slack_client.post_ephemeral(message=msg)

        xl_release_config = {
            "slack_user_id": request_form.get('user_id'),
            "xl_release_url": command_input[1],
            "username": command_input[2]
        }
        config_helper = ConfigHelper(slack_client=self.slack_client,
                                     db_client=self.db_client,
                                     vault_client=self.vault_client)
        user = {
            "id": request_form.get('user_id'),
            "name": request_form.get('user_name')
        }
        channel = {
            "id": request_form.get('channel_id'),
            "name": request_form.get('channel_name'),
        }
        config_helper.add_configuration(user=user,
                                        channel=channel,
                                        xl_release_config=xl_release_config,
                                        secret=command_input[3])

    def handle_create_release_command(self, request_form=None):
        user_id = request_form.get('user_id')
        channel_id = request_form.get('channel_id')
        release_helper = ReleaseHelper(slack_client=self.slack_client,
                                       db_client=self.db_client,
                                       vault_client=self.vault_client)
        try:
            release_helper.show_templates(user_id=user_id,
                                          channel_id=channel_id)
        except Exception as e:
            self.logger.exception("Can not retrieve templates.")
            msg = get_general_error()
            msg['token'] = self.vault_client.get_secret(path="bot_access_token")
            msg['channel'] = request_form.get('channel_id')
            msg['user'] = request_form.get('user_id')
            msg['attachments'] = []
            self.slack_client.post_ephemeral(message=msg)

    def handle_template_callback(self, request_form=None):
        payload = json.loads(request_form.get("payload"))
        template_id = payload["actions"][0]["selected_options"][0]["value"]
        trigger_id = payload["trigger_id"]

        release_helper = ReleaseHelper(slack_client=self.slack_client,
                                       db_client=self.db_client,
                                       vault_client=self.vault_client)

        release_helper.show_template(template_id=template_id,
                                     trigger_id=trigger_id,
                                     user=payload["user"],
                                     channel=payload["channel"],
                                     ts=payload["message_ts"])

    def handle_track_release_command(self, request_form=None):
        user_id = request_form.get('user_id')
        channel_id = request_form.get('channel_id')
        release_tracker = ReleaseTracker(slack_client=self.slack_client,
                                         db_client=self.db_client,
                                         vault_client=self.vault_client)
        try:
            release_tracker.show_releases(user_id=user_id,
                                          channel_id=channel_id)
        except Exception:
            self.logger.exception("Can not retrieve releases.")
            msg = get_general_error()
            msg['token'] = self.vault_client.get_secret(path="bot_access_token")
            msg['channel'] = request_form.get('channel_id')
            msg['user'] = request_form.get('user_id')
            msg['attachments'] = []
            if "text" not in msg:
                msg["text"] = "Can not retrieve releases."
            self.slack_client.post_ephemeral(message=msg)

    def handle_release_create_callback(self, request_form=None):
        payload = json.loads(request_form.get("payload"))
        release_helper = ReleaseHelper(slack_client=self.slack_client,
                                       db_client=self.db_client,
                                       vault_client=self.vault_client)

        release = release_helper.create_release(user=payload["user"],
                                                channel=payload["channel"],
                                                data=payload["submission"])
        if release.status_code == 200:
            release_data = release.json()
            release_tracker = ReleaseTracker(slack_client=self.slack_client,
                                             db_client=self.db_client,
                                             vault_client=self.vault_client)
            tracker_thread = threading.Thread(target=release_tracker.track_release,
                                              args=(payload["user"], payload["channel"], release_data["id"], self.polling_time))
            tracker_thread.start()

    def handle_release_track_callback(self, request_form=None):
        payload = json.loads(request_form.get("payload"))
        release_id = payload["actions"][0]["selected_options"][0]["value"]

        release_tracker = ReleaseTracker(slack_client=self.slack_client,
                                         db_client=self.db_client,
                                         vault_client=self.vault_client)

        release_tracker.send_release_track_message(user=payload["user"],
                                                   channel=payload["channel"],
                                                   release_id=release_id,
                                                   ts=payload["message_ts"])
        tracker_thread = threading.Thread(target=release_tracker.track_release,
                                          args=(payload["user"], payload["channel"], release_id, self.polling_time))
        tracker_thread.start()

    def handle_task_trigger(self, request_form=None):
        payload = json.loads(request_form.get("payload"))
        task_action = payload["actions"][0]["name"]
        task_id = payload["actions"][0]["value"]
        trigger_id = payload["trigger_id"]
        task_helper = TaskHelper(slack_client=self.slack_client,
                                 db_client=self.db_client,
                                 vault_client=self.vault_client)
        if task_action == "assign":
            task_helper.assign_to_me_action(user=payload["user"],
                                            channel=payload["channel"],
                                            task_id=task_id,
                                            ts=payload["message_ts"])
        elif task_action in ["complete", "fail", "retry", "skip"]:
            task_helper.show_task_action_dialog(user=payload["user"],
                                                trigger_id=trigger_id,
                                                task_id=task_id,
                                                task_action=task_action)
        else:
            pass

    def handle_task_action(self, request_form=None):
        payload = json.loads(request_form.get("payload"))
        task_data = payload["callback_id"].split(":")
        task_helper = TaskHelper(slack_client=self.slack_client,
                                 db_client=self.db_client,
                                 vault_client=self.vault_client)
        task_helper.task_action(user=payload["user"],
                                partial_task_id=task_data[3],
                                action=task_data[2],
                                comment=payload["submission"]["comment"])

    def recover_restart(self):
        self.logger.info("Enter recover_restart")
        try:
            access_token = self.vault_client.get_secret(path="access_token")
            self.logger.debug("recover_restart access_token = %s" % access_token)
            bot_token = self.vault_client.get_secret(path="bot_token")
            self.logger.debug("recover_restart bot_token = %s" % bot_token)
        except:
            self.logger.error("recover_restart -> Missing Property")
            return

        if access_token and bot_token:
            self.slack_client = Client(access_token=access_token,
                                       bot_token=bot_token)
            release_tracker = ReleaseTracker(slack_client=self.slack_client,
                                             db_client=self.db_client,
                                             vault_client=self.vault_client)
            release_tracker.restart_tracking(self.polling_time)
