"""Create local thumbnails from images in an input folder."""

import argparse
from io import BytesIO
from pathlib import Path
from pathlib import PurePosixPath
from typing import BinaryIO

from PIL import Image, ImageOps


THUMBNAIL_SIZE = (300, 300)
SUPPORTED_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}


def create_thumbnail(image_data: bytes | BinaryIO, extension: str) -> bytes:
    """Create an in-memory thumbnail while preserving the source image format."""
    extension = extension.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported image extension: {extension}")

    image_format = Image.registered_extensions()[extension]
    source = BytesIO(image_data) if isinstance(image_data, bytes) else image_data
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
        if extension in {".jpg", ".jpeg"} and image.mode not in {"L", "RGB", "CMYK"}:
            image = image.convert("RGB")
        output = BytesIO()
        image.save(output, format=image_format)
    return output.getvalue()


def thumbnail_name(filename: str) -> str:
    """Return the source filename with the standard thumbnail suffix."""
    path = Path(filename)
    return f"{path.stem}_thumbnail{path.suffix.lower()}"


def thumbnail_object_key(key: str) -> str:
    """Return an S3 object key for a source key's thumbnail."""
    path = PurePosixPath(key)
    return str(path.with_name(thumbnail_name(path.name)))


def process_images(input_dir: Path, output_dir: Path) -> int:
    """Create a thumbnail for each supported image in input_dir."""
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()

    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input folder does not exist: {input_dir}")
    if input_dir == output_dir:
        raise ValueError("Input and output folders must be different.")

    output_dir.mkdir(parents=True, exist_ok=True)
    image_paths = sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    for image_path in image_paths:
        output_path = output_dir / thumbnail_name(image_path.name)
        with image_path.open("rb") as source:
            thumbnail = create_thumbnail(source, image_path.suffix)
        output_path.write_bytes(thumbnail)
        print(f"Created: {output_path}")

    if not image_paths:
        print(f"No supported images found in: {input_dir}")

    return len(image_paths)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resize images into thumbnails in a local output folder."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("input_images"),
        help="Folder containing images (default: input_images)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output_images"),
        help="Folder where thumbnails are saved (default: output_images)",
    )
    args = parser.parse_args()
    count = process_images(args.input, args.output)
    print(f"Finished: {count} thumbnail(s) created.")


if __name__ == "__main__":
    main()
