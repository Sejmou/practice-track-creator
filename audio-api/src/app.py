from flask import Flask, request, jsonify, send_file, make_response
import os
from zipfile import ZipFile
import uuid
from flask_cors import CORS
from practice_tracks import create_practice_tracks
from werkzeug.utils import secure_filename
import shutil
import logging

from utils import get_absolute_path
from settings import DEBUG

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO if not DEBUG else logging.DEBUG,
    handlers=[
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "..", "logs/app.log")
        ),
        logging.StreamHandler(),
    ],  # log to file and console
)

app = Flask(__name__)
CORS(app)


@app.route("/practice_tracks", methods=["POST"])
def practice_tracks():
    logging.info("Received request")
    logging.debug(request.files)
    # request.files is a dictionary of files sent in the request
    # theoretically there could have been multiple file uploads with different keys
    # (e.g. "audio_files", "other_files"), but in this case we only have one key: "file"
    files_key = "files"
    if files_key not in request.files:
        return make_response(jsonify({"error": "No files included"}), 400)

    files = request.files.getlist(files_key)
    logging.info(f"Received {len(files)} files:", files)

    if len(files) == 0:
        return make_response(jsonify({"error": "No files uploaded"}, 400))

    # create temp dir
    dir_path = os.path.abspath(os.path.join("uploads", str(uuid.uuid4())))
    os.makedirs(dir_path, exist_ok=True)
    logging.debug(f"Created temp dir at {dir_path}")

    try:
        for file in files:
            if file.filename.endswith(".mp3"):
                file.save(os.path.join(dir_path, secure_filename(file.filename)))
            else:
                return make_response(
                    jsonify({"error": "Only mp3 files are supported"}), 400
                )

        # create practice tracks by reading the files in the temp dir
        temp_file_paths = [
            get_absolute_path(os.path.join(dir_path, file))
            for file in os.listdir(dir_path)
            if file.endswith(".mp3")
        ]
        logging.debug("temp file paths:", temp_file_paths)
        output_path = os.path.join(dir_path, "practice_tracks")
        create_practice_tracks(temp_file_paths, output_path)

        # zip the practice tracks
        zip_path = os.path.join(dir_path, "practice_tracks.zip")
        with ZipFile(zip_path, "w") as zip_file:
            for file in os.listdir(output_path):
                zip_file.write(os.path.join(output_path, file), file)
        return make_response(send_file(zip_path), 200)
    except Exception as e:
        logging.exception(e)
        return make_response(jsonify({"error": "Something went wrong"}), 500)
    finally:
        shutil.rmtree(dir_path)
        logging.debug(f"Deleted temp dir at {os.path.abspath(dir_path)}")


if __name__ == "__main__":
    app.run(debug=DEBUG)
