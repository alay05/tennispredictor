from __future__ import annotations

import csv
from dataclasses import dataclass

from tennisprediction.ingestion.manifests import SourceFileEntry, SourceManifest
from tennisprediction.ingestion.sackmann_contracts import classify_file_scope
from tennisprediction.ingestion.schemas import RawSchema, schema_for_file, validate_date_value


@dataclass(frozen=True)
class FileQuarantineRecord:
    relative_path: str
    reason: str
    source_url: str
    source_path: str
    size_bytes: int


@dataclass(frozen=True)
class ValidatedSnapshot:
    manifest: SourceManifest
    rows_by_file: dict[str, list[dict[str, str]]]
    quarantined_files: dict[str, FileQuarantineRecord]


def _validate_row_types(row: dict[str, str], schema: RawSchema, file_name: str) -> None:
    for column in schema.integer_columns:
        try:
            int(row[column])
        except (TypeError, ValueError) as exc:
            msg = f"{file_name}: column {column} must parse as integer"
            raise ValueError(msg) from exc

    for column in schema.optional_integer_columns:
        value = row.get(column, "")
        if value == "":
            continue
        try:
            int(value)
        except ValueError as exc:
            msg = f"{file_name}: optional column {column} must parse as integer when present"
            raise ValueError(msg) from exc

    for column in schema.date_columns:
        validate_date_value(row[column], file_name=file_name, column=column)


def _build_file_quarantine_record(entry: SourceFileEntry, *, reason: str) -> FileQuarantineRecord:
    return FileQuarantineRecord(
        relative_path=entry.relative_path.as_posix(),
        reason=reason,
        source_url=entry.source_url,
        source_path=entry.source_path,
        size_bytes=entry.size_bytes,
    )


def validate_snapshot(manifest: SourceManifest) -> ValidatedSnapshot:
    if not all(manifest.verify_checksums().values()):
        msg = "snapshot checksum verification failed"
        raise ValueError(msg)

    rows_by_file: dict[str, list[dict[str, str]]] = {}
    quarantined_files: dict[str, FileQuarantineRecord] = {}
    for entry in manifest.files:
        scope = classify_file_scope(entry.relative_path)
        if not scope.accepted:
            quarantined_files[entry.relative_path.as_posix()] = _build_file_quarantine_record(
                entry,
                reason=scope.reason or "unknown_file_family",
            )
            continue

        schema = schema_for_file(entry.relative_path)
        file_path = manifest.file_path(entry)
        with file_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                msg = f"{entry.relative_path}: missing header row"
                raise ValueError(msg)

            missing = [
                column for column in schema.required_columns if column not in reader.fieldnames
            ]
            if missing:
                msg = f"{entry.relative_path}: missing required columns {missing}"
                raise ValueError(msg)

            rows: list[dict[str, str]] = []
            for row in reader:
                _validate_row_types(row, schema, entry.relative_path.as_posix())
                rows.append(row)
            rows_by_file[entry.relative_path.as_posix()] = rows

    if not rows_by_file:
        msg = "no schema-valid ATP files were found in the snapshot"
        raise ValueError(msg)

    return ValidatedSnapshot(
        manifest=manifest,
        rows_by_file=rows_by_file,
        quarantined_files=quarantined_files,
    )
