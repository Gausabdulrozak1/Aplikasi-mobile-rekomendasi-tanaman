from __future__ import annotations

import csv
import json
import re
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path

import pytest
from PIL import Image

from ml_pipeline.src.common.config import (
    apply_class_filter,
    class_definitions,
    load_config,
    source_definitions,
    validate_class_config,
)
from ml_pipeline.src.dataset.caption_dataset import build_caption
from ml_pipeline.src.dataset.cli import (
    build_parser,
    command_audit,
    command_prepare,
    command_report,
)
from ml_pipeline.src.dataset.dataset_inventory import (
    DatasetNotAvailableError,
    build_inventory,
)
from ml_pipeline.src.dataset.dataset_review import HUMAN_REVIEW_FIELDS
from ml_pipeline.src.dataset.detect_duplicates import (
    add_perceptual_hashes,
    assign_duplicate_groups,
    duplicate_report,
)
from ml_pipeline.src.dataset.final_package_validation import validate_final_dataset_package
from ml_pipeline.src.dataset.finalize_reviewed import finalize_reviewed_dataset
from ml_pipeline.src.dataset.io_utils import read_jsonl, sha256_file, write_csv
from ml_pipeline.src.dataset.package_dataset import PackageBlockedError, create_dataset_package
from ml_pipeline.src.dataset.provenance import PROVENANCE_FIELDS
from ml_pipeline.src.dataset.semantic_screening import run_automated_semantic_screening
from ml_pipeline.src.dataset.validate_images import validate_records
from ml_pipeline.src.dataset.validate_metadata import validate_metadata_file
from ml_pipeline.src.evaluation.evaluator import write_confusion_review_template


def audit_fixture(config: dict) -> tuple[list, dict]:
    records = add_perceptual_hashes(validate_records(config, build_inventory(config)))
    duplicates = duplicate_report(config, records)
    return assign_duplicate_groups(records, duplicates), duplicates


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def complete_manual_review(
    config: dict,
    *,
    rejected: set[str] | None = None,
) -> None:
    template = Path(config["dataset"]["review_directory"]) / "manual_review_template.csv"
    rows = read_csv_rows(template)
    rejected_names = rejected or set()
    for row in rows:
        if row["curated_file_name"] in rejected_names:
            row["accepted"] = "no"
            row["reviewer_notes"] = "Rejected by fixture reviewer"
        else:
            row["accepted"] = "yes"
    write_csv(template, rows, list(rows[0]))


def prepare_final(config: dict) -> dict:
    pending = command_prepare(config)
    assert pending["status"] == "manual_review_required"
    complete_manual_review(config)
    result = command_prepare(config)
    assert result["status"] == "final_dataset_prepared", result["metadata_validation"]
    return result


def test_finalize_reviewed_uses_authoritative_review_mapping(
    multicrop_config: dict,
) -> None:
    pending = command_prepare(multicrop_config)
    assert pending["status"] == "manual_review_required"
    complete_manual_review(multicrop_config)

    result = finalize_reviewed_dataset(multicrop_config)

    assert result["status"] == "final_dataset_prepared", result["metadata_validation"]
    assert set(result["selected_per_class"]) == {
        "padi",
        "jagung",
        "cabai",
        "kacang_tanah",
    }
    assert all(count >= 4 for count in result["selected_per_class"].values())
    assert result["metadata_validation"]["valid"] is True
    mapping = read_csv_rows(
        Path(multicrop_config["dataset"]["reports_directory"]) / "curation_mapping.csv"
    )
    assert {row["review_batch"] for row in mapping} == {"original_350"}
    assert all(row["manual_review_status"] == "yes" for row in mapping)


