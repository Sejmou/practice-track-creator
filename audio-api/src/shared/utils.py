import zipfile


def unzip_file(zip_file_path, extract_to_path):
    with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
        zip_ref.extractall(extract_to_path)
