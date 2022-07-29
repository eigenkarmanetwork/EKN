#!/bin/bash
gunicorn --bind 0.0.0.0:31415 app:app
