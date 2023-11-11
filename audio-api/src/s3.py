import boto3
import logging
import os
from settings import S3_KEY, S3_SECRET, S3_REGION, S3_ENDPOINT, S3_BUCKET

s3 = boto3.client(
    "s3",
    aws_access_key_id=S3_KEY,
    aws_secret_access_key=S3_SECRET,
    region_name=S3_REGION,
    endpoint_url=S3_ENDPOINT,
)


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
        result = s3.upload_file(file_path, bucket_name, object_name)
        logging.debug(f"Uploaded file to S3: {result}")
    except Exception as e:
        logging.error(e)
        return False
    return True


from botocore.exceptions import ClientError


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
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response
