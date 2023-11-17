import ffmpeg
from typing import List
import os
import logging
import uuid
import shutil
from zipfile import ZipFile
from concurrent.futures import ProcessPoolExecutor, as_completed

from celery_worker import app
from shared.utils import unzip_file
from shared.s3 import download_file_from_s3, upload_file_to_s3, create_presigned_s3_url


@app.task(bind=True, serializer="json")
def create(self, upload_id: str):
    """
    Downloads practice tracks for a given upload_id
    :param upload_id: the id of the upload for which to create practice tracks
    :return: A signature that when called will create the practice tracks
    """
    logging.info(f"Creating practice tracks for upload {upload_id}")

    progress = 0

    def report_progress(progress):
        self.update_state(state="PROGRESS", meta={"progress": progress})

    # download the zip file from S3 to a temporary file
    tmp_root = os.path.abspath("tmp")
    tmp_dir = os.path.join(tmp_root, f"{uuid.uuid4()}")
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        relative_s3_zip_path = f"{upload_id}/input_files.zip"
        file_path = os.path.join(tmp_dir, os.path.basename(relative_s3_zip_path))

        logging.info(
            f"Downloading zip file from S3 (path: {relative_s3_zip_path}) to '{file_path}'"
        )
        download_file_from_s3(relative_s3_zip_path, file_path)
        progress += 0.1
        report_progress(progress)

        logging.info(f"Extracting zip file to {tmp_dir}")
        unzip_file(file_path, tmp_dir)
        progress += 0.1
        report_progress(progress)

        input_files = [
            os.path.join(tmp_dir, file)
            for file in os.listdir(tmp_dir)
            if file.endswith(".mp3")
        ]

        if len(input_files) < 2:
            logging.info(
                f"Cancelling task as there are not enough mp3 files {len(input_files)} instead of at least 2)"
            )
            raise Exception(
                f"Input directory must contain at least 2 mp3 files (found only {len(input_files)}"
            )

        logging.info(
            f"Found the following files: {[os.path.basename(f) for f in input_files]}"
        )

        practice_tracks_dir = os.path.join(tmp_dir, "practice_tracks")
        os.makedirs(practice_tracks_dir, exist_ok=True)

        with ProcessPoolExecutor() as executor:
            futures = []
            for i in range(len(input_files)):
                main_track = input_files[i]
                other_tracks = input_files[:i] + input_files[i + 1 :]
                futures.append(
                    executor.submit(
                        create_practice_track,
                        main_track,
                        other_tracks,
                        practice_tracks_dir,
                    )
                )
            futures.append(
                executor.submit(create_balanced_mix, input_files, practice_tracks_dir)
            )
            # estimate: file processing takes 50% of the total processing time
            file_processing_progress_share = 0.5
            progress_per_task = file_processing_progress_share / len(futures)

            # wait for all futures to complete
            for future in as_completed(futures):
                # not interested in result (which we would get with future.result()) as it is None
                # but, we want to update the progress
                progress += progress_per_task
                report_progress(progress)
                # if we were interested, we could get it with future.result() and store it in a variable like so:
                # result = future.result()
                # print(result)

        # upload the practice tracks to S3
        logging.info(f"Uploading practice tracks to S3")

        # create zip file
        zip_name = "practice_tracks.zip"
        zip_path = os.path.join(tmp_dir, zip_name)
        with ZipFile(zip_path, "w") as zip_file:
            for file in os.listdir(practice_tracks_dir):
                zip_file.write(
                    os.path.join(practice_tracks_dir, file),
                    os.path.basename(file),
                )
        progress += 0.1

        # upload zip file to S3
        s3_relative_path = f"{upload_id}/{zip_name}"
        upload_file_to_s3(zip_path, s3_relative_path)
        progress += 0.2
        report_progress(progress)

        # create presigned url for the zip file
        presigned_url = create_presigned_s3_url(s3_relative_path)
        progress = 1

        return presigned_url

        # TODO: figure out how to chain tasks so that multiprocessing is actually handled by celery
        # possible roadblock: submitting tasks across different workers would mean that the files would not be available locally on the worker
        # subtasks = [
        #     create_practice_track.s(
        #         main_track_path=input_files[i],
        #         other_track_paths=input_files[:i] + input_files[i + 1 :],
        #         output_dir=practice_tracks_dir,
        #     )
        #     for i in range(len(input_files))
        # ]
        # subtasks.append(
        #     create_balanced_mix.s(
        #         track_paths=input_files, output_dir=practice_tracks_dir
        #     )
        # )

        # job = chain(group(subtasks), remove_temporary_files)

        # return job

    except Exception as e:
        logging.error("Error while creating practice tracks")
        logging.exception(e)
        raise e
    finally:
        remove_temporary_files(upload_id)


