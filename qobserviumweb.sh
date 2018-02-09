#!/bin/bash
touch /etc/crontab /etc/cron.*/*
cd /opt/observium
#exec chpst python /opt/observium/run_web_service.py
exec chpst python ./gunicorn -w 2 --error-logfile  gunicorn_err_log -b 0.0.0.0:4504  run_web_service:app
