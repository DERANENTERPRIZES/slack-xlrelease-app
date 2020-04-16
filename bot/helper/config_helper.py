from bot.helper import Helper
from bot.messages.configuration_added import get_configuration_added_message
from bot.xlrelease.xl_release_client import XLReleaseClient
import json
import logging


class ConfigHelper(Helper):

    def __init__(self, slack_client=None, db_client=None, vault_client=None):
        self.logger = logging.getLogger(__name__)
        super(ConfigHelper, self).__init__(slack_client=slack_client, db_client=db_client, vault_client=vault_client)

    def add_configuration(self, user=None, channel=None, xl_release_config=None, secret=None):
        self.db_client.insert_xl_release_config(user_id=user["id"], xl_release_config=xl_release_config)
        self.vault_client.set_secret(path=user["id"], secret=secret)
        xl_release = XLReleaseClient(xl_release_config=xl_release_config,
                                     secret=secret)
        response = xl_release.get_user()

        token = self.vault_client.get_secret(path="bot_token")
        self.logger.info("1. ======================================================")
        user_profile = self.slack_client.get_user_profile(token=token, user_id=user["id"])
        self.logger.info("add_configuration -> user profile = %s" % user_profile )
        self.logger.info("user_profile is type %s" % type(user_profile))
        self.logger.info("2. ======================================================")
        #tmpMsg = json.loads(user_profile)
        #self.logger.info("add_configuration -> user profile = %s" % json.dumps(tmpMsg, indent=4, sort_keys=True))
        message = get_configuration_added_message(username=user["name"],
                                                  xl_release_url=xl_release_config["xl_release_url"],
                                                  response=response,
                                                  profile=user_profile)
        self.logger.info("3. ======================================================")
        self.logger.info("message is type %s" % type(message))
        self.logger.info("add_configuration -> message = %s" % message)
        message['channel'] = channel["id"]
        message['token'] = token
        message['title'] = message["attachments"][0]["title"]
        message['text'] = message["attachments"][0]["text"]
        message['color'] = message["attachments"][0]["color"]

        #tmpMsg = json.loads(message)
        #self.logger.info("add_configuration -> %s" % json.dumps(tmpMsg, indent=4, sort_keys=True))
        self.logger.info("add_configuration -> %s" % message)
        self.logger.info("user_profile is type %s" % type(message))
        self.slack_client.post_message(message=message)
