import importlib
import sys
import types
import unittest
from unittest.mock import patch

from PIL import Image


class FakeS3:
    def __init__(self):
        self.downloads = []
        self.uploads = []

    def download_file(self, bucket, key, destination):
        self.downloads.append((bucket, key))
        Image.new("RGB", (600, 300), color="blue").save(destination, format="PNG")

    def upload_file(self, source, bucket, key, ExtraArgs=None):
        with Image.open(source) as image:
            dimensions = image.size
        self.uploads.append((bucket, key, ExtraArgs, dimensions))


# Supply a harmless boto3 stub so this local test does not need AWS credentials
# or a boto3 installation. The handler's S3 client is replaced with FakeS3 below.
fake_s3 = FakeS3()
boto3_stub = types.ModuleType("boto3")
boto3_stub.client = lambda service_name: fake_s3
previous_boto3 = sys.modules.get("boto3")
sys.modules["boto3"] = boto3_stub
try:
    lambda_function = importlib.import_module("lambda_function")
finally:
    if previous_boto3 is None:
        del sys.modules["boto3"]
    else:
        sys.modules["boto3"] = previous_boto3


class LambdaHandlerLocalTest(unittest.TestCase):
    def test_creates_and_uploads_thumbnail_from_s3_event(self):
        fake_s3 = FakeS3()
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "input-bucket"},
                        "object": {"key": "uploads/sample+image.png"},
                    }
                }
            ]
        }

        with patch.object(lambda_function, "s3", fake_s3):
            result = lambda_function.lambda_handler(event, None)

        self.assertEqual(
            fake_s3.downloads,
            [("input-bucket", "uploads/sample image.png")],
        )
        self.assertEqual(
            fake_s3.uploads,
            [
                (
                    "input-bucket",
                    "thumbnails/sample image_thumbnail.jpg",
                    {"ContentType": "image/jpeg"},
                    (300, 150),
                )
            ],
        )
        self.assertEqual(result["results"][0]["status"], "created")
        self.assertEqual(
            result["results"][0]["thumbnail"],
            "s3://input-bucket/thumbnails/sample image_thumbnail.jpg",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
