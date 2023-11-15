import os
from shared.s3 import (
    download_file_from_s3,
    upload_file_to_s3,
    remove_file_from_s3,
    create_presigned_s3_url,
)


def test_s3():
    # if all of this runs without errors and prints a URL everything is working as expected

    # create temp file and upload
    with open("test.txt", "w") as f:
        f.write("Hello World")
    upload_file_to_s3("test.txt", "test.txt")

    download_file_from_s3("test.txt", "test.txt")
    print(create_presigned_s3_url("test.txt"))
    remove_file_from_s3("test.txt")
    os.remove("test.txt")
