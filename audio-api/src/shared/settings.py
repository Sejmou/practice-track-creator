from decouple import config

DEBUG = config("DEBUG", default=False, cast=bool)

# S3
S3_KEY = config("S3_KEY")
S3_SECRET = config("S3_SECRET")
S3_BUCKET = config("S3_BUCKET")
S3_REGION = config("S3_REGION")
S3_ENDPOINT = config("S3_ENDPOINT")

# Celery (Task Queue for background jobs)
BROKER_URL = config("BROKER_URL")
