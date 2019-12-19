FROM python:3.7.5-slim-stretch

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    libpq-dev libc6-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 5555

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY uwsgi.ini /app/uwsgi.ini

COPY server.py /app/server.py

CMD uwsgi uwsgi.ini