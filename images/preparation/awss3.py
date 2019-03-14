import boto3
import threading
import os
import sys

s3 = boto3.client("s3")
bucket = "twistimages"


class AWSProgressPercentage(object):
    def __init__(self, filesize):
        self._size = filesize
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r %s / %s  (%.2f%%)" % (self._seen_so_far, self._size, percentage)
            )
            sys.stdout.flush()


def upload(filepath, url_type="generated"):

    filesize = float(os.path.getsize(filepath))
    key = os.path.basename(filepath)

    if url_type == "generated":
        acl = "private"
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=7200,
        )
    elif url_type == "static":
        acl = "public-read"
        location = s3.get_bucket_location(Bucket=bucket)["LocationConstraint"]
        url = f"https://s3.{ location }.amazonaws.com/{ bucket }/{ key }"
    else:
        raise NotImplementedError()

    s3.upload_file(
        filepath,
        bucket,
        key,
        ExtraArgs={"ACL": acl},
        Callback=AWSProgressPercentage(filesize),
    )

    sys.stdout.write("\n")

    return url
