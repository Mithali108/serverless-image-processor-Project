"""Streamlit UI for uploading images to LocalStack and retrieving thumbnails."""

import mimetypes
import os
import time
import uuid
from pathlib import PurePosixPath

import boto3
import streamlit as st
from botocore.exceptions import BotoCoreError, ClientError

from image_processor import SUPPORTED_EXTENSIONS, thumbnail_name, thumbnail_object_key


ENDPOINT_URL = os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566")
INPUT_BUCKET = os.environ.get("INPUT_BUCKET", "input-bucket")
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET", "output-bucket")
THUMBNAIL_WAIT_SECONDS = 30


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT_URL,
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
    )


def wait_for_thumbnail(s3, key: str) -> bytes:
    deadline = time.monotonic() + THUMBNAIL_WAIT_SECONDS
    while time.monotonic() < deadline:
        try:
            response = s3.get_object(Bucket=OUTPUT_BUCKET, Key=key)
            return response["Body"].read()
        except ClientError as error:
            error_code = error.response.get("Error", {}).get("Code")
            if error_code not in {"NoSuchKey", "404", "NotFound"}:
                raise
            time.sleep(0.5)
    raise TimeoutError(
        "The thumbnail was not created within "
        f"{THUMBNAIL_WAIT_SECONDS} seconds. Check LocalStack and the Lambda logs."
    )


st.set_page_config(page_title="Local Image Processor", page_icon="🖼️")
st.title("Local Image Processor")
st.caption("Upload an image to LocalStack S3 and preview or download its thumbnail.")

uploaded_file = st.file_uploader(
    "Choose an image",
    type=sorted(extension.lstrip(".") for extension in SUPPORTED_EXTENSIONS),
)

if uploaded_file is not None:
    if st.button("Create thumbnail", type="primary"):
        original_name = PurePosixPath(uploaded_file.name).name
        object_key = f"uploads/{uuid.uuid4().hex}_{original_name}"
        output_key = thumbnail_object_key(object_key)
        s3 = get_s3_client()

        try:
            with st.spinner("Uploading image and waiting for the Lambda thumbnail..."):
                s3.put_object(
                    Bucket=INPUT_BUCKET,
                    Key=object_key,
                    Body=uploaded_file.getvalue(),
                    ContentType=uploaded_file.type or "application/octet-stream",
                )
                thumbnail = wait_for_thumbnail(s3, output_key)

            st.success("Thumbnail created.")
            st.image(thumbnail, caption=thumbnail_name(original_name))
            st.download_button(
                "Download thumbnail",
                data=thumbnail,
                file_name=thumbnail_name(original_name),
                mime=mimetypes.guess_type(thumbnail_name(original_name))[0]
                or "application/octet-stream",
            )
        except (BotoCoreError, ClientError, TimeoutError, ValueError) as error:
            st.error(f"Image processing failed: {error}")
