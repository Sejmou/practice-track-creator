#!/bin/bash
pipreqs . --ignore flask_app --savepath requirements-celery_worker.txt
pipreqs . --ignore celery_worker --savepath requirements-flask_app.txt