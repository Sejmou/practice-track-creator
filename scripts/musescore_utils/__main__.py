import os
import shutil
import zipfile
import xml.etree.ElementTree as ET
import argparse
from os.path import basename, splitext, abspath, dirname
import subprocess

MUSESCORE3_PATH = "/Applications/MuseScore 3.app/Contents/MacOS/mscore"
MUSESCORE4_PATH = "/Applications/MuseScore 4.app/Contents/MacOS/mscore"


def get_part_names(file_path):
    """
    Given a path to a .mscz file, return a list of all part names in the file.
    """
    # Get the element tree from the mscz file
    tree = get_content_tree_from_musescore_file(file_path)

    # Get the root element of the tree
    root = tree.getroot()

    # Get all parts in the score
    parts = get_parts(root)

    part_names = [get_part_name(p) for p in parts]

    return part_names


def create_separate_msczs_for_parts(file_path, out_dir=None):
    """
    Given a path to a .mscz file, create a new .mscz file for each part in the file.
    """
    # Get the element tree from the mscz file
    tree = get_content_tree_from_musescore_file(file_path)

    # Get the root element of the tree
    root = tree.getroot()

    # Get all parts in the score
    parts = get_parts(root)

    if out_dir is None:
        # if no output directory is specified, use the name of the file as the output directory
        # place that directory in the same directory as the input file
        out_dir = os.path.join(
            abspath(dirname(file_path)), f"{splitext(basename(file_path))[0]}_parts"
        )
    os.makedirs(out_dir, exist_ok=True)

    for part in parts:
        part_name = get_part_name(part)
        create_single_part_mscz(file_path, part_name, out_dir)


def create_msczs_with_all_other_parts_silenced_for_every_part_in(
    file_path, out_dir=None
):
    """
    Given a path to a .mscz file, create a new .mscz file for each part in the file. In this file, all parts except the chosen part are silenced.
    """
    # Get the element tree from the mscz file
    tree = get_content_tree_from_musescore_file(file_path)

    # Get the root element of the tree
    root = tree.getroot()

    # Get all parts in the score
    parts = get_parts(root)

    if out_dir is None:
        # if no output directory is specified, use the name of the file as the output directory
        # place that directory in the same directory as the input file
        out_dir = os.path.join(
            abspath(dirname(file_path)), f"{splitext(basename(file_path))[0]}_parts"
        )
    os.makedirs(out_dir, exist_ok=True)

    for part in parts:
        part_name = get_part_name(part)
        silence_all_parts_except(file_path, part_name, out_dir)


def silence_all_parts_except(file_path, part_name, out_dir=None):
    """
    Given a path to a .mscz file, create a new .mscz file containing only the part with the given name.

    The other parts still exist, but are 'silenced' (i.e. any notes are replaced by rests)
    """
    # Get the element tree from the mscz file
    tree = get_content_tree_from_musescore_file(file_path)

    # Get the root element of the tree
    root = tree.getroot()

    # Get all parts in the score
    parts = get_parts(root)

    # Find the part with the given name
    part = next((p for p in parts if get_part_name(p) == part_name), None)
    if part is None:
        raise ValueError(f"No part named {part_name} found in {file_path}")

    # Silence all parts except the one we want to keep
    for p in parts:
        if p != part:
            silence_all_measures_of_part(p, root)

    # remove <Harmony> parent elements from the tree (they will otherwise cause chords to be played back on the exported audio)
    removed_count = 0
    harmony_parents = root.findall(".//Harmony/..")
    for parent in harmony_parents:
        harmony_elements = parent.findall("./Harmony")
        for harmony_element in harmony_elements:
            parent.remove(harmony_element)
            removed_count += 1

    # store the new data in a new musescore file by applying the following steps:
    file_name = os.path.basename(file_path)
    new_file_name = f"{part_name}.mscz"
    shutil.copyfile(file_path, new_file_name)

    # unzip the file (every .mscz file is essentially a zip file)
    file_name_without_extension = os.path.splitext(file_name)[0]
    temp_folder_name = f"{file_name_without_extension}_temp"
    try:
        with zipfile.ZipFile(new_file_name, "r") as zip_ref:
            zip_ref.extractall(temp_folder_name)

        # replace the content of the <whatever_name>.mscx file inside that unzipped directory with the new content of the element tree
        mscx_file_name = next(
            (f for f in os.listdir(temp_folder_name) if f.endswith(".mscx")), None
        )
        if mscx_file_name is None:
            raise FileNotFoundError(f"No .mscx file in {file_path}")

        content_file_path = os.path.join(temp_folder_name, mscx_file_name)
        tree.write(content_file_path, encoding="utf-8", xml_declaration=True)

        # zip the directory again
        print(f"Creating {part_name}.zip")
        shutil.make_archive(part_name, "zip", temp_folder_name)

        # change the extension of the zip file to .mscz
        os.rename(
            f"{part_name}.zip",
            f"{part_name}.mscz",
        )

        # (optional) move the zip file to the output directory
        if out_dir is not None:
            shutil.move(f"{part_name}.mscz", out_dir)
    finally:
        # delete the temporary directory again
        shutil.rmtree(temp_folder_name, ignore_errors=True)


