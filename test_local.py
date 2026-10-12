from io import BytesIO
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from image_processor import (
    create_thumbnail,
    process_images,
    thumbnail_name,
    thumbnail_object_key,
)


class LocalImageProcessorTest(unittest.TestCase):
    def test_create_thumbnail_from_image_bytes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "source.png"
            Image.new("RGB", (600, 300), color="blue").save(source)

            thumbnail_bytes = create_thumbnail(source.read_bytes(), ".png")

            with Image.open(BytesIO(thumbnail_bytes)) as thumbnail:
                self.assertEqual(thumbnail.size, (300, 150))

    def test_thumbnail_name_preserves_nested_path_basename(self):
        self.assertEqual(
            thumbnail_name("1234_photo.JPG"),
            "1234_photo_thumbnail.jpg",
        )

    def test_thumbnail_object_key_preserves_directory_and_unique_prefix(self):
        self.assertEqual(
            thumbnail_object_key("uploads/1234_photo.JPG"),
            "uploads/1234_photo_thumbnail.jpg",
        )

    def test_creates_bounded_thumbnails_and_skips_non_images(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()

            Image.new("RGB", (600, 300), color="blue").save(input_dir / "large.png")
            Image.new("RGB", (100, 80), color="red").save(input_dir / "small.jpg")
            (input_dir / "notes.txt").write_text("not an image")

            count = process_images(input_dir, output_dir)

            self.assertEqual(count, 2)
            with Image.open(output_dir / "large_thumbnail.png") as thumbnail:
                self.assertEqual(thumbnail.size, (300, 150))
            with Image.open(output_dir / "small_thumbnail.jpg") as thumbnail:
                self.assertEqual(thumbnail.size, (100, 80))
            self.assertTrue((input_dir / "large.png").is_file())

    def test_rejects_same_input_and_output_folder(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            with self.assertRaisesRegex(ValueError, "must be different"):
                process_images(folder, folder)

    def test_rejects_missing_input_folder(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            with self.assertRaises(NotADirectoryError):
                process_images(root / "missing", root / "output")


if __name__ == "__main__":
    unittest.main(verbosity=2)
