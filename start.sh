#!/bin/bash
export FLASK_RUN_HOST=0.0.0.0
export FLASK_RUN_PORT=31415
export FLASK_ENV=development
python -m flask run
