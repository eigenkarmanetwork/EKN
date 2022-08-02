#!/bin/bash
gunicorn --bind 0.0.0.0:31415 --log-level debug --access-logfile /var/log/etn/etn_access.log --error-logfile /var/log/etn/etn_error.log app:app
