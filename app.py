"""Streamlit UI for uploading images to LocalStack and retrieving thumbnails."""

import hashlib
import mimetypes
import os
import time
import uuid
from io import BytesIO
from pathlib import PurePosixPath

import boto3
import streamlit as st
from botocore.exceptions import BotoCoreError, ClientError
from PIL import Image, UnidentifiedImageError

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


st.set_page_config(
    page_title="Serverless Image Processor",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Force larger base font across Streamlit elements */
    .stApp {
        font-size: 1.15rem !important;
    }
    p, span, label, div {
        font-size: 1.1rem !important;
    }
    .main-header {
        font-size: 2.8rem !important;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.25rem !important;
        color: #4B5563;
        margin-bottom: 2rem;
    }
    /* Make sidebar text readable */
    section[data-testid="stSidebar"] * {
        font-size: 1.05rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="main-header">🖼️ Serverless Image Processor</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-header">Upload an image to generate an optimized thumbnail '
    "with LocalStack S3 and Lambda.</p>",
    unsafe_allow_html=True,
)
st.divider()

with st.sidebar:
    st.header("⚙️ System")
    st.markdown(f"**LocalStack endpoint:** `{ENDPOINT_URL}`")
    st.markdown(f"**Input bucket:** `{INPUT_BUCKET}`")
    st.markdown(f"**Output bucket:** `{OUTPUT_BUCKET}`")
    st.markdown("---")
    st.markdown("### 📌 Instructions")
    st.markdown(
        "1. Upload a supported image.\n"
        "2. Click **Generate Thumbnail**.\n"
        "3. Preview and download the result."
    )

uploaded_file = st.file_uploader(
    "Choose an image file",
    type=sorted(extension.lstrip(".") for extension in SUPPORTED_EXTENSIONS),
)

if uploaded_file is not None:
    image_data = uploaded_file.getvalue()
    upload_signature = hashlib.sha256(image_data).hexdigest()
    try:
        with Image.open(BytesIO(image_data)) as image:
            original_dimensions = image.size
            original_preview = image.copy()
    except (UnidentifiedImageError, OSError) as error:
        st.error(f"Could not open the uploaded image: {error}")
    else:
        preview_col, result_col = st.columns(2, gap="large")

        with preview_col:
            st.subheader("📤 Original Image")
            st.image(original_preview, use_container_width=True)
            st.caption(
                f"Dimensions: {original_dimensions[0]} × "
                f"{original_dimensions[1]} px"
            )

        with result_col:
            st.subheader("✨ Processed Thumbnail")
            if st.button("🚀 Generate Thumbnail", type="primary"):
                original_name = PurePosixPath(uploaded_file.name).name
                object_key = f"uploads/{uuid.uuid4().hex}_{original_name}"
                output_key = thumbnail_object_key(object_key)

                try:
                    with st.spinner("Processing image through S3 and Lambda..."):
                        s3 = get_s3_client()
                        s3.put_object(
                            Bucket=INPUT_BUCKET,
                            Key=object_key,
                            Body=image_data,
                            ContentType=uploaded_file.type
                            or "application/octet-stream",
                        )
                        thumbnail_data = wait_for_thumbnail(s3, output_key)

                    st.session_state["thumbnail"] = thumbnail_data
                    st.session_state["thumbnail_name"] = thumbnail_name(
                        original_name
                    )
                    st.session_state["thumbnail_source"] = upload_signature
                    st.success("Thumbnail created.")
                except (BotoCoreError, ClientError, TimeoutError, ValueError) as error:
                    st.error(f"Image processing failed: {error}")

            if st.session_state.get("thumbnail_source") == upload_signature:
                thumbnail_data = st.session_state["thumbnail"]
                thumbnail_filename = st.session_state["thumbnail_name"]
                with Image.open(BytesIO(thumbnail_data)) as thumbnail_image:
                    thumbnail_dimensions = thumbnail_image.size
                    st.image(thumbnail_image, use_container_width=True)
                st.caption(
                    f"Thumbnail dimensions: {thumbnail_dimensions[0]} × "
                    f"{thumbnail_dimensions[1]} px"
                )
                st.download_button(
                    label="📥 Download Thumbnail",
                    data=thumbnail_data,
                    file_name=thumbnail_filename,
                    mime=mimetypes.guess_type(thumbnail_filename)[0]
                    or "application/octet-stream",
                )
