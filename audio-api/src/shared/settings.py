from decouple import config

DEBUG = config("DEBUG", default=False, cast=bool)

# remote S3 (AWS, Wasabi etc.)
S3_KEY = config("S3_KEY")
S3_SECRET = config("S3_SECRET")
S3_BUCKET = config("S3_BUCKET")
S3_REGION = config("S3_REGION")
S3_ENDPOINT = config("S3_ENDPOINT")

# Local S3 (e.g. MinIO)
LOCAL_S3_KEY = config("LOCAL_S3_KEY")
LOCAL_S3_SECRET = config("LOCAL_S3_SECRET")
LOCAL_S3_BUCKET = config("LOCAL_S3_BUCKET")

# Celery (Task Queue for background jobs)
BROKER_URL = config("BROKER_URL")