def get_staff_element_with_measures(part_element, root):
    staff_id = part_element.find("Staff").get("id")
    return root.find(f"./Score/Staff[@id='{staff_id}']")


def silence_all_measures_of_part(part_element, root):
    # print(f"Silencing part {get_part_name(part_element)}")
    staff_element = get_staff_element_with_measures(part_element, root)
    measures = staff_element.findall("./Measure")
    for measure in measures:
        # every measure has at least one <Voice> element
        voices = measure.findall("./voice")
        for voice in voices:
            # notes for a voice are usually stored in <Chord> elements and have a <durationType> child;
            # to be safe, set tag of _any_ element with a <durationType> child to 'Rest', turning it into a <Rest> element
            elements_with_duration = voice.findall(".//*[durationType]")
            for el in elements_with_duration:
                el.tag = "Rest"


def create_single_part_mscz(file_path, part_name, out_dir=None):
    """
    Given a path to a .mscz file, create a new .mscz file containing only the part with the given name.
    """
    # Get the element tree from the mscz file
    tree = get_content_tree_from_musescore_file(file_path)

    # Get the root element of the tree
    root = tree.getroot()

    # Get all parts in the score
    parts = get_parts(root)

    # Find the part with the given name
    part = next((p for p in parts if get_part_name(p) == part_name), None)
    if part is None:
        raise ValueError(f"No part named {part_name} found in {file_path}")

    # Remove all parts except the one we want to keep
    for p in parts:
        if p != part:
            remove_part(p, root)

    # store the new data in a new musescore file by applying the following steps:
    file_name = os.path.basename(file_path)
    new_file_name = f"{part_name}.mscz"
    shutil.copyfile(file_path, new_file_name)

    # unzip the file (every .mscz file is essentially a zip file)
    file_name_without_extension = os.path.splitext(file_name)[0]
    temp_folder_name = f"{file_name_without_extension}_temp"
    try:
        with zipfile.ZipFile(new_file_name, "r") as zip_ref:
            zip_ref.extractall(temp_folder_name)

        # replace the content of the <whatever_name>.mscx file inside that unzipped directory with the new content of the element tree
        mscx_file_name = next(
            (f for f in os.listdir(temp_folder_name) if f.endswith(".mscx")), None
        )
        if mscx_file_name is None:
            raise FileNotFoundError(f"No .mscx file in {file_path}")

        content_file_path = os.path.join(temp_folder_name, mscx_file_name)
        tree.write(content_file_path, encoding="utf-8", xml_declaration=True)

        # zip the directory again
        shutil.make_archive(part_name, "zip", temp_folder_name)

        # change the extension of the zip file to .mscz
        os.rename(
            f"{part_name}.zip",
            f"{part_name}.mscz",
        )

        # (optional) move the zip file to the output directory
        if out_dir is not None:
            shutil.move(f"{part_name}.mscz", out_dir)
    except Exception as e:
        print("Error while processing file", file_path)
        print(e)
    finally:
        # delete the temporary directory again
        shutil.rmtree(temp_folder_name, ignore_errors=True)


