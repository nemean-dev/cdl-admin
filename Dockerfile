FROM python:3.12-slim-bookworm

WORKDIR /cdl-admin
EXPOSE 80

ENV FLASK_APP=cdl_admin.py

COPY requirements.txt ./
RUN pip install -r requirements.txt
RUN pip install gunicorn psycopg2-binary

COPY cdl_admin.py config.py boot.sh ./
RUN chmod a+x boot.sh

COPY migrations migrations
COPY app app

ENTRYPOINT ["./boot.sh"]