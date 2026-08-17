from dataclasses import dataclass, field
from pathlib import Path

from media_editor.media import MediaKind, classify_media


@dataclass(frozen=True)
class MediaAsset:
    path: Path
    kind: MediaKind


@dataclass
class MediaProject:
    assets: list[MediaAsset] = field(default_factory=list)

    def add_paths(self, paths: list[Path]) -> list[MediaAsset]:
        """중복을 제외하고 지원하는 media file을 project에 추가한다."""
        existing_paths = {asset.path.resolve() for asset in self.assets}
        added: list[MediaAsset] = []

        for path in paths:
            resolved = path.resolve()
            if resolved in existing_paths:
                continue

            asset = MediaAsset(path=path, kind=classify_media(path))
            self.assets.append(asset)
            added.append(asset)
            existing_paths.add(resolved)

        return added

    def remove(self, asset: MediaAsset) -> None:
        self.assets.remove(asset)
