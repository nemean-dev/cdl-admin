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

echo creating default admin...
flask cli create-default-admin
if [[ "$?" != "0" ]]; then
    echo "Failed to create default admin user."
    exit 1
fi

exec gunicorn -b :80 --access-logfile - --error-logfile - cdl_admin:app