from sklearn.model_selection import GridSearchCV
from xgboost import XGBClassifier

from hatua_ml.config import ARTEFACTS
from hatua_ml.features.item_sets import ITEM_SETS
from hatua_ml.features.prepare import model_inputs, risk_target
from hatua_ml.models.evaluation import choose_threshold, cv, evaluate, save_artefacts
from hatua_ml.models.split import SEED, kenya_split, load_feature_table

PARAM_GRID = {
    "n_estimators": [400, 800],
    "max_depth": [1, 2, 3],
    "learning_rate": [0.1, 0.2],
    "subsample": [0.8, 1.0],
}


def make_model():
    return XGBClassifier(eval_metric="logloss", random_state=SEED, n_jobs=1)


def train(item_set: str) -> dict:
    items = ITEM_SETS[item_set]
    train_df, test_df = kenya_split(load_feature_table())
    X_tr, y_tr = model_inputs(train_df, items), risk_target(train_df)
    X_te, y_te = model_inputs(test_df, items), risk_target(test_df)

    search = GridSearchCV(make_model(), PARAM_GRID, scoring="roc_auc", cv=cv(), n_jobs=-1)
    search.fit(X_tr, y_tr)
    model = search.best_estimator_

    threshold = choose_threshold(model, X_tr, y_tr)
    metrics = {
        "item_set": item_set,
        **evaluate(y_te, model.predict_proba(X_te)[:, 1], threshold),
        "cv_auc": float(search.best_score_),
        "best_params": search.best_params_,
    }
    save_artefacts(ARTEFACTS / "xgboost" / item_set, model, items, threshold, metrics)
    return metrics


if __name__ == "__main__":
    for name in ITEM_SETS:
        m = train(name)
        print(f"{name:7s} auc {m['auc']:.3f}  sensitivity {m['sensitivity']:.3f}  "
              f"specificity {m['specificity']:.3f}  best {m['best_params']}")