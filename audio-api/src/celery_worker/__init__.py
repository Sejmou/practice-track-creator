from celery import Celery
from shared.settings import BROKER_URL


# create custom Celery app that overrides default naming convention
class MyCelery(Celery):
    def gen_task_name(self, name, module):
        # remove prefix for first two hierarchy levels
        module = ".".join(module.split(".")[2:])
        return super().gen_task_name(name, module)


app = MyCelery("audio_processing_tasks", broker=BROKER_URL, backend=BROKER_URL)

# have to import tasks one-by-one so that they are properly registered with celery
# TODO: figure out better way
from .tasks import practice_tracks
