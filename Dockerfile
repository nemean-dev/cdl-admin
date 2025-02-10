FROM python:3.12

WORKDIR /cdl-admin
EXPOSE 80

ENV FLASK_APP=cdl_admin.py
COPY scripts scripts

COPY requirements.txt ./
RUN pip install -r requirements.txt && pip install gunicorn psycopg

COPY cdl_admin.py config.py boot.sh ./
RUN chmod a+x boot.sh

COPY migrations migrations
COPY app app

ENTRYPOINT ["./boot.sh"]