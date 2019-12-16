FROM python:3.7.4-slim-stretch

EXPOSE 5555

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY uwsgi.ini /app/uwsgi.ini

COPY oauth /app/oauth
COPY server.py /app/server.py

CMD uwsgi uwsgi.ini