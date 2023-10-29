import argparse
import ffmpeg
from typing import List
import os
from tqdm import tqdm

from utils import get_absolute_path


def create_practice_tracks(input_files: List[str], output_dir: str):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    print(f"Creating practice tracks in {output_dir}")
    print(f"Found the following files: {[os.path.basename(f) for f in input_files]}")

    for i in tqdm(range(len(input_files))):
        main_track = input_files[i]
        other_tracks = input_files[:i] + input_files[i + 1 :]
        create_practice_track(main_track, other_tracks, output_dir)


def create_practice_track(
    main_track_path: str,
    other_track_paths: List[str],
    output_dir: str,
    other_tracks_volume: str = "-10dB",
):
    main_filename = os.path.basename(main_track_path)
    print(
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
    ffmpeg.run(temp_out)

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
    ffmpeg.run(out)


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", "-i", default="raw_tracks")
    parser.add_argument("--output_dir", "-o", default="practice_tracks")

    args = parser.parse_args()

    input_dir = get_absolute_path(args.input_dir)
    if not os.path.exists(input_dir):
        raise Exception("Input directory does not exist")

    output_dir = get_absolute_path(args.output_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    ## get all mp3 files in input_dir
    input_files = []
    for file in os.listdir(input_dir):
        if file.endswith(".mp3"):
            input_files.append(os.path.join(input_dir, file))

    if len(input_files) < 2:
        raise Exception(
            f"Input directory must contain at least 2 mp3 files (found only {len(input_files)}"
        )

    create_practice_tracks(input_files, output_dir)