def test_automated_screening_is_proxy_and_preserves_human_review(
    multicrop_config: dict,
) -> None:
    pending = command_prepare(multicrop_config)
    assert pending["status"] == "manual_review_required"
    review_template = (
        Path(multicrop_config["dataset"]["review_directory"]) / "manual_review_template.csv"
    )
    review_before = review_template.read_bytes()

    result = run_automated_semantic_screening(multicrop_config)

    assert result["status"] == "proxy_complete_human_review_still_required"
    assert result["human_review_required"] is True
    assert review_template.read_bytes() == review_before
    rows = read_csv_rows(Path(result["report"]))
    assert rows
    assert {row["semantic_class_status"] for row in rows} == {"not_assessed_no_semantic_model"}
    assert {row["eligible_for_final_without_human_review"] for row in rows} == {"False"}
    for class_id in ("padi", "jagung", "cabai", "kacang_tanah"):
        assert (
            Path(multicrop_config["dataset"]["review_directory"]) / f"review_{class_id}.jpg"
        ).is_file()


def test_repository_config_uses_final_classes_sources_and_triggers() -> None:
    config = load_config("ml_pipeline/configs/dataset_public_multicrop.yaml")
    classes = class_definitions(config)
    assert [item["id"] for item in classes] == [
        "padi",
        "jagung",
        "cabai",
        "kacang_tanah",
    ]
    assert {item["trigger_token"] for item in classes} == {
        "taniadaptif_padi",
        "taniadaptif_jagung",
        "taniadaptif_cabai",
        "taniadaptif_kacang_tanah",
    }
    sources = source_definitions(config)
    assert {(item["class_id"], item["type"]) for item in sources} == {
        ("padi", "public"),
        ("padi", "local_aikmel"),
        ("jagung", "public"),
        ("cabai", "public"),
        ("kacang_tanah", "public"),
    }


def test_class_ids_and_trigger_tokens_are_unique(multicrop_config: dict) -> None:
    validate_class_config(multicrop_config)
    classes = class_definitions(multicrop_config)
    assert len({item["id"] for item in classes}) == 4
    assert len({item["trigger_token"] for item in classes}) == 4


def test_local_aikmel_source_is_rejected_for_non_padi(multicrop_config: dict) -> None:
    invalid = deepcopy(multicrop_config)
    invalid["classes"][1]["sources"].append(
        {
            "type": "local_aikmel",
            "directory": "unused",
            "required": False,
        }
    )
    with pytest.raises(ValueError, match="only valid for class 'padi'"):
        validate_class_config(invalid)


def test_optional_local_padi_directory_can_be_absent(multicrop_config: dict) -> None:
    local_source = multicrop_config["classes"][0]["sources"][1]
    shutil.rmtree(local_source["directory"])
    records = build_inventory(multicrop_config)
    assert records
    assert not any(record.source_type == "local_aikmel" for record in records)


def test_inventory_contains_required_provenance(multicrop_config: dict) -> None:
    records = build_inventory(multicrop_config)
    padi_public = next(
        record for record in records if record.class_id == "padi" and record.source_type == "public"
    )
    padi_local = next(
        record
        for record in records
        if record.class_id == "padi" and record.source_type == "local_aikmel"
    )
    assert padi_public.trigger_token == "taniadaptif_padi"
    assert padi_public.is_local_aikmel is False
    assert padi_local.is_local_aikmel is True
    assert set(padi_public.to_dict()) >= set(PROVENANCE_FIELDS)


def test_source_manifest_is_created_without_invented_facts_and_preserves_edits(
    multicrop_config: dict,
) -> None:
    command_audit(multicrop_config)
    manifest = Path(multicrop_config["dataset"]["source_manifest"])
    rows = read_csv_rows(manifest)
    assert rows
    assert set(rows[0]) == set(PROVENANCE_FIELDS)
    assert all(row["source_type"] in {"public", "local_aikmel", ""} for row in rows)
    public_row = next(row for row in rows if row["source_type"] == "public")
    assert public_row["license"] == ""
    public_row["license"] = "verified-test-license"
    public_row["source_name"] = "verified-test-source"
    write_csv(manifest, rows, PROVENANCE_FIELDS)

    command_audit(multicrop_config)
    updated = {row["original_path"]: row for row in read_csv_rows(manifest)}[
        public_row["original_path"]
    ]
    assert updated["license"] == "verified-test-license"
    assert updated["source_name"] == "verified-test-source"