def create_part_mp3s(file_path, out_dir=None):
    """
    Given a path to a .mscz file, create an mp3 file for each part in the file.
    """
    parts_mp3_dir = out_dir or abspath(f"{splitext(basename(file_path))[0]}_part_mp3s")
    os.makedirs(parts_mp3_dir, exist_ok=True)

    create_msczs_with_all_other_parts_silenced_for_every_part_in(
        file_path, out_dir=parts_mp3_dir
    )

    # get paths to all created mscz files in the output directory
    mscz_files = [
        os.path.join(parts_mp3_dir, f)
        for f in os.listdir(parts_mp3_dir)
        if f.endswith(".mscz")
    ]

    for mscz in mscz_files:
        create_mp3(mscz)
        os.remove(mscz)


def create_mp3(file_path):
    """
    Export the given .mscz file as an mp3 file.
    """
    ms_version = get_musescore_version(file_path)
    if ms_version == 3:
        ms_path = MUSESCORE3_PATH
    elif ms_version == 4:
        ms_path = MUSESCORE4_PATH
    else:
        raise ValueError(f"Unsupported musescore version {ms_version}")
    try:
        subprocess.run(
            [
                ms_path,
                file_path,
                "-o",
                f"{os.path.join(abspath(dirname(file_path)), splitext(basename(file_path))[0])}.mp3",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error while processing file {file_path}")
        print(e)


def get_musescore_version(file_path):
    """
    Given a path to a .mscz file, return the version of musescore used to create the file.
    """
    # Get the element tree from the mscz file
    tree = get_content_tree_from_musescore_file(file_path)

    # Get the root element of the tree
    root = tree.getroot()

    # Get the programVersion element and extract the major version number
    version_element = root.find(".//programVersion")
    if version_element is not None:
        return int(version_element.text.split(".")[0])
    else:
        raise ValueError(f"No version information found in {file_path}")


def get_content_tree_from_musescore_file(file_path):
    """
    Extract the <whatever_name>.mscx file from a musescore file (.mscz),
    parse it as an XML document and return the element tree
    """
    file_name = os.path.basename(file_path)
    file_name_without_extension = os.path.splitext(file_name)[0]
    temp_folder_name = f"{file_name_without_extension}_temp"

    try:
        # Every .mscz file is essentially a zip file - unzip to a temporary folder
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(temp_folder_name)

        # mscx file in the mscz file is essentially an XML document describing most of the content of the score
        mscx_file_name = next(
            (f for f in os.listdir(temp_folder_name) if f.endswith(".mscx")), None
        )
        if mscx_file_name is None:
            raise FileNotFoundError(f"No .mscx file in {file_path}")

        score_file_path = os.path.join(temp_folder_name, mscx_file_name)
        with open(score_file_path, "r", encoding="utf-8") as score_file:
            # Parse the XML content and find the programVersion element
            tree = ET.parse(score_file)
            if tree is None:
                raise ValueError(f"No root element found in {file_path}")
            return tree

    finally:
        shutil.rmtree(temp_folder_name, ignore_errors=True)


def get_parts(root):
    return root.findall(".//Part")


def get_part_name(part_element):
    # part name is in <longName> element which in turn is located in the child <Instrument> element
    instrument_element = part_element.find("Instrument")
    if instrument_element is None:
        raise ValueError(f"No Instrument element found in {part_element}")
    long_name_element = instrument_element.find("longName")
    if long_name_element is None:
        # try to read the name from the shortName element instead
        short_name_element = instrument_element.find("shortName")
        if short_name_element is None:
            # try to read the name from the <trackName> element instead
            track_name_element = part_element.find("trackName")
            if track_name_element is None:
                raise ValueError(
                    f"No longName, shortName or trackName element found in {instrument_element}"
                )
            else:
                pretty_print_xml(part_element)
                return track_name_element.text
    return long_name_element.text


def remove_part(part_element, root):
    # A <Path> element stores metadata about a part. This includes (among other things):
    # - the track name
    # - the track's short name and, most importantly
    # - the ID of the <Staff> element that contains the notes of the part

    # hence, if we want to remove a part, we need to not only remove the Part Element, but also remove the associated Staff element

    staff_id = part_element.find("Staff").get("id")
    part_id = part_element.get("id")
    # get parent of part element (i.e. element with Part with given part id as child)
    parent = root.find(f".//Part[@id='{part_id}']/..")
    # remove part element
    parent.remove(part_element)

    staff_element = root.find(f".//Staff[@id='{staff_id}']")
    # get parent of staff element (i.e. element with Staff with given staff id as child)
    staff_parent = root.find(f".//Staff[@id='{staff_id}']/..")
    staff_parent.remove(staff_element)


def pretty_print_xml(element):
    print(ET.tostring(element, encoding="unicode", short_empty_elements=False))


def main():
    parser = argparse.ArgumentParser(description="My CLI App")

    subparsers = parser.add_subparsers(title="Commands", dest="command", required=True)

    parser_partnames = subparsers.add_parser(
        "partnames", help="List names of all available parts for a given file"
    )
    parser_partnames.add_argument(
        "file_path", type=str, help="Path to a .mscz file containing multiple parts"
    )
    partnames_cmd = lambda args: print(get_part_names(args.file_path))
    parser_partnames.set_defaults(func=partnames_cmd)

    parser_create_single = subparsers.add_parser(
        "single_part_mscz",
        help="Create a new mscz. file with only a specified part from a given mscz. file with multiple parts",
    )
    parser_create_single.add_argument(
        "file_path", type=str, help="Path to a .mscz file containing multiple parts"
    )
    parser_create_single.add_argument(
        "part_name", type=str, help="Name of the part to extract from the file"
    )
    create_single_part_cmd = lambda args: create_single_part_mscz(
        args.file_path, args.part_name
    )
    parser_create_single.set_defaults(func=create_single_part_cmd)

    parser_create_mp3 = subparsers.add_parser(
        "mp3", help="Create an mp3 file for a given mscz. file"
    )
    parser_create_mp3.add_argument(
        "file_path", type=str, help="Path to a .mscz file containing multiple parts"
    )
    create_mp3_cmd = lambda args: create_mp3(args.file_path)
    parser_create_mp3.set_defaults(func=create_mp3_cmd)

    parser_part_mp3s = subparsers.add_parser(
        "part_mp3s", help="Create an mp3 file for each part in a given mscz. file"
    )
    parser_part_mp3s.add_argument(
        "file_path", type=str, help="Path to a .mscz file containing multiple parts"
    )
    part_mp3s_cmd = lambda args: create_part_mp3s(args.file_path)
    parser_part_mp3s.set_defaults(func=part_mp3s_cmd)

    parser_silence_all_parts_except = subparsers.add_parser(
        "part_mscz_with_silenced_others",
        help="Create a new mscz. file for a given part from a given mscz. file with multiple parts. In this file, all parts except the chosen part are silenced.",
    )
    parser_silence_all_parts_except.add_argument(
        "file_path", type=str, help="Path to a .mscz file containing multiple parts"
    )
    parser_silence_all_parts_except.add_argument(
        "part_name", type=str, help="Name of the part to extract from the file"
    )
    parser_silence_all_parts_except.add_argument(
        "--output_dir",
        "-o",
        type=str,
        help="Path to a directory where the new files should be stored",
    )
    silence_all_parts_except_cmd = lambda args: silence_all_parts_except(
        args.file_path, args.part_name, args.output_dir
    )
    parser_silence_all_parts_except.set_defaults(func=silence_all_parts_except_cmd)

    parser_silence_other_parts = subparsers.add_parser(
        "part_msczs_with_silenced_others",
        help="Create a new mscz. file for each part from a given mscz. file with multiple parts. In this file, all parts except the chosen part are silenced.",
    )
    parser_silence_other_parts.add_argument(
        "file_path", type=str, help="Path to a .mscz file containing multiple parts"
    )
    parser_silence_other_parts.add_argument(
        "--output_dir",
        "-o",
        type=str,
        help="Path to a directory where the new files should be stored",
    )
    silence_other_parts_cmd = (
        lambda args: create_msczs_with_all_other_parts_silenced_for_every_part_in(
            args.file_path, args.output_dir
        )
    )
    parser_silence_other_parts.set_defaults(func=silence_other_parts_cmd)

    parser_separate = subparsers.add_parser(
        "separate",
        help="Create a new mscz. file for each part from a given mscz. file with multiple parts",
    )
    parser_separate.add_argument(
        "file_path", type=str, help="Path to a .mscz file containing multiple parts"
    )
    parser_separate.add_argument(
        "--output_dir",
        "-o",
        type=str,
        help="Path to a directory where the new files should be stored",
    )
    separate_cmd = lambda args: create_separate_msczs_for_parts(
        args.file_path, args.output_dir
    )
    parser_separate.set_defaults(func=separate_cmd)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
