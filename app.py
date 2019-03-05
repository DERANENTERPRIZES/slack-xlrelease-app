import json
import logging
import jinja2
from flask import Flask, render_template, request, make_response
from slackeventsapi import SlackEventAdapter

from bot import setup_logging
from bot.xl_release_bot import XLReleaseBot

setup_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__, instance_relative_config=False)
app.config.from_object('config')
app.config.from_pyfile('config.py')

xl_release_bot = XLReleaseBot()
events_adapter = SlackEventAdapter(signing_secret=xl_release_bot.verification,
                                   endpoint="/slack",
                                   server=app)

template_loader = jinja2.ChoiceLoader([
    events_adapter.server.jinja_loader,
    jinja2.FileSystemLoader(['templates']),
])
events_adapter.server.jinja_loader = template_loader


@app.route("/install", methods=["GET"])
def before_install():
    """
    This route renders an installation page for our app!
    """
    client_id = xl_release_bot.oauth["client_id"]
    scope = xl_release_bot.oauth["scope"]
    state = xl_release_bot.new_state()
    return render_template("install.html", client_id=client_id, scope=scope, state=state)


@app.route("/thanks", methods=["GET"])
def thanks():
    """
    This route renders a page to thank users for installing our app!
    """
    auth_code = request.args.get('code')
    state = request.args.get('state')
    success = xl_release_bot.auth(code=auth_code, state=state)
    if success:
        return render_template("thanks.html")
    else:
        return before_install()


@app.route("/xlrelease", methods=["POST"])
def xlrelease_command():
    channel_id = request.form.get('channel_id')
    user_id = request.form.get('user_id')

    message = request.form.get('text')
    if "connect" in message:
        xl_release_bot.handle_config_command(request_form=request.form)
    elif "create" in message:
        xl_release_bot.handle_create_release_command(request_form=request.form)
    elif "track" in message:
        xl_release_bot.handle_track_release_command(request_form=request.form)
    else:
        xl_release_bot.show_help(channel_id=channel_id,
                                 user_id=user_id)
    return make_response("", 200)


@events_adapter.on("message")
def handle_message(event_data):
    message = event_data["event"]
    if 'text' in message:
        if "help" in message.get('text'):
            xl_release_bot.show_help(channel_id=message["channel"], user_id=message["user"])
            return make_response("", 200)
    else:
        pass


@app.route("/actions", methods=["GET", "POST"])
def respond():
    slack_payload = json.loads(request.form.get("payload"))
    callback_id = slack_payload["callback_id"]
    if callback_id == "create-release-dialog":
        xl_release_bot.handle_template_callback(request_form=request.form)
    elif callback_id == "add-xl-release-configuration":
        xl_release_bot.handle_config_dialog_trigger(request_form=request.form)
    elif callback_id == "track-release":
        xl_release_bot.handle_release_track_callback(request_form=request.form)
    elif callback_id == "create-release-submit":
        xl_release_bot.handle_release_create_callback(request_form=request.form)
    elif callback_id == "task-action":
        xl_release_bot.handle_task_trigger(request_form=request.form)
    elif "task-action:submit:" in callback_id:
        xl_release_bot.handle_task_action(request_form=request.form)
    else:
        logger.debug("Do not find matching callback id. Slack Payload : {}".format(slack_payload))
    return make_response("", 200)


@app.before_first_request
def before_first_request():
    # find appropriate position for this
    xl_release_bot.recover_restart()

    client_id = xl_release_bot.oauth.get("client_id")
    client_secret = xl_release_bot.oauth.get("client_secret")
    verification = xl_release_bot.verification
    if not client_id:
        logger.info("Can't find Client ID, did you set this env variable?")
    if not client_secret:
        logger.info("Can't find Client Secret, did you set this env variable?")
    if not verification:
        logger.info("Can't find Verification Token, did you set this env variable?")


if __name__ == "__main__":
    app.run()