def test_validator_rejects_corrupt_small_and_unknown_images(
    multicrop_config: dict,
) -> None:
    records, _ = audit_fixture(multicrop_config)
    reasons = {record.rejection_reason for record in records if record.status == "invalid"}
    assert any(reason.startswith("unreadable_image") for reason in reasons)
    assert "resolution_too_small" in reasons
    assert "unknown_class" in reasons


def test_exact_and_near_duplicate_detection_work_across_classes(
    multicrop_config: dict,
) -> None:
    records, duplicates = audit_fixture(multicrop_config)
    assert any(
        {row["canonical_class_id"], row["duplicate_class_id"]} == {"padi", "jagung"}
        for row in duplicates["exact"]
    )
    assert any(
        {row["left_class_id"], row["right_class_id"]} == {"cabai", "kacang_tanah"}
        for row in duplicates["near"]
    )
    assert sum(record.status == "duplicate" for record in records) >= 2


def test_cross_source_duplicate_is_reported_for_padi(multicrop_config: dict) -> None:
    _, duplicates = audit_fixture(multicrop_config)
    assert duplicates["cross_source_padi"]
    assert {
        duplicates["cross_source_padi"][0]["canonical_source_type"],
        duplicates["cross_source_padi"][0]["duplicate_source_type"],
    } == {"public", "local_aikmel"}


