FROM python

ENV APP_ROOT=/opt/xebialabs
ENV APP_HOME=${APP_ROOT}/slack-xlrelease-app

# Copy bot resources
COPY bot/ ${APP_HOME}/bot/
COPY templates/ ${APP_HOME}/templates/

COPY app.py config.py Pipfile logging.yaml ${APP_HOME}/

WORKDIR ${APP_HOME}

RUN mkdir log

RUN pip install pipenv && \
    pip install --upgrade pip && \
    pip install jinja2 flask pyyaml slackclient slackeventsapi redis hvac polling && \
    pipenv install

EXPOSE 5000
VOLUME ["${APP_HOME}/log"]

ENV CLIENT_ID="" \
    CLIENT_SECRET="" \
    SIGNING_SECRET="" \
    VAULT_TOKEN="" \
    VAULT_URL=http://vault:8200 \
    REDIS_HOST=redis \
    REDIS_PORT=6379 \
    REDIS_PASSWORD="" \
    POLLING_TIME=30

CMD ["pipenv", "run", "gunicorn", "app:app", "-b", "0.0.0.0:5000"]
