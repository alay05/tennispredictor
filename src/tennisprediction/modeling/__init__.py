"""Frozen modeling dataset, artifact registry, and chronological split contracts."""

from tennisprediction.modeling.datasets import materialize_modeling_dataset
from tennisprediction.modeling.metrics import build_segment_diagnostics
from tennisprediction.modeling.registry import (
    load_model_artifact_bundle,
    write_model_artifact_bundle,
)
from tennisprediction.modeling.reports import write_model_reports
from tennisprediction.modeling.schemas import (
    FrozenModelingDataset,
    FrozenSplitManifest,
    FrozenSplitWindow,
    ModelArtifactManifest,
    ModelingRow,
    SegmentDiagnosticRow,
)
from tennisprediction.modeling.splits import (
    SplitBoundaryConfig,
    freeze_chronological_splits,
    load_split_manifest,
)

__all__ = [
    "ModelingRow",
    "FrozenModelingDataset",
    "FrozenSplitWindow",
    "FrozenSplitManifest",
    "ModelArtifactManifest",
    "SegmentDiagnosticRow",
    "SplitBoundaryConfig",
    "materialize_modeling_dataset",
    "build_segment_diagnostics",
    "write_model_reports",
    "write_model_artifact_bundle",
    "load_model_artifact_bundle",
    "freeze_chronological_splits",
    "load_split_manifest",
]
