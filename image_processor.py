"""Create local thumbnails from images in an input folder."""

import argparse
from pathlib import Path

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
        output_path = output_dir / f"{image_path.stem}_thumbnail{image_path.suffix.lower()}"
        with Image.open(image_path) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            if output_path.suffix in {".jpg", ".jpeg"} and image.mode not in {
                "L",
                "RGB",
                "CMYK",
            }:
                image = image.convert("RGB")
            image.save(output_path)
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
