# Local Image Thumbnail Processor

This project supports both the original local-folder workflow and a browser-based
workflow using LocalStack to simulate S3 and Lambda. No AWS account or cloud
credentials are needed.

## Requirements

- Windows 11
- Python 3.10 or newer
- Docker Desktop with Docker Compose

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

## Run the LocalStack and browser workflow

The browser app uploads to `input-bucket`. LocalStack sends the S3 object-created
event to `image-thumbnail-processor`, which creates a same-format thumbnail in
`output-bucket`. The web app then previews the thumbnail and offers it for
download.

1. Start Docker Desktop, then start LocalStack from the project folder:

   ```powershell
   docker compose up -d localstack
   docker compose ps
   ```

   Wait for the `localstack` service to show as healthy.

2. Build a Lambda ZIP with Pillow compiled for the Linux Lambda runtime. This is
   important when the project is being developed on Windows:

   ```powershell
   docker compose run --build --rm lambda-package
   ```

   This writes `build\lambda.zip`.

3. In the activated project virtual environment, install dependencies and
   provision the buckets, Lambda, and S3 notification:

   ```powershell
   python -m pip install -r requirements.txt
   python setup_localstack.py
   ```

   The setup script uses `boto3` with `endpoint_url="http://localhost:4566"`.
   It is safe to rerun after changing the Lambda code.

4. Start the Streamlit app:

   ```powershell
   python -m streamlit run app.py
   ```

   Open the local URL Streamlit prints, select a supported image, and choose
   **Create thumbnail**. Supported formats are BMP, GIF, JPEG, PNG, TIFF, and
   WebP. Thumbnails are bounded to 300 × 300 pixels and keep their aspect ratio.

Set `LOCALSTACK_ENDPOINT`, `INPUT_BUCKET`, and `OUTPUT_BUCKET` environment
variables to override the app's defaults. The setup script uses the standard
local endpoint and bucket names above.

To inspect LocalStack logs:

```powershell
docker compose logs -f localstack
```

To stop LocalStack:

```powershell
docker compose down
```

The local data directory is `.\.localstack`; removing it resets the
simulated AWS state. The original `python image_processor.py` command and its
`--input` / `--output` options remain available.
