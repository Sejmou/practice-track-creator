FROM python:3.13.0a1-bookworm

RUN mkdir /logs

WORKDIR /app

# install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

COPY requirements.txt requirements.txt 
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/

RUN pip install Gunicorn
# setting large timeout of 5 minutes (300 seconds) as especially on cheap AWS EC2 instances processing can really take a long time
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app", "--access-logfile", "/logs/access.log", "--error-logfile", "/logs/error.log", "--log-level", "debug", "--timeout", "300"]