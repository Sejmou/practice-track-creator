from flask import Flask, request, jsonify, make_response
import os
from zipfile import ZipFile
import uuid
from flask_cors import CORS
from werkzeug.utils import secure_filename
import logging
import uuid
import shutil
from celery import Celery
from celery.result import AsyncResult

# note: the DEBUG setting from here only affects my 'business logic' (calls to logging.debug made by my code and any code I use, including s3 client stuff)
# IIUC, it does not affect the logging level of Flask itself (e.g. the logging of request details); you need to pass the debug flag to flask run directly
from shared.settings import DEBUG, BROKER_URL
from shared.s3 import upload_file_to_s3, remove_file_from_s3

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO if not DEBUG else logging.DEBUG,
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(),
    ],  # log to file and console
)


app = Flask(__name__)
app.config.from_mapping(
    CELERY=dict(
        broker_url=BROKER_URL,
        result_backend=BROKER_URL,
        task_ignore_result=True,
    ),
)
# enable CORS TODO: figure out if this is still required
CORS(app)
celery_app = Celery(app.name, broker=BROKER_URL, backend=BROKER_URL)


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
    logging.info(f"Received {len(files)} files: {files}")

    if len(files) == 0:
        return make_response(jsonify({"error": "No files uploaded"}, 400))

    upload_id = uuid.uuid4()
    temp_dir_path = os.path.join(os.path.abspath("tmp"), f"{upload_id}")
    os.makedirs(temp_dir_path, exist_ok=True)

    zip_name = f"input_files.zip"
    zip_path = os.path.join(temp_dir_path, zip_name)

    try:
        # save all mp3 files to the zip file
        with ZipFile(zip_path, "w") as zip_file:
            processed_mp3_count = 0
            for file in files:
                if file.filename.endswith(".mp3"):
                    file.save(
                        os.path.join(temp_dir_path, secure_filename(file.filename))
                    )
                    zip_file.write(
                        os.path.join(temp_dir_path, secure_filename(file.filename)),
                        secure_filename(file.filename),
                    )
                    processed_mp3_count += 1
                else:
                    return make_response(
                        jsonify({"error": "Only mp3 files are supported"}), 400
                    )

            if processed_mp3_count < 2:
                return make_response(
                    jsonify({"error": "At least two mp3 files are required"}), 400
                )

        logging.info(f"Created zip file at {zip_path}")
        s3_relative_path = f"{upload_id}/{zip_name}"
        upload_file_to_s3(zip_path, s3_relative_path)

        """
        The Flask App doesn't import/access the task implementation from the Celery app directly, so we need to create the signature by hand.
        
        The signature wraps a task and its arguments. we can call it in the same way as we would call a task directly.
        To create the signature, we need to specify the task name and the arguments.
        
        The task name follows the scheme
          <task_module>.<task_name> where <task_module> is the name of a module file in the 'tasks' submodule of the celery_worker source code
        
        See also: https://celery.school/posts/how-to-call-a-celery-task-from-another-app/
        """
        create_practice_tracks = celery_app.signature(
            "practice_tracks.create", kwargs={"upload_id": upload_id}
        )

        def on_update(state):
            logging.info(f"Task state: {state}")
            status = state["status"]
            if status == "PROGRESS":
                logging.info(f"Task progress: {state['result']}")
            elif status == "SUCCESS":
                logging.info(f"Task result: {state['result']}")
            elif status == "FAILURE":
                logging.info(f"Task failed: {state['result']}")
            else:
                logging.info(f"Task status: {status}")

        r = create_practice_tracks.apply_async()
        logging.info(
            f"Started worker for practice track creation (upload ID: {upload_id})"
        )
        result = r.get(on_message=on_update, propagate=False)

        logging.info(f"Task result: {result}")

        # inform client that the request was received and is being processed
        return make_response(
            jsonify({"message": "Received upload", "uploadId": upload_id}), 200
        )
    except Exception as e:
        logging.exception(e)
        remove_file_from_s3(s3_relative_path)
        return make_response(jsonify({"error": "Something went wrong"}), 500)
    finally:
        shutil.rmtree(temp_dir_path)
        logging.info(f"Deleted temporary directory at {temp_dir_path}")


if __name__ == "__main__":
    app.run(debug=DEBUG)
