import os
import argparse
from musescore_utils import create_part_mp3s
from os.path import basename, splitext


def load_lines(file_path):
    with open(file_path, "r") as f:
        lines = [l.strip() for l in f.readlines()]
    return lines


def export_mp3s(ms_file, mp3_folder):
    folder_name = splitext(basename(ms_file))[0]
    subfolder_path = os.path.join(mp3_folder, folder_name)
    if os.path.exists(subfolder_path):
        print(f"Skipping {folder_name} because it already exists")
        return
    create_part_mp3s(ms_file, subfolder_path)
    print(f"Created mp3s for {folder_name}")


def main():
    parser = argparse.ArgumentParser(description="Convert MuseScore files to MP3s.")
    parser.add_argument(
        "input_file", help="Path to a file containing MuseScore file paths."
    )
    parser.add_argument(
        "output_folder", help="Path to the folder where MP3s will be generated."
    )
    args = parser.parse_args()

    ms_files = load_lines(args.input_file)
    os.makedirs(args.output_folder, exist_ok=True)

    for ms_file in ms_files:
        export_mp3s(ms_file, args.output_folder)


if __name__ == "__main__":
    main()
