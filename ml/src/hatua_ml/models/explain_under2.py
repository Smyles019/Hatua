"""SHAP explanations for the under-24 short-form model.

Builds the Explainer against training visits, saves same-age averages
(peer_stats.json) next to the model so the API needs no training data, checks
that band base + contributions = model output, and prints one flagged example.

Run:  python -m hatua_ml.models.explain_under2
"""
import json

import joblib
import numpy as np
import pandas as pd

from hatua_ml.config import ARTEFACTS, ROOT
from hatua_ml.models.explain import UNDER2_BANDS, Explainer, under2_domains
from hatua_ml.models.train_under2 import inputs, load_table

MODEL_DIR = ARTEFACTS / "xgboost_under2" / "short_30"
LABELS = ROOT / "ml" / "src" / "hatua_ml" / "features" / "ddi_items.csv"


def load_explainer(model_dir=MODEL_DIR) -> tuple[Explainer, list[str]]:
    """Rebuild from saved artefacts only (what the API will do)."""
    art = joblib.load(model_dir / "model.joblib")
    peers = json.loads((model_dir / "peer_stats.json").read_text())
    exp = Explainer(art["model"], art["items"], threshold=art["threshold"], peer_stats=peers,
                    domains=under2_domains(art["items"]), bands=UNDER2_BANDS)
    return exp, art["items"]


def main() -> None:
    art = joblib.load(MODEL_DIR / "model.joblib")
    items, model = art["items"], art["model"]
    table = load_table()
    train = table[table["split"] == "train"].reset_index(drop=True)
    test = table[table["split"] == "test"].reset_index(drop=True)

    exp = Explainer(model, items, background=inputs(train, items), threshold=art["threshold"],
                    domains=under2_domains(items), bands=UNDER2_BANDS)
    (MODEL_DIR / "peer_stats.json").write_text(json.dumps(exp.peer_stats(), indent=2))

    X_te = inputs(test, items)
    c = exp.contributions(X_te)
    base = np.array([exp.base(a) for a in X_te["age_months"]])
    margin = model.predict(X_te, output_margin=True)
    gap = float(np.max(np.abs(base + c.sum(axis=1).to_numpy() - margin)))
    print(f"additivity: max |base + contributions - output| = {gap:.2e}")

    rebuilt, _ = load_explainer()
    same = np.allclose(rebuilt.contributions(X_te.head(200)), c.head(200))
    print("rebuilt from peer_stats.json matches:", same)

    results = exp.explain(X_te)
    flagged = [i for i, r in enumerate(results) if r["flagged"]]
    status = pd.DataFrame([{d: v["status"] for d, v in r["domains"].items()} for r in results])
    print(f"test visits flagged: {len(flagged)} of {len(results)}")
    print(status.apply(pd.Series.value_counts).fillna(0).astype(int).to_string())

    labels = pd.read_csv(LABELS).set_index("item")["label"]
    i = flagged[0]
    r = results[i]
    print(f"\nexample: age {X_te.loc[i, 'age_months']:.1f} months, daz {test.loc[i, 'daz']:.2f}")
    for d, v in r["domains"].items():
        print(f"  {d:16s} {v['status']:13s} items {v['n_items']}")
    for reason in r["top_reasons"]:
        print(f"  reason: {labels[reason['item']]} ({reason['domain']})")


if __name__ == "__main__":
    main()
