import json

import polling
import threading
import logging

from bot.helper import Helper, get_task_name
from bot.messages.release_completed import get_release_completed_message
from bot.messages.release_tracking_started import get_release_tracking_message, get_updated_tracking_message
from bot.messages.show_releases import get_releases_message
from bot.messages.task_messages import get_task_messages


class ReleaseTracker(Helper):

    def __init__(self, slack_client=None, db_client=None, vault_client=None):
        super(ReleaseTracker, self).__init__(slack_client=slack_client, db_client=db_client, vault_client=vault_client)
        self.logger = logging.getLogger(__name__)

    def show_releases(self, user_id=None, channel_id=None):
        """
        A method to get all releases from XL Release instance and
        show as list on slack
        """
        xl_release = super(ReleaseTracker, self).get_xl_release(user_id=user_id)
        releases = xl_release.get_releases()
        message = get_releases_message(releases=releases)
        message['channel'] = channel_id
        message['token'] = self.vault_client.get_secret(path="access_token")
        self.logger.info("show_releases -> releases = %s" % message)
        if "text" not in message:
            message['text'] = "Release List"
            #if "attachments" in message:
            #    message['title'] = message["attachments"][0]["title"]
            #    message['text'] = message["attachments"][0]["text"]
            #    message['color'] = message["attachments"][0]["color"]
        self.slack_client.post_message(message=message)

    def send_release_track_message(self, user=None, channel=None, release_id=None, ts=None):
        xl_release = super(ReleaseTracker, self).get_xl_release(user_id=user["id"])
        release_data = xl_release.get_release(release_id)
        token = self.vault_client.get_secret(path="access_token")
        user_profile = self.slack_client.get_user_profile(token=token, user_id=user["id"])
        config_meta = self.db_client.get_xl_release_config(user_id=user["id"])
        base_url = config_meta["xl_release_url"]
        message = get_release_tracking_message(username=user["name"],
                                               release_data=release_data,
                                               base_url=base_url,
                                               profile=user_profile)

        message['channel'] = channel["id"]
        message['token'] = token
        message["ts"] = ts
        if "text" not in message:
            message["text"] = "Release Message"
        self.logger.info("assign_to_me_action -> message = %s" % json.dumps(message, indent=4, sort_keys=True) )
        slack_response = self.slack_client.update_message(message=message)

        release_meta = {
            "user": json.dumps(user),
            "channel": json.dumps(channel),
            "status": release_data["status"],
            "ts": slack_response["ts"],
            "message": json.dumps(message)
        }

        self.db_client.insert_release_meta(release_id=release_id, release_meta=release_meta)

    def track_release(self, user=None, channel=None, release_id=None, polling_time=None):
        known_active_tasks = self.db_client.get_release_task_meta(release_id=release_id)

        polling.poll(target=self.__get_active_tasks,
                     args=(user, channel, release_id, known_active_tasks),
                     step=polling_time, poll_forever=True)
        polling.poll(target=self.__track_release_completed_status,
                     args=(user, channel, release_id),
                     step=polling_time, poll_forever=True)

    def restart_tracking(self, polling_time=None):
        releases = self.db_client.get_active_releases()
        for key, value in releases.items():
            tracker_thread = threading.Thread(target=self.track_release,
                                              args=(json.loads(value["user"]),
                                                    json.loads(value["channel"]),
                                                    key,
                                                    polling_time))
            tracker_thread.start()

    def __get_active_tasks(self, user=None, channel=None, release_id=None, known_active_tasks=None):
        # TODO: Check for Pause and Planned Releases
        self.__get_active_release_status(user=user, channel=channel, release_id=release_id)

        xl_release = super(ReleaseTracker, self).get_xl_release(user_id=user["id"])

        release_data = xl_release.get_release(release_id=release_id)
        config_meta = self.db_client.get_xl_release_config(user_id=user["id"])
        all_user_config_meta = self.db_client.get_xl_release_config()

        base_url = config_meta["xl_release_url"]

        try:
            self.__handle_known_active_tasks(channel=channel, xl_release=xl_release,
                                             release_data=release_data, all_user_config_meta=all_user_config_meta,
                                             base_url=base_url, known_active_tasks=known_active_tasks)

            response = xl_release.get_active_tasks(release_id)
            if response.status_code == 200:
                active_tasks = response.json()
                if active_tasks:
                    for task in active_tasks:
                        if task["type"] not in ["xlrelease.ParallelGroup", "xlrelease.SequentialGroup"]:
                            self.__handle_task_messages(channel=channel, xl_release=xl_release,
                                                        task=task, release_data=release_data,
                                                        all_user_config_meta=all_user_config_meta,
                                                        base_url=base_url, known_active_tasks=known_active_tasks)
                    return False
                elif release_data["status"] in ["PLANNED", "PAUSED"]:
                    return False
                else:
                    return True
            else:
                return True
        except Exception:
            self.logger.exception("Exception Occurred")

    def __handle_known_active_tasks(self, channel=None, xl_release=None, release_data=None,
                                    all_user_config_meta=None, base_url=None, known_active_tasks=None):
        for key, value in known_active_tasks.items():
            if value["status"] != "COMPLETED" or value["status"] != "SKIPPED":
                current_task = xl_release.get_task(key)
                if current_task["status"] in ["COMPLETED", "SKIPPED", "ABORTED"]:
                    self.__handle_task_messages(channel=channel, xl_release=xl_release,
                                                task=current_task, release_data=release_data,
                                                all_user_config_meta=all_user_config_meta,
                                                base_url=base_url, known_active_tasks=known_active_tasks)

    def __handle_task_messages(self, channel=None, xl_release=None, task=None, release_data=None,
                               all_user_config_meta=None, base_url=None, known_active_tasks=None):
        task_type = get_task_name(xl_release, task["type"])
        message = get_task_messages(release_title=release_data["title"],
                                    task=task,
                                    task_type=task_type,
                                    all_user_config_meta=all_user_config_meta,
                                    base_url=base_url)

        if task["id"] not in known_active_tasks:
            message['channel'] = channel['id']
            message['token'] = self.vault_client.get_secret(path="access_token")
            if "text" not in message:
                message["text"] = "Task Message"
            result = self.slack_client.post_message(message=message)
            known_active_tasks[task["id"]] = {
                "ts": result["ts"],
                "status": task["status"]
            }
        elif task["id"] in known_active_tasks and \
                known_active_tasks[task["id"]]["status"] != task["status"]:
            self.slack_client.delete_message(channel=channel["id"],
                                             ts=known_active_tasks[task["id"]]["ts"],
                                             token=self.vault_client.get_secret(path="access_token") )
            message['channel'] = channel["id"]
            message['token'] = self.vault_client.get_secret(path="access_token")
            if "text" not in message:
                message["text"] = "Task Message"
            result = self.slack_client.post_message(message=message)
            known_active_tasks[task["id"]]["ts"] = result["ts"]
            known_active_tasks[task["id"]]["status"] = task["status"]

        self.db_client.insert_task_meta(task_id=task["id"],
                                        task_meta=known_active_tasks[task["id"]])

    def __get_active_release_status(self, user=None, channel=None, release_id=None):
        xl_release = super(ReleaseTracker, self).get_xl_release(user_id=user["id"])
        release_data = xl_release.get_release(release_id)
        release_meta = self.db_client.get_release_meta(release_id=release_id)
        message = get_updated_tracking_message(message=json.loads(release_meta["message"]),
                                               release_data=release_data)
        message['channel'] = channel["id"]
        message["ts"] = release_meta["ts"]
        message['token'] = self.vault_client.get_secret(path="access_token")
        if "text" not in message:
            message["text"] = "Update Message"
        self.slack_client.update_message(message=message)

    def __track_release_completed_status(self, user=None, channel=None, release_id=None):
        xl_release = super(ReleaseTracker, self).get_xl_release(user_id=user["id"])
        release_data = xl_release.get_release(release_id)
        if release_data["status"] in ["COMPLETED", "ABORTED"]:
            config_meta = self.db_client.get_xl_release_config(user_id=user["id"])
            base_url = config_meta["xl_release_url"]
            token = self.vault_client.get_secret(path="access_token")
            user_profile = self.slack_client.get_user_profile(token=token, user_id=user["id"])
            message = get_release_completed_message(username=user["name"],
                                                    base_url=base_url,
                                                    release_data=release_data,
                                                    profile=user_profile)
            message['channel'] = channel["id"]
            message['token'] = token
            if "text" not in message:
                message["text"] = "Release Completed"
            self.slack_client.post_message(message=message)
            all_user_config_meta = self.db_client.get_xl_release_config()
            known_active_tasks = self.db_client.get_release_task_meta(release_id=release_id)
            self.__handle_known_active_tasks(channel=channel, xl_release=xl_release,
                                             release_data=release_data, all_user_config_meta=all_user_config_meta,
                                             base_url=base_url, known_active_tasks=known_active_tasks)

            self.db_client.delete_release_meta(release_id=release_id)
            self.db_client.delete_release_task_meta(release_id=release_id)
            return True
        else:
            return False
