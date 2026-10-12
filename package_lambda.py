"""Package the Lambda runtime dependencies and handler into a deployment ZIP."""

import sys
import zipfile
from pathlib import Path


def main() -> None:
    source_dir = Path(sys.argv[1])
    archive_path = Path(sys.argv[2])
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in source_dir.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir))


if __name__ == "__main__":
    main()
