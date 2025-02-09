#!/bin/bash
while true; do
    sleep 5
    flask db upgrade
    if [[ "$?" == "0" ]]; then
        break
    fi
    echo db upgrade command failed, retrying in 5 secs...
done
echo db upgrade command successful

python create_admin.py

exec gunicorn -b :80 --access-logfile - --error-logfile - cdl_admin:app