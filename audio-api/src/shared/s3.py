import boto3
from botocore.exceptions import ClientError
import logging
import os
from .settings import (
    S3_KEY,
    S3_SECRET,
    S3_REGION,
    S3_ENDPOINT,
    S3_BUCKET,
)

s3 = boto3.client(
    "s3",
    aws_access_key_id=S3_KEY,
    aws_secret_access_key=S3_SECRET,
    region_name=S3_REGION,
    endpoint_url=S3_ENDPOINT,
)


def download_file_from_s3(object_name, file_path, bucket_name=S3_BUCKET):
    """Download a file from an S3 bucket

    Args:
        object_name (str): Name of the file to download
        file_path (str): Local path to save the file to.
        bucket_name (str): Name of the bucket to download from. Defaults to the configured bucket name from settings.py.

    Returns:
        bool: True if file was downloaded, else False
    """
    try:
        result = s3.download_file(bucket_name, object_name, file_path)
        logging.debug(f"Downloaded file from S3: {result}")
    except Exception as e:
        logging.error(f"Could not download '{object_name}' from S3")
        logging.exception(e)
        return False
    return True


def upload_file_to_s3(file_path, object_name=None, bucket_name=S3_BUCKET):
    """Upload a file to an S3 bucket

    Args:
        file_path (str): Path to the file to upload
        object_name (str, optional): Name to save the file as in the bucket. Defaults to None (i.e. use the file's name).
        bucket_name (str): Name of the bucket to upload to. Defaults to the configured bucket name from settings.py.

    Returns:
        bool: True if file was uploaded, else False
    """
    if object_name is None:
        object_name = os.path.basename(file_path)
    try:
        logging.debug(
            f"Uploading local file '{file_path}' to S3 ({object_name}, bucket: {bucket_name})"
        )
        s3.upload_file(file_path, bucket_name, object_name)
        logging.debug(f"Uploaded file to S3 ({object_name}, bucket: {bucket_name})")
    except Exception as e:
        logging.error(f"Could not upload '{file_path}' to S3 ({object_name})")
        logging.exception(e)
        return False
    return True


def create_presigned_s3_url(object_name, bucket_name=S3_BUCKET, expiration=3600):
    """Generate a presigned URL to share an S3 object

    :param object_name: string
    :param bucket_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """
    try:
        response = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=expiration,
        )
    except ClientError as e:
        logging.error(f"Could not generate presigned URL for '{object_name}'")
        logging.exception(e)
        return None

    # The response contains the presigned URL
    return response


def remove_file_from_s3(object_name, bucket_name=S3_BUCKET):
    """Remove a file from an S3 bucket

    Args:
        object_name (str): Name of the file to remove
        bucket_name (str): Name of the bucket to remove from. Defaults to the configured bucket name from settings.py.

    Returns:
        bool: True if file was removed, else False
    """
    try:
        result = s3.delete_object(Bucket=bucket_name, Key=object_name)
        logging.debug(f"Removed file from S3: {result}")
    except Exception as e:
        logging.error(f"Could not remove '{object_name}' from S3")
        logging.exception(e)
        return False
    return True