# @app.task
def create_balanced_mix(
    track_paths: List[str],
    output_dir: str,
):
    filename = "all.mp3"
    logging.debug(f"Creating balanced mix of {len(track_paths)} tracks")
    # get the first track's mean volume (measured in negative dB; volume of 0dB is the maximum volume, so -10dB is quieter than -5)
    # assumption: all tracks have the same mean volume - if this is not the case, results might be unexpected!
    original_mean_volume = get_volume(track_paths[0])

    input_streams = [ffmpeg.input(path, format="mp3") for path in track_paths]

    # Combine the input streams into a single output stream (i.e. audio from all files 'playing' at once)
    # amix is a filter that mixes multiple audio streams into one. however, it only accepts two inputs at a time
    # hence, we need to add the streams one by one
    combined_audio = ffmpeg.filter(
        input_streams, "amix", inputs=len(input_streams), dropout_transition=0
    )

    # Define a temporary output stream and write it to a temporary file
    temp_out_path = os.path.join(output_dir, f"temp_all.mp3")
    temp_out = ffmpeg.output(combined_audio, temp_out_path)
    ffmpeg.run(temp_out, quiet=True)

    # get the mean volume of the temporary output file
    temp_mean_volume = get_volume(temp_out_path)
    # can delete the temporary output file now
    os.remove(temp_out_path)

    volume_diff = original_mean_volume - temp_mean_volume

    # apply the volume difference to the combined audio stream
    combined_audio = ffmpeg.filter(combined_audio, "volume", f"{volume_diff}dB")

    # write the output stream with the volume adjustment to the output file
    out_path = os.path.join(output_dir, filename)
    out = ffmpeg.output(combined_audio, out_path)
    ffmpeg.run(out, quiet=True)


# @app.task
def create_practice_track(
    main_track_path: str,
    other_track_paths: List[str],
    output_dir: str,
    other_tracks_volume: str = "-10dB",
):
    main_filename = os.path.basename(main_track_path)
    logging.debug(
        f"Creating practice track for {main_filename} with {len(other_track_paths)} other tracks"
    )

    # create input streams for each file
    main_stream = ffmpeg.input(main_track_path, format="mp3")
    # get the main track's mean volume (measured in negative dB; volume of 0dB is the maximum volume, so -10dB is quieter than -5)
    original_mean_volume = get_volume(main_track_path)

    input_streams = [main_stream]
    # other tracks should be quieter than the main track => apply volume filter
    for path in other_track_paths:
        input_stream = ffmpeg.input(path, format="mp3").filter(
            "volume", other_tracks_volume
        )
        input_streams.append(input_stream)

    # Combine the input streams into a single output stream (i.e. audio from all files 'playing' at once)
    # amix is a filter that mixes multiple audio streams into one. however, it only accepts two inputs at a time
    # hence, we need to add the streams one by one
    combined_audio = ffmpeg.filter(
        input_streams, "amix", inputs=len(input_streams), dropout_transition=0
    )

    # Define a temporary output stream and write it to a temporary file
    temp_out_path = os.path.join(output_dir, f"temp_{main_filename}")
    temp_out = ffmpeg.output(combined_audio, temp_out_path)
    ffmpeg.run(temp_out, quiet=True)

    # get the mean volume of the temporary output file
    temp_mean_volume = get_volume(temp_out_path)
    # can delete the temporary output file now
    os.remove(temp_out_path)

    volume_diff = original_mean_volume - temp_mean_volume

    # apply the volume difference to the combined audio stream
    combined_audio = ffmpeg.filter(combined_audio, "volume", f"{volume_diff}dB")

    # write the output stream with the volume adjustment to the output file
    out_path = os.path.join(output_dir, os.path.basename(main_track_path))
    out = ffmpeg.output(combined_audio, out_path)
    ffmpeg.run(out, quiet=True)


def remove_temporary_files(upload_id):
    logging.info(f"Removing temporary files for upload {upload_id}")
    tmp_root = os.path.abspath("tmp")
    tmp_dir = os.path.join(tmp_root, f"{upload_id}")
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
        logging.info(f"Removed directory {tmp_dir}")
    else:
        logging.error(f"Directory {tmp_dir} does not exist")


def get_volume(input_path):
    if not os.path.isfile(input_path):
        raise Exception(f"Input path {input_path} is not a file")
    # ffmpeg command from https://superuser.com/a/323127/1185399 (slightly modified to pipe stderr to stdout and grep for the stuff we are interested in)
    cmd = f'ffmpeg -i "{input_path}" -af "volumedetect" -vn -sn -dn -f null /dev/null 2>&1 | grep "mean_volume"'
    # execute the command and get the output
    output = os.popen(cmd).read()
    # parse the output to get the volume (should be in negative dB)
    volume = float(output.split("mean_volume: ")[1].split(" dB")[0])
    return volume
