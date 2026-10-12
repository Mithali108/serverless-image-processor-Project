"""AWS Lambda entry point for S3-triggered image thumbnail generation."""

import os
from urllib.parse import unquote_plus

import boto3

from image_processor import (
    SUPPORTED_EXTENSIONS,
    create_thumbnail,
    thumbnail_object_key,
)


def handler(event, context):
    """Process S3 object-created records and save thumbnails to the output bucket."""
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ.get(
            "LOCALSTACK_ENDPOINT", "http://localhost:4566"
        ),
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
    )
    output_bucket = os.environ.get("OUTPUT_BUCKET", "output-bucket")
    results = []

    for record in event.get("Records", []):
        source_bucket = record["s3"]["bucket"]["name"]
        source_key = unquote_plus(record["s3"]["object"]["key"])
        extension = os.path.splitext(source_key)[1].lower()
        if extension not in SUPPORTED_EXTENSIONS:
            continue

        source = s3.get_object(Bucket=source_bucket, Key=source_key)
        thumbnail = create_thumbnail(source["Body"].read(), extension)
        output_key = thumbnail_object_key(source_key)
        content_type = source.get("ContentType", "application/octet-stream")
        s3.put_object(
            Bucket=output_bucket,
            Key=output_key,
            Body=thumbnail,
            ContentType=content_type,
        )
        results.append({"bucket": output_bucket, "key": output_key})

    return {"processed": len(results), "thumbnails": results}
