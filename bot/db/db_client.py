import redis


class DBClient(object):
    CONFIG_CACHE_KEY = "config"
    TEMPLATE_META_CACHE_KEY = "template_meta"
    SLACK_TOKEN_CACHE_KEY = "slack_token"
    RELEASE_TRACK_KEY = "release"
    TASK_TRACK_KEY = "task"

    def __init__(self, host='localhost', port=6379, password="", db=0):
        self.redis_client = redis.StrictRedis(host=host,
                                              port=port,
                                              password=password,
                                              db=db,
                                              decode_responses=True,
                                              charset="utf-8")

    def testClient( self ):
        self.redis_client.set("TEST", "XLR-SLACKBOT")
        self.redis_client.get("TEST")
        

    def get_xl_release_config(self, user_id=None):
        if user_id:
            return self.redis_client.hgetall(name="{}#{}".format(DBClient.CONFIG_CACHE_KEY, user_id))
        else:
            keys = self.redis_client.keys(pattern="{}#*".format(DBClient.CONFIG_CACHE_KEY))
            all_config = []
            for key in keys:
                all_config.append(self.redis_client.hgetall(key))
            return all_config

    def insert_xl_release_config(self, user_id=None, xl_release_config=None):
        self.redis_client.hmset(name="{}#{}".format(DBClient.CONFIG_CACHE_KEY, user_id),
                                mapping=xl_release_config)

    def get_template_meta(self, user_id=None, channel_id=None):
        return self.redis_client.hgetall(name="{}#{}#{}".format(DBClient.TEMPLATE_META_CACHE_KEY, user_id, channel_id))

    def delete_template_meta(self, user_id=None, channel_id=None):
        return self.redis_client.delete("{}#{}#{}".format(DBClient.TEMPLATE_META_CACHE_KEY, user_id, channel_id))

    def insert_template_meta(self, user_id=None, channel_id=None, template_meta=None):
        self.redis_client.hmset(name="{}#{}#{}".format(DBClient.TEMPLATE_META_CACHE_KEY, user_id, channel_id),
                                mapping=template_meta)

    def get_slack_token(self):
        return self.redis_client.hgetall(name="{}".format(DBClient.SLACK_TOKEN_CACHE_KEY))

    def insert_slack_token(self, slack_config=None):
        self.redis_client.hmset(name="{}".format(DBClient.SLACK_TOKEN_CACHE_KEY),
                                mapping=slack_config)

    def get_release_meta(self, release_id=None):
        return self.redis_client.hgetall(name="{}#{}".format(DBClient.RELEASE_TRACK_KEY, release_id))

    def delete_release_meta(self, release_id=None):
        return self.redis_client.delete("{}#{}".format(DBClient.RELEASE_TRACK_KEY, release_id))

    def insert_release_meta(self, release_id=None, release_meta=None):
        return self.redis_client.hmset(name="{}#{}".format(DBClient.RELEASE_TRACK_KEY, release_id),
                                       mapping=release_meta)

    def get_complete_task_id(self, partial_task_id=None):
        keys = self.redis_client.keys(pattern="{}#*/{}".format(DBClient.TASK_TRACK_KEY, partial_task_id))
        for key in keys:
            return key.split("{}#".format(DBClient.TASK_TRACK_KEY))[1]
        pass

    def get_active_releases(self):
        keys = self.__get_release_meta_keys()
        releases = {}
        for key in keys:
            release_id = key.split("{}#".format(DBClient.RELEASE_TRACK_KEY))[1]
            releases[release_id] = self.get_release_meta(release_id=release_id)
        return releases

    def get_release_task_meta(self, release_id=None):
        keys = self.__get_task_meta_keys(release_id=release_id)
        tasks = {}
        for key in keys:
            task_id = key.split("{}#".format(DBClient.TASK_TRACK_KEY))[1]
            tasks[task_id] = self.redis_client.hgetall(key)
        return tasks

    def insert_task_meta(self, task_id=None, task_meta=None):
        return self.redis_client.hmset(name="{}#{}".format(DBClient.TASK_TRACK_KEY, task_id),
                                       mapping=task_meta)

    def delete_release_task_meta(self, release_id=None):
        keys = self.__get_task_meta_keys(release_id=release_id)
        return self.redis_client.delete(*keys)

    def __get_task_meta_keys(self, release_id=None):
        return self.redis_client.keys(pattern="{}#{}/*".format(DBClient.TASK_TRACK_KEY, release_id))

    def __get_release_meta_keys(self):
        return self.redis_client.keys(pattern="{}#*".format(DBClient.RELEASE_TRACK_KEY))
