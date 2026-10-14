"""Tests for the versioned model release (#33)."""
import json

import numpy as np
import pandas as pd
import pytest
from xgboost import XGBClassifier

from hatua_ml.config import ARTEFACTS
from hatua_ml.export import FILES, ReleaseError, export, load_release
from hatua_ml.features.build_table import FEATURE_TABLE
from hatua_ml.features.item_sets import SHORT_FORM_13
from hatua_ml.features.prepare import model_inputs
from hatua_ml.models.explain import Explainer


# --- explainer rebuilt from saved peer averages (always runs, synthetic) ---

def test_explainer_from_peer_stats_matches_one_built_from_training_data():
    rng = np.random.default_rng(0)
    items = ["ecd24", "ecd27", "ecd32", "ecd36"]
    df = pd.DataFrame({"age_months": rng.uniform(24, 59, 600), "sex": rng.integers(1, 3, 600),
                       **{i: rng.integers(0, 2, 600).astype(float) for i in items}})
    X = model_inputs(df, items)
    y = (X[items].sum(axis=1) < 2).astype(int)
    model = XGBClassifier(n_estimators=30, max_depth=2, random_state=0).fit(X, y)

    original = Explainer(model, items, X, threshold=0.5)
    stats = json.loads(json.dumps(original.peer_stats()))  # through JSON, as on disk
    rebuilt = Explainer(model, items, threshold=0.5, peer_stats=stats)
    pd.testing.assert_frame_equal(original.contributions(X), rebuilt.contributions(X))
    assert original.explain(X.head(20)) == rebuilt.explain(X.head(20))


# --- full release from the trained artefacts (skips until trained) ---

needs_artefacts = pytest.mark.skipif(
    not (FEATURE_TABLE.is_file()
         and (ARTEFACTS / "xgboost" / "short13" / "model.joblib").is_file()
         and (ARTEFACTS / "anomaly" / "iforest" / "short13" / "model.joblib").is_file()),
    reason="feature table or short13 artefacts missing")


@pytest.fixture(scope="module")
def release(tmp_path_factory):
    return export("0.0.0-test", releases=tmp_path_factory.mktemp("releases"))


@needs_artefacts
def test_release_contains_exactly_the_expected_files_and_manifest(release):
    assert sorted(p.name for p in release.iterdir()) == sorted([*FILES, "manifest.json"])
    m = json.loads((release / "manifest.json").read_text())
    assert m["version"] == "0.0.0-test"
    assert m["items"] == SHORT_FORM_13
    assert set(m["files"]) == set(FILES)
    assert sum(len(v) for v in m["domains"].values()) == len(SHORT_FORM_13)
    assert 0 < m["risk"]["threshold"] < 1 and m["risk"]["target_sensitivity"] == 0.95


@needs_artefacts
def test_loaded_release_gives_identical_answers_to_the_research_code(release):
    from hatua_ml.models.split import kenya_split, load_feature_table

    loaded = load_release(release)
    train, test = kenya_split(load_feature_table())
    items = loaded["items"]
    X = model_inputs(test, items)

    research = Explainer(loaded["model"], items, model_inputs(train, items), loaded["threshold"])
    assert loaded["explainer"].explain(X) == research.explain(X)

    flags = loaded["flagger"].flag(test)
    assert 0 < flags.mean() < 0.1


@needs_artefacts
def test_release_is_never_overwritten(release):
    with pytest.raises(ReleaseError, match="already exists"):
        export("0.0.0-test", releases=release.parent)


@needs_artefacts
def test_altered_or_missing_file_is_refused(release, tmp_path):
    import shutil

    altered = tmp_path / "altered"
    shutil.copytree(release, altered)
    stats = json.loads((altered / "peer_stats.json").read_text())
    stats["24-29"]["base"] += 1.0
    (altered / "peer_stats.json").write_text(json.dumps(stats, indent=2))
    with pytest.raises(ReleaseError, match="checksum"):
        load_release(altered)

    (altered / "anomaly_flagger.joblib").unlink()
    with pytest.raises(ReleaseError, match="missing"):
        load_release(altered)
