from __future__ import annotations

from tennisprediction.modeling.datasets import materialize_modeling_dataset
from tests.unit.modeling_fixtures import build_synthetic_modeling_fixture


def test_materialize_modeling_dataset_joins_labels_and_orders_rows(tmp_path) -> None:
    fixture = build_synthetic_modeling_fixture(tmp_path)

    dataset = materialize_modeling_dataset(
        database_path=fixture.database_path,
        feature_version=fixture.feature_version,
    )

    assert [row.canonical_match_id for row in dataset.rows] == fixture.ordered_match_ids
    assert [row.target for row in dataset.rows[:6]] == [1, 1, 0, 1, 1, 0]

    earliest_row = dataset.rows[0]
    assert earliest_row.feature_version == fixture.feature_version
    assert earliest_row.as_of_date == "20240101"
    assert earliest_row.lineage_source_file_path == "atp_matches_2024.csv"
    assert earliest_row.lineage_source_row_number == 1
    assert earliest_row.feature_values["surface"] == "Clay"
    assert earliest_row.feature_values["elo_diff"] == 25.0

    tie_break_rows = [row for row in dataset.rows if row.as_of_date == "20240102"]
    assert [
        (row.lineage_source_file_path, row.lineage_source_row_number) for row in tie_break_rows
    ] == [
        ("atp_matches_2024.csv", 2),
        ("atp_matches_2024_extra.csv", 3),
    ]


def test_materialize_modeling_dataset_exposes_stable_feature_columns_and_lineage(tmp_path) -> None:
    fixture = build_synthetic_modeling_fixture(tmp_path)

    dataset = materialize_modeling_dataset(
        database_path=fixture.database_path,
        feature_version=fixture.feature_version,
    )

    assert dataset.feature_version == fixture.feature_version
    assert dataset.label_definition == "player_a_id == winner_canonical_player_id"
    assert dataset.feature_columns == fixture.expected_feature_columns

    feature_row = dataset.rows[5]
    assert set(feature_row.feature_values) == set(fixture.expected_feature_columns)
    assert feature_row.feature_values["player_a_rank"] == 16
    assert feature_row.feature_values["player_b_rank"] == 36
    assert feature_row.feature_values["service_first_won_rate_diff"] == 0.036
    assert feature_row.lineage_source_repo == "JeffSackmann/tennis_atp"
    assert feature_row.lineage_source_commit_sha == "abcdef1"
    assert feature_row.lineage_source_snapshot_root == "/tmp/raw-snapshot"
