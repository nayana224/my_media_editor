"""Download a checksum-pinned FFmpeg/FFprobe pair without extracting archive paths."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import time
import urllib.request
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def download(url: str, target: Path, expected_sha256: str) -> None:
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as source, target.open("wb") as out:
                shutil.copyfileobj(source, out)
            break
        except OSError:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    with target.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != expected_sha256:
        target.unlink()
        raise RuntimeError(f"FFmpeg SHA256 mismatch: expected {expected_sha256}, got {digest}")


def bundle(platform: str, destination: Path, cache: Path) -> None:
    manifest = json.loads((PROJECT_ROOT / "packaging/ffmpeg.json").read_text("utf-8"))
    entry = manifest[platform]
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / entry["url"].rsplit("/", 1)[1]
    # Always verify a cached archive too.
    if archive.is_file():
        with archive.open("rb") as stream:
            valid = hashlib.file_digest(stream, "sha256").hexdigest() == entry["sha256"]
        if not valid:
            archive.unlink()
    if not archive.is_file():
        download(entry["url"], archive, entry["sha256"])

    suffix = ".exe" if platform == "windows-x64" else ""
    wanted = {f"ffmpeg{suffix}", f"ffprobe{suffix}"}
    found = set()
    notices = destination / "third-party/ffmpeg"
    notices.mkdir(parents=True, exist_ok=True)
    (destination / "bin").mkdir(parents=True, exist_ok=True)

    def copy_member(name, source):
        parts = PurePosixPath(name).parts
        if len(parts) < 2 or any(p in ("..", "/") or ":" in p or "\\" in p for p in parts):
            raise ValueError(f"Unsafe FFmpeg archive member: {name}")
        relative = PurePosixPath(*parts[1:])
        if relative.parent == PurePosixPath("bin") and relative.name in wanted:
            target = destination / "bin" / relative.name
            with target.open("wb") as out:
                shutil.copyfileobj(source, out)
            target.chmod(0o755)
            found.add(relative.name)
        elif relative.suffix.lower() in (".txt", ".md", ".html") or relative.name.lower().startswith(("license", "copying", "readme")):
            target = notices.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as out:
                shutil.copyfileobj(source, out)

    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as package:
            for member in package.infolist():
                if not member.is_dir():
                    with package.open(member) as source:
                        copy_member(member.filename, source)
    else:
        with tarfile.open(archive, "r:xz") as package:
            for member in package:
                if member.isfile():
                    with package.extractfile(member) as source:
                        copy_member(member.name, source)
    if found != wanted:
        raise RuntimeError(f"FFmpeg archive missing tools: {wanted - found}")
    if not any(p.is_file() and p.name.lower().startswith(("license", "copying")) for p in notices.rglob("*")):
        raise RuntimeError("FFmpeg archive did not contain license files")
    (notices / "provenance.json").write_text(json.dumps(entry, indent=2) + "\n", "utf-8")
    print(f"Bundled FFmpeg and FFprobe: {destination / 'bin'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("linux-x86_64", "windows-x64"), required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    bundle(args.platform, args.destination, args.cache)
