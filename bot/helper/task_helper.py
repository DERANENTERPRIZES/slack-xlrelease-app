import json
import logging

from bot.dialogs.task_action_dialog import get_task_action_dialog
from bot.helper import Helper
from bot.helper import get_task_name
from bot.messages.task_messages import get_task_messages


class TaskHelper(Helper):

    def __init__(self, slack_client=None, db_client=None, vault_client=None):
        self.logger = logging.getLogger(__name__)
        super(TaskHelper, self).__init__(slack_client=slack_client, db_client=db_client, vault_client=vault_client)

    def assign_to_me_action(self, user=None, channel=None, task_id=None, ts=None):
        config_meta = self.db_client.get_xl_release_config(user_id=user["id"])
        base_url = config_meta["xl_release_url"]
        owner = config_meta["username"]
        all_user_config_meta = self.db_client.get_xl_release_config()

        xl_release = super(TaskHelper, self).get_xl_release(user_id=user["id"])
        response = xl_release.assign_task(task_id, owner)

        if response.status_code == 200:
            task = response.json()
            temp_release_id = task["id"][:task["id"].find('/Phase')]
            task_type = get_task_name(xl_release, task["type"])
            release_title = xl_release.get_release(release_id=temp_release_id)["title"]
            message = get_task_messages(release_title=release_title,
                                        task=task,
                                        task_type=task_type,
                                        all_user_config_meta=all_user_config_meta,
                                        base_url=base_url)
            message['channel'] = channel["id"]
            message["ts"] = ts
            message['token'] = self.vault_client.get_secret(path="access_token")
            self.logger.info("assign_to_me_action -> message = %s" % json.dumps(message, indent=4, sort_keys=True) )
            self.slack_client.update_message(message=message)

    def show_task_action_dialog(self, user=None, trigger_id=None, task_id=None, task_action=None):
        xl_release = super(TaskHelper, self).get_xl_release(user_id=user["id"])
        task = xl_release.get_task(task_id)
        dialog = get_task_action_dialog(task=task,
                                        action=task_action)
        self.slack_client.open_dialog(trigger_id=trigger_id,
                                      dialog=dialog)

    def task_action(self, user=None, partial_task_id=None, action=None, comment=None):
        task_id = self.db_client.get_complete_task_id(partial_task_id=partial_task_id)
        if task_id:
            xl_release = super(TaskHelper, self).get_xl_release(user_id=user["id"])
            request_body = {
                "comment": comment
            }
            xl_release.task_action(task_id, action, json.dumps(request_body))
