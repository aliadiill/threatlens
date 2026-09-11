from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
target = root / "build" / "backend.zip"
target.parent.mkdir(exist_ok=True)
with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
    for path in sorted((root / "backend").glob("*.py")):
        archive.write(path, "backend/" + path.name)
print("Built backend package with package-relative imports preserved")
