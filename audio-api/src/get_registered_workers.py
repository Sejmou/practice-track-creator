# quick utility script to get a list of registered workers and tasks
from celery import Celery
from shared.settings import BROKER_URL

# Initialize Celery
app = Celery("your_celery_app", broker=BROKER_URL)

i = app.control.inspect()

print("Registered Workers and Tasks:")
for worker, tasks in i.registered().items():
    print(f"Worker: {worker}")
    for task in tasks:
        print(f"  - {task}")
