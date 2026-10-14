"""Logistic regression baseline on Kenya, for each item set."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from hatua_ml.config import ARTEFACTS
from hatua_ml.features.item_sets import ITEM_SETS
from hatua_ml.features.prepare import model_inputs, risk_target
from hatua_ml.models.evaluation import choose_threshold, evaluate, save_artefacts
from hatua_ml.models.split import kenya_split, load_feature_table


def make_model():
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))


def train(item_set: str) -> dict:
    items = ITEM_SETS[item_set]
    train_df, test_df = kenya_split(load_feature_table())
    X_tr, y_tr = model_inputs(train_df, items), risk_target(train_df)
    X_te, y_te = model_inputs(test_df, items), risk_target(test_df)

    model = make_model()
    threshold = choose_threshold(model, X_tr, y_tr)
    model.fit(X_tr, y_tr)
    metrics = {"item_set": item_set, **evaluate(y_te, model.predict_proba(X_te)[:, 1], threshold)}
    save_artefacts(ARTEFACTS / "logreg" / item_set, model, items, threshold, metrics)
    return metrics


if __name__ == "__main__":
    for name in ITEM_SETS:
        m = train(name)
        print(f"{name:7s} auc {m['auc']:.3f}  sensitivity {m['sensitivity']:.3f}  "
              f"specificity {m['specificity']:.3f}  (n={m['n_test']})")