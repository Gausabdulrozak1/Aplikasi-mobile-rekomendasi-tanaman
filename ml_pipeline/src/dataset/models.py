from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ImageRecord:
    original_path: str
    class_id: str
    display_name: str
    trigger_token: str
    file_name: str
    extension: str
    format: str
    width: int
    height: int
    color_mode: str
    file_size: int
    sha256: str
    original_file_name: str = ""
    source_type: str = ""
    source_name: str = ""
    source_identifier: str = ""
    source_url: str = ""
    license: str = ""
    access_date: str = ""
    is_local_aikmel: bool = False
    capture_date: str = ""
    location_general: str = ""
    photographer: str = ""
    permission_status: str = ""
    review_status: str = ""
    notes: str = ""
    perceptual_hash: str = ""
    status: str = "pending"
    rejection_reason: str = ""
    duplicate_group: str = ""
    duplicate_warning: str = ""
    exif_orientation: str = ""
    exif_orientation_status: str = ""

    def to_dict(self) -> dict[str, object]:
        row = asdict(self)
        row["file_format"] = self.format
        row["technical_status"] = self.status
        return row


@dataclass(frozen=True)
class MetadataRecord:
    file_name: str
    text: str
    class_id: str
    trigger_token: str
    source_type: str
    is_local_aikmel: bool
    location_general: str
    duplicate_group: str
    original_file_name: str = ""
    manual_review_status: str = "yes"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_training_dict(self) -> dict[str, object]:
        return self.to_dict()