def test_prepare_stratifies_every_class_and_both_padi_sources(
    multicrop_config: dict,
) -> None:
    result = prepare_final(multicrop_config)
    summary = json.loads(
        (Path(multicrop_config["dataset"]["reports_directory"]) / "split_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert result["metadata_validation"]["valid"] is True
    assert all(counts["train"] > 0 for counts in summary["per_class"].values())
    assert all(counts["validation"] > 0 for counts in summary["per_class"].values())
    for source_type in ("public", "local_aikmel"):
        assert summary["per_source"]["padi"][source_type]["train"] > 0
        assert summary["per_source"]["padi"][source_type]["validation"] > 0


def test_split_is_reproducible(multicrop_config: dict) -> None:
    prepare_final(multicrop_config)
    manifest = Path(multicrop_config["dataset"]["reports_directory"]) / "split_manifest.csv"
    first = manifest.read_text(encoding="utf-8")
    command_prepare(multicrop_config)
    assert manifest.read_text(encoding="utf-8") == first


def test_report_preserves_prepared_split_counts(multicrop_config: dict) -> None:
    prepare_final(multicrop_config)
    command_report(multicrop_config)
    rows = read_csv_rows(
        Path(multicrop_config["dataset"]["reports_directory"]) / "source_distribution.csv"
    )
    assert all(int(row["train_count"]) > 0 for row in rows if row["class_id"] != "unknown")
    assert all(int(row["validation_count"]) > 0 for row in rows if row["class_id"] != "unknown")


def test_duplicate_group_never_crosses_splits(multicrop_config: dict) -> None:
    prepare_final(multicrop_config)
    manifest = Path(multicrop_config["dataset"]["reports_directory"]) / "split_manifest.csv"
    groups: dict[str, set[str]] = {}
    for row in read_csv_rows(manifest):
        groups.setdefault(row["duplicate_group"], set()).add(row["split"])
    assert all(len(splits) == 1 for splits in groups.values())


def test_split_manifest_contains_source_policy_fields(multicrop_config: dict) -> None:
    prepare_final(multicrop_config)
    manifest = Path(multicrop_config["dataset"]["reports_directory"]) / "split_manifest.csv"
    rows = read_csv_rows(manifest)
    assert set(rows[0]) >= {
        "file_name",
        "original_file_name",
        "class_id",
        "source_type",
        "is_local_aikmel",
        "split",
        "duplicate_group",
        "seed",
        "caption",
    }
    assert {row["seed"] for row in rows} == {"42"}


def test_caption_is_conservative_and_uses_final_trigger(multicrop_config: dict) -> None:
    caption = build_caption(multicrop_config, "padi")
    assert caption == (
        "a realistic agricultural photograph of taniadaptif_padi, "
        "rice plants growing in an agricultural environment, natural lighting"
    )
    assert not any(
        phrase in caption.casefold()
        for phrase in ("sunny", "cloudy", "water", "moisture", "growth stage")
    )


def test_public_caption_never_claims_aikmel(multicrop_config: dict) -> None:
    caption = build_caption(
        multicrop_config,
        "padi",
        {"source_type": "public", "location_general": "Aikmel"},
    )
    assert "aikmel" not in caption.casefold()


def test_local_caption_mentions_aikmel_only_with_supporting_location(
    multicrop_config: dict,
) -> None:
    unsupported = build_caption(
        multicrop_config,
        "padi",
        {"source_type": "local_aikmel", "location_general": ""},
    )
    supported = build_caption(
        multicrop_config,
        "padi",
        {"source_type": "local_aikmel", "location_general": "Aikmel"},
    )
    assert "aikmel" not in unsupported.casefold()
    assert "aikmel" in supported.casefold()


def test_metadata_rejects_wrong_trigger(multicrop_config: dict) -> None:
    prepare_final(multicrop_config)
    metadata_path = (
        Path(multicrop_config["dataset"]["processed_directory"]) / "train" / "metadata.jsonl"
    )
    rows = read_jsonl(metadata_path)
    padi_row = next(row for row in rows if row["file_name"].startswith("padi/"))
    padi_row["text"] = padi_row["text"].replace("taniadaptif_padi", "taniadaptif_jagung")
    metadata_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    result = validate_metadata_file(metadata_path, multicrop_config)
    assert result["valid"] is False
    assert any("wrong trigger" in error for error in result["errors"])


def test_metadata_rejects_local_source_for_non_padi(multicrop_config: dict) -> None:
    prepare_final(multicrop_config)
    metadata_path = (
        Path(multicrop_config["dataset"]["processed_directory"]) / "train" / "metadata.jsonl"
    )
    rows = read_jsonl(metadata_path)
    jagung = next(row for row in rows if row["class_id"] == "jagung")
    jagung["source_type"] = "local_aikmel"
    jagung["is_local_aikmel"] = True
    metadata_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    result = validate_metadata_file(metadata_path, multicrop_config)
    assert result["valid"] is False
    assert any("not allowed" in error for error in result["errors"])


def test_metadata_rejects_invalid_json(multicrop_config: dict) -> None:
    prepare_final(multicrop_config)
    metadata_path = (
        Path(multicrop_config["dataset"]["processed_directory"]) / "validation" / "metadata.jsonl"
    )
    with metadata_path.open("a", encoding="utf-8") as handle:
        handle.write("{invalid json}\n")
    result = validate_metadata_file(metadata_path, multicrop_config)
    assert result["valid"] is False
    assert any("invalid JSON" in error for error in result["errors"])


def test_metadata_records_source_distribution(multicrop_config: dict) -> None:
    result = prepare_final(multicrop_config)
    train_sources = result["metadata_validation"]["splits"]["train"]["source_distribution"]
    assert train_sources["padi:public"] > 0
    assert train_sources["padi:local_aikmel"] > 0
    assert all(
        not key.endswith(":local_aikmel") for key in train_sources if not key.startswith("padi:")
    )


def test_required_reports_and_curation_provenance_are_created(
    multicrop_config: dict,
) -> None:
    prepare_final(multicrop_config)
    reports = Path(multicrop_config["dataset"]["reports_directory"])
    expected = {
        "inventory_padi.csv",
        "inventory_jagung.csv",
        "inventory_cabai.csv",
        "inventory_kacang_tanah.csv",
        "inventory_all_classes.csv",
        "invalid_images.csv",
        "exact_duplicates.csv",
        "near_duplicates.csv",
        "cross_source_duplicates_padi.csv",
        "cross_class_duplicates.csv",
        "provenance_warnings.csv",
        "audit_summary.md",
        "source_distribution.csv",
        "curation_mapping.csv",
        "split_manifest.csv",
        "split_summary.json",
        "split_summary.md",
        "metadata_validation_report.json",
        "metadata_validation_report.md",
        "manual_review_summary.csv",
        "final_curation_summary.md",
    }
    assert expected <= {path.name for path in reports.iterdir()}
    mapping = read_csv_rows(reports / "curation_mapping.csv")
    assert set(mapping[0]) >= {
        "original_path",
        "original_file_name",
        "curated_path",
        "curated_file_name",
        "new_file_name",
        "class_id",
        "source_type",
        "is_local_aikmel",
        "validation_status",
        "technical_status",
        "manual_review_status",
        "final_status",
        "perceptual_hash",
        "sha256",
        "duplicate_group",
    }


def test_manual_review_outputs_are_reproducible_and_human_fields_stay_empty(
    multicrop_config: dict,
) -> None:
    result = command_prepare(multicrop_config)
    assert result["status"] == "manual_review_required"
    review_dir = Path(multicrop_config["dataset"]["review_directory"])
    for class_id in ("padi", "jagung", "cabai", "kacang_tanah"):
        assert (review_dir / f"review_{class_id}_01.jpg").is_file()
    template = review_dir / "manual_review_template.csv"
    first = template.read_text(encoding="utf-8")
    rows = read_csv_rows(template)
    assert all(not row[field] for row in rows for field in HUMAN_REVIEW_FIELDS)
    assert {row["source_type"] for row in rows if row["class_id"] == "padi"} == {
        "public",
        "local_aikmel",
    }
    assert all(row["source_type"] == "public" for row in rows if row["class_id"] != "padi")
    command_prepare(multicrop_config)
    assert template.read_text(encoding="utf-8") == first


def test_prepare_preserves_raw_dataset(multicrop_config: dict) -> None:
    raw_root = Path(multicrop_config["classes"][0]["sources"][0]["directory"]).parents[1]
    before = {path: sha256_file(path) for path in raw_root.rglob("*") if path.is_file()}
    command_prepare(multicrop_config)
    after = {path: sha256_file(path) for path in raw_root.rglob("*") if path.is_file()}
    assert before == after


def test_public_only_classes_do_not_generate_missing_local_warning(
    multicrop_config: dict,
) -> None:
    result = command_prepare(multicrop_config)
    assert not any(
        class_id in warning and "local" in warning.casefold()
        for class_id in ("jagung", "cabai", "kacang_tanah")
        for warning in result["warnings"]
    )


def test_curated_names_are_consistent(multicrop_config: dict) -> None:
    prepare_final(multicrop_config)
    processed = Path(multicrop_config["dataset"]["processed_directory"])
    names = [
        path.name
        for split in ("train", "validation")
        for path in (processed / split).rglob("*.jpg")
    ]
    assert names
    assert all(re.fullmatch(r"(padi|jagung|cabai|kacang_tanah)_\d{4}\.jpg", name) for name in names)


def test_manual_review_gate_prevents_final_split_and_package(multicrop_config: dict) -> None:
    result = command_prepare(multicrop_config)
    reports = Path(multicrop_config["dataset"]["reports_directory"])
    processed = Path(multicrop_config["dataset"]["processed_directory"])
    package = Path(multicrop_config["dataset"]["packages_directory"]) / "dataset_multicrop_v1.zip"
    assert result["status"] == "manual_review_required"
    assert result["final_dataset_created"] is False
    assert result["manual_review"]["pending"] > 0
    assert not (processed / "train").exists()
    assert not (processed / "validation").exists()
    assert not (reports / "split_manifest.csv").exists()
    assert not package.exists()


def test_unsure_decision_blocks_final_split(multicrop_config: dict) -> None:
    command_prepare(multicrop_config)
    template = Path(multicrop_config["dataset"]["review_directory"]) / "manual_review_template.csv"
    rows = read_csv_rows(template)
    for index, row in enumerate(rows):
        row["accepted"] = "unsure" if index == 0 else "yes"
    write_csv(template, rows, list(rows[0]))

    result = command_prepare(multicrop_config)
    assert result["status"] == "manual_review_required"
    assert result["manual_review"]["unsure"] == 1
    assert result["manual_review"]["pending"] == 0
    processed = Path(multicrop_config["dataset"]["processed_directory"])
    assert not (processed / "train").exists()
    assert not (processed / "validation").exists()


def test_rejected_image_never_enters_final_dataset(multicrop_config: dict) -> None:
    command_prepare(multicrop_config)
    template = Path(multicrop_config["dataset"]["review_directory"]) / "manual_review_template.csv"
    rows = read_csv_rows(template)
    rejected_name = next(row["curated_file_name"] for row in rows if row["class_id"] == "padi")
    complete_manual_review(multicrop_config, rejected={rejected_name})
    result = command_prepare(multicrop_config)
    assert result["status"] == "final_dataset_prepared"

    mapping = read_csv_rows(
        Path(multicrop_config["dataset"]["reports_directory"]) / "curation_mapping.csv"
    )
    rejected = next(row for row in mapping if row["curated_file_name"] == rejected_name)
    assert rejected["manual_review_status"] == "no"
    assert rejected["final_status"] == "rejected_manual"
    processed = Path(multicrop_config["dataset"]["processed_directory"])
    assert not any(path.name == rejected_name for path in processed.rglob("*.jpg"))


def test_package_is_not_created_when_manual_review_is_incomplete(
    multicrop_config: dict,
) -> None:
    command_prepare(multicrop_config)
    with pytest.raises(PackageBlockedError, match="Manual review is incomplete"):
        create_dataset_package(multicrop_config, tests_passed=True)
    package = Path(multicrop_config["dataset"]["packages_directory"]) / "dataset_multicrop_v1.zip"
    assert not package.exists()


def test_package_is_not_created_when_metadata_is_invalid(multicrop_config: dict) -> None:
    prepare_final(multicrop_config)
    metadata_path = (
        Path(multicrop_config["dataset"]["processed_directory"]) / "train" / "metadata.jsonl"
    )
    rows = read_jsonl(metadata_path)
    rows[0]["text"] = "caption without a trigger"
    metadata_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(PackageBlockedError, match="Metadata validation failed"):
        create_dataset_package(multicrop_config, tests_passed=True)
    package = Path(multicrop_config["dataset"]["packages_directory"]) / "dataset_multicrop_v1.zip"
    assert not package.exists()


def test_package_is_reopened_and_checksum_is_verified(multicrop_config: dict) -> None:
    prepare_final(multicrop_config)
    result = create_dataset_package(multicrop_config, tests_passed=True)
    zip_path = Path(str(result["zip"]))
    checksum_path = Path(str(result["checksum_file"]))

    assert result["zip_validation"]["valid"] is True
    assert result["sha256"] == sha256_file(zip_path)
    assert checksum_path.read_text(encoding="ascii").split()[0] == result["sha256"]
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
    assert "dataset_multicrop_v1/processed/train/metadata.jsonl" in names
    assert "dataset_multicrop_v1/processed/validation/metadata.jsonl" in names
    assert "dataset_multicrop_v1/PACKAGE_MANIFEST.json" in names
    assert not any("/raw/" in name or "/.venv/" in name for name in names)


def test_final_package_validation_reports_valid_package(multicrop_config: dict) -> None:
    prepare_final(multicrop_config)
    create_dataset_package(multicrop_config, tests_passed=True)

    result = validate_final_dataset_package(multicrop_config)

    assert result["valid"] is True
    assert result["training_allowed"] is True
    assert result["package"]["checksum_valid"] is True
    assert Path(result["reports"]["json"]).is_file()
    assert Path(result["reports"]["markdown"]).is_file()


def test_final_package_validation_reports_blockers(multicrop_config: dict) -> None:
    command_prepare(multicrop_config)

    result = validate_final_dataset_package(multicrop_config)

    assert result["valid"] is False
    assert result["training_allowed"] is False
    assert any(
        check["id"] == "review_complete" and not check["passed"] for check in result["checks"]
    )
    assert any(
        check["id"] == "package_checksum" and not check["passed"] for check in result["checks"]
    )


def test_package_is_not_created_when_a_class_is_below_minimum(
    multicrop_config: dict,
) -> None:
    command_prepare(multicrop_config)
    template = Path(multicrop_config["dataset"]["review_directory"]) / "manual_review_template.csv"
    rows = read_csv_rows(template)
    rejected_name = next(row["curated_file_name"] for row in rows if row["class_id"] == "jagung")
    complete_manual_review(multicrop_config, rejected={rejected_name})

    result = command_prepare(multicrop_config)
    assert result["status"] == "insufficient_final_images"
    assert result["shortfalls"]["jagung"] == {
        "accepted": 3,
        "minimum": 4,
        "shortfall": 1,
    }
    balance = read_csv_rows(
        Path(multicrop_config["dataset"]["reports_directory"]) / "class_balance_report.csv"
    )
    jagung_balance = next(row for row in balance if row["class_id"] == "jagung")
    assert jagung_balance["curated_count"] == "3"
    assert jagung_balance["manual_accepted_count"] == "3"
    assert jagung_balance["manual_rejected_count"] == "1"
    assert jagung_balance["shortfall_to_minimum"] == "1"
    assert jagung_balance["target_status"] == "below_minimum"
    with pytest.raises(PackageBlockedError, match="minimum"):
        create_dataset_package(multicrop_config, tests_passed=True)
    package = Path(multicrop_config["dataset"]["packages_directory"]) / "dataset_multicrop_v1.zip"
    assert not package.exists()


def test_audit_detects_exif_orientation_and_same_content_different_extension(
    multicrop_config: dict,
) -> None:
    public_padi = Path(multicrop_config["classes"][0]["sources"][0]["directory"])
    oriented = Image.new("RGB", (96, 128), "green")
    exif = Image.Exif()
    exif[274] = 6
    oriented.save(public_padi / "oriented.jpg", exif=exif)
    shutil.copy2(public_padi / "padi_2.png", public_padi / "same_bytes.jpg")

    records, duplicates = audit_fixture(multicrop_config)
    orientation_record = next(record for record in records if record.file_name == "oriented.jpg")
    assert orientation_record.exif_orientation == "6"
    assert orientation_record.exif_orientation_status == "requires_transpose"
    assert any(row["same_content_different_extension"] for row in duplicates["exact"])


def test_cli_filters_and_missing_dataset_error(multicrop_config: dict, tmp_path: Path) -> None:
    args = build_parser().parse_args(
        [
            "audit",
            "--config",
            "fixture.yaml",
            "--class",
            "cabai",
        ]
    )
    filtered = apply_class_filter(
        multicrop_config,
        args.class_id,
        all_classes=args.all_classes,
    )
    assert [item["id"] for item in class_definitions(filtered)] == ["cabai"]

    missing = deepcopy(multicrop_config)
    for item in missing["classes"]:
        for source in item["sources"]:
            source["directory"] = str(tmp_path / "not_available" / item["id"] / source["type"])
    with pytest.raises(DatasetNotAvailableError, match="Dataset raw is not available"):
        build_inventory(missing)


def test_confusion_review_template_leaves_human_fields_empty(tmp_path: Path) -> None:
    target = tmp_path / "class_confusion_review.csv"
    write_confusion_review_template(
        target,
        [
            {
                "expected_class": "padi",
                "prompt": "taniadaptif_padi, rice plants in an agricultural environment",
                "seed": 42,
            }
        ],
    )
    row = read_csv_rows(target)[0]
    assert row["expected_class"] == "padi"
    assert row["predicted_visual_class"] == ""
    assert row["class_correct"] == ""
    assert row["mixed_crop_detected"] == ""
