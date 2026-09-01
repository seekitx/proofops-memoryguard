from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from importlib import import_module
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from typing import Any

SIBYL_SDK_DISTRIBUTION = "sibyl-memory-client"
EXPECTED_SIBYL_SDK_VERSION = "0.7.0"
# The pinned 0.7.0 wheel's bundled schema.sql records versions 1 through 4.
EXPECTED_SIBYL_SCHEMA_VERSION = 4
_REQUIRED_RUNTIME_FILES = {
    "sibyl_memory_client/__init__.py",
    "sibyl_memory_client/client.py",
    "sibyl_memory_client/storage.py",
    "sibyl_memory_client/schema.sql",
}


@lru_cache(maxsize=1)
def sibyl_sdk_identity() -> dict[str, Any]:
    """Return non-secret evidence binding the import to pinned package metadata."""

    try:
        installed_distribution = distribution(SIBYL_SDK_DISTRIBUTION)
        installed_version = installed_distribution.version
        module = import_module("sibyl_memory_client")
        module_file = Path(str(module.__file__)).resolve()
        recorded_entry = next(
            (
                entry
                for entry in (installed_distribution.files or ())
                if Path(installed_distribution.locate_file(entry)).resolve() == module_file
            ),
            None,
        )
        import_file_recorded = recorded_entry is not None
        import_file_hash_matches_record = False
        if recorded_entry is not None and recorded_entry.hash is not None:
            file_hash = hashlib.new(recorded_entry.hash.mode, module_file.read_bytes()).digest()
            encoded_hash = base64.urlsafe_b64encode(file_hash).decode().rstrip("=")
            import_file_hash_matches_record = encoded_hash == recorded_entry.hash.value
        runtime_entries = [
            entry
            for entry in (installed_distribution.files or ())
            if entry.hash is not None
            and str(entry).startswith("sibyl_memory_client/")
            and Path(str(entry)).suffix in {".py", ".sql"}
        ]
        recorded_runtime_files = {str(entry) for entry in runtime_entries}
        required_runtime_files_recorded = _REQUIRED_RUNTIME_FILES.issubset(
            recorded_runtime_files
        )
        runtime_file_hashes_match = bool(runtime_entries) and all(
            base64.urlsafe_b64encode(
                hashlib.new(
                    entry.hash.mode,
                    Path(installed_distribution.locate_file(entry)).read_bytes(),
                ).digest()
            )
            .decode()
            .rstrip("=")
            == entry.hash.value
            for entry in runtime_entries
            if entry.hash is not None
        )
    except (
        PackageNotFoundError,
        ImportError,
        ModuleNotFoundError,
        TypeError,
        OSError,
        ValueError,
    ):
        return {
            "sdk_distribution": SIBYL_SDK_DISTRIBUTION,
            "sdk_version": None,
            "sdk_version_expected": EXPECTED_SIBYL_SDK_VERSION,
            "sdk_import_file_recorded_by_distribution": False,
            "sdk_import_file_hash_matches_record": False,
            "sdk_required_runtime_files_recorded": False,
            "sdk_runtime_file_hashes_match_record": False,
            "sdk_version_matches_pin": False,
            "sdk_identity_ready": False,
        }
    version_matches = installed_version == EXPECTED_SIBYL_SDK_VERSION
    return {
        "sdk_distribution": SIBYL_SDK_DISTRIBUTION,
        "sdk_version": installed_version,
        "sdk_version_expected": EXPECTED_SIBYL_SDK_VERSION,
        "sdk_import_file_recorded_by_distribution": import_file_recorded,
        "sdk_import_file_hash_matches_record": import_file_hash_matches_record,
        "sdk_required_runtime_files_recorded": required_runtime_files_recorded,
        "sdk_runtime_file_hashes_match_record": runtime_file_hashes_match,
        "sdk_version_matches_pin": version_matches,
        "sdk_identity_ready": (
            import_file_recorded
            and import_file_hash_matches_record
            and required_runtime_files_recorded
            and runtime_file_hashes_match
            and version_matches
        ),
    }
