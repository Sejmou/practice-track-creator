#!/bin/bash
# sets up tmux with three panes for all required services for debugging on your local machine
# - flask_app
# - celery_worker
# - redis (used as a broker for celery)
#
# Note: assumes that the following is installed on your machine:
# - docker
# - tmux
# - watchmedo (python package required for hot reload of celery worker, install via `pip install watchdog`)
#
# If less than 3 panes show up, probably one of the services couldn't launch because the port was already allocated or due to some other error.
# To kill anything running on a particular port, just run:
# kill -9 $(lsof -t -i :<port_number>) (e.g. kill -9 $(lsof -t -i :5000))

# start detached tmux session with redis
tmux new-session -d -s audio_api_dev "docker run -p 6379:6379 redis"

# create new pane and run flask app in it
tmux split-window -vt audio_api_dev "flask -A src/flask_app run --debug"

# create another pane and start celery worker in it (watching for changes) (see also: https://celery.school/posts/auto-reload-celery-on-code-changes/)
# for some reason -A src/celery_worker doesn't work, so cd into the directory first
# I also need to load .env before switching to the celery_worker directory to get the correct env variables
tmux split-window -vt audio_api_dev "source .env && cd src && watchmedo auto-restart --directory=./celery_worker --pattern='*.py' --recursive -- celery -A celery_worker worker --concurrency=1 --loglevel=INFO"

# set layout to even-vertical
tmux select-layout -t audio_api_dev even-vertical

# attach to tmux session
tmux attach-session -t audio_api_dev