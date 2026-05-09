from __future__ import annotations

MACRO_PACKET_FIELDS = [
    "protein_g",
    "carbs_g",
    "fat_g",
    "macro_visibility_status",
    "macro_source_basis",
    "macro_confidence",
]
MACRO_CONTRACT = {
    "packet_fields": MACRO_PACKET_FIELDS,
    "macro_truth_owner": "fooddb_approved_packet",
    "missing_macro_policy": "preserve_null_do_not_invent",
}
APPROVED_PACKET_READY_SCHEMA_VERSION = "fooddb_approved_packet_ready_artifact_v1"
APPROVED_PACKET_READY_SOURCE_QUALITY = "packet_ready_approved"


__all__ = [
    "APPROVED_PACKET_READY_SCHEMA_VERSION",
    "APPROVED_PACKET_READY_SOURCE_QUALITY",
    "MACRO_CONTRACT",
    "MACRO_PACKET_FIELDS",
]
