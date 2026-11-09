"""Versioned model release for the API (#33).

A release is one folder holding everything inference needs, and nothing else:

    ml/artefacts/release/<version>/
        risk_model.joblib       XGBoost risk model, items and cut-off
        anomaly_flagger.joblib  Isolation Forest flagger (Kenya)
        peer_stats.json         same-age averages for the SHAP explainer
        manifest.json           version, items, cut-offs, metrics, library versions, checksums

Releases are never overwritten. The API loads one with load_release(path).

Two cut-offs on the risk probability: the screening cut-off (95% target sensitivity)
separates low from flagged, and the high-risk cut-off (99% specificity among on-track
training children) splits flagged into medium and high. Both come from training-data
cross-validation only. Releases built before the second cut-off existed (1.0.0) have no
high_threshold; the API then falls back to a provisional value and says so.

Run: python -m hatua_ml.export <version>          e.g. python -m hatua_ml.export 1.0.0
"""
import hashlib
import json
import platform
import shutil
import sys
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version
from pathlib import Path

import joblib

from hatua_ml.config import ARTEFACTS
from hatua_ml.models.evaluation import (HIGH_RISK_SPECIFICITY, TARGET_SENSITIVITY,
                                        choose_high_threshold, cv_probabilities)
from hatua_ml.models.explain import DOMAINS, Explainer

RELEASES = ARTEFACTS / "release"
ITEM_SET = "short13"
FILES = ("risk_model.joblib", "anomaly_flagger.joblib", "peer_stats.json")
LIBRARIES = ("xgboost", "scikit-learn", "pyod", "shap", "numpy", "pandas", "joblib")


class ReleaseError(Exception):
    """A release folder is missing, incomplete or altered."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(version: str, item_set: str = ITEM_SET, releases: Path = RELEASES) -> Path:
    """Build a release from the trained artefacts. Fails if the version already exists."""
    from hatua_ml.features.prepare import model_inputs, risk_target
    from hatua_ml.models.split import kenya_split, load_feature_table

    out = releases / version
    if out.exists():
        raise ReleaseError(f"release {version} already exists; releases are never overwritten")

    risk_dir = ARTEFACTS / "xgboost" / item_set
    flag_dir = ARTEFACTS / "anomaly" / "iforest" / item_set
    for d in (risk_dir, flag_dir):
        if not (d / "model.joblib").is_file():
            raise ReleaseError(f"missing trained artefact in {d}")
    risk = joblib.load(risk_dir / "model.joblib")
    flagger = joblib.load(flag_dir / "model.joblib")["model"]
    if risk["items"] != flagger.items_:
        raise ReleaseError("risk model and anomaly flagger were trained on different items")

    train, _ = kenya_split(load_feature_table())
    X, y = model_inputs(train, risk["items"]), risk_target(train)
    high = choose_high_threshold(cv_probabilities(risk["model"], X, y), y, risk["threshold"])
    return write_release(
        out, version=version, item_set=item_set, model=risk["model"], items=risk["items"],
        threshold=risk["threshold"], high_threshold=high, flagger=flagger,
        explainer=Explainer(risk["model"], risk["items"], X, risk["threshold"]),
        test_metrics=json.loads((risk_dir / "metrics.json").read_text()),
        fitted_on="Kenya KDHS 2022 training children")


def write_release(out: Path, *, version, item_set, model, items, threshold, high_threshold,
                  flagger, explainer, test_metrics, fitted_on) -> Path:
    """Write the release files and manifest to out (which must not exist yet).

    Split from export() so tests can build a small release from synthetic data without
    the survey files."""
    out = Path(out)
    if out.exists():
        raise ReleaseError(f"release {version} already exists; releases are never overwritten")
    out.mkdir(parents=True)
    try:
        joblib.dump({"model": model, "items": list(items), "threshold": float(threshold)},
                    out / "risk_model.joblib")
        joblib.dump(flagger, out / "anomaly_flagger.joblib")
        (out / "peer_stats.json").write_text(json.dumps(explainer.peer_stats(), indent=2))
        manifest = {
            "version": version,
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "item_set": item_set,
            "items": list(items),  # model input order: age_months, female, then these
            "domains": {d: [i for i in members if i in items] for d, members in DOMAINS.items()},
            "age_range_months": [24, 59],
            "risk": {"threshold": float(threshold), "target_sensitivity": TARGET_SENSITIVITY,
                     "high_threshold": float(high_threshold),
                     "high_specificity": HIGH_RISK_SPECIFICITY,
                     "test_metrics": test_metrics},
            "anomaly": {"threshold": flagger.threshold_, "detector": flagger.kind,
                        "fitted_on": fitted_on},
            "python": platform.python_version(),
            "libraries": {lib: pkg_version(lib) for lib in LIBRARIES},
            "files": {name: sha256(out / name) for name in FILES},
        }
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    except Exception:
        shutil.rmtree(out)  # never leave a half-written release behind
        raise
    return out


def load_release(path: Path) -> dict:
    """Load and verify a release. Returns risk model, items, threshold, flagger, explainer."""
    path = Path(path)
    manifest_path = path / "manifest.json"
    if not manifest_path.is_file():
        raise ReleaseError(f"no manifest.json in {path}")
    manifest = json.loads(manifest_path.read_text())
    for name, expected in manifest["files"].items():
        if not (path / name).is_file():
            raise ReleaseError(f"{name} missing from release {manifest['version']}")
        if sha256(path / name) != expected:
            raise ReleaseError(f"{name} does not match its checksum; release altered")

    risk = joblib.load(path / "risk_model.joblib")
    peer_stats = json.loads((path / "peer_stats.json").read_text())
    return {
        "manifest": manifest,
        "model": risk["model"],
        "items": risk["items"],
        "threshold": risk["threshold"],
        # None for releases made before the second cut-off existed (1.0.0)
        "high_threshold": manifest["risk"].get("high_threshold"),
        "flagger": joblib.load(path / "anomaly_flagger.joblib"),
        "explainer": Explainer(risk["model"], risk["items"], threshold=risk["threshold"],
                               peer_stats=peer_stats),
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m hatua_ml.export <version>")
    print("release written to", export(sys.argv[1]))
