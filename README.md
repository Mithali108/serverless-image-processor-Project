# Local Image Thumbnail Processor

A small Python command-line project that resizes images locally with Pillow. It reads images from an input folder and saves thumbnails in an output folder. It does not use AWS, Docker, or cloud credentials.

## Requirements

- Windows 11
- Python 3.10 or newer

## Setup

Open PowerShell in the project folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell does not allow virtual-environment activation, you can run the Python executable directly as `.venv\Scripts\python.exe`.

## Run

Create an `input_images` folder in the project folder and copy images into it. Then run:

```powershell
python image_processor.py
```

Thumbnails are written to `output_images`. Both folders are relative to the current working directory; the output folder is created if it does not exist.

To specify different folders:

```powershell
python image_processor.py --input "C:\path\to\images" --output "C:\path\to\thumbnails"
```

The processor scans files directly inside the input folder (not subfolders). It supports BMP, GIF, JPEG, PNG, TIFF, and WebP file extensions. Each thumbnail keeps the source format and is named `<original-name>_thumbnail.<extension>`. The maximum dimensions are 300 × 300 pixels; aspect ratio is preserved and smaller images are not enlarged. Non-image files and unsupported extensions are skipped.

## Run tests

```powershell
python -m unittest -v test_local
```
