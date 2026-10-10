import os
import tempfile
from pathlib import PurePosixPath
from urllib.parse import unquote_plus

import boto3
from PIL import Image


s3 = boto3.client("s3")
THUMBNAIL_SIZE = (300, 300)
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET")
OUTPUT_PREFIX = os.environ.get("OUTPUT_PREFIX", "thumbnails/").strip("/")
OUTPUT_PREFIX = f"{OUTPUT_PREFIX}/" if OUTPUT_PREFIX else ""


def lambda_handler(event, context):
    """Create and upload a JPEG thumbnail for each image in an S3 event."""
    results = []

    for record in event["Records"]:
        source_bucket = record["s3"]["bucket"]["name"]
        source_key = unquote_plus(record["s3"]["object"]["key"])
        destination_bucket = OUTPUT_BUCKET or source_bucket

        if source_bucket == destination_bucket and not OUTPUT_PREFIX:
            raise ValueError(
                "OUTPUT_PREFIX must be non-empty when thumbnails are written to the source bucket."
            )

        # Ignore objects in the output location so they cannot trigger a loop.
        if source_bucket == destination_bucket and source_key.startswith(OUTPUT_PREFIX):
            results.append({"key": source_key, "status": "skipped"})
            continue

        filename = PurePosixPath(source_key).name
        thumbnail_name = f"{PurePosixPath(filename).stem}_thumbnail.jpg"
        destination_key = f"{OUTPUT_PREFIX}{thumbnail_name}"

        # Use a unique temporary directory to avoid collisions between records.
        with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
            source_path = os.path.join(temp_dir, filename)
            thumbnail_path = os.path.join(temp_dir, thumbnail_name)

            s3.download_file(source_bucket, source_key, source_path)

            with Image.open(source_path) as image:
                image.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                image.convert("RGB").save(thumbnail_path, format="JPEG", optimize=True)

            s3.upload_file(
                thumbnail_path,
                destination_bucket,
                destination_key,
                ExtraArgs={"ContentType": "image/jpeg"},
            )

        results.append(
            {
                "source": f"s3://{source_bucket}/{source_key}",
                "thumbnail": f"s3://{destination_bucket}/{destination_key}",
                "status": "created",
            }
        )

    return {"results": results}
