"""Load item-level Birth to Twenty data (childdevdata gcdg_zaf) for under-24-month norms."""
import pyreadr

from hatua_ml.config import CHILDDEV_ZAF


def load_zaf():
    return pyreadr.read_r(str(CHILDDEV_ZAF))["gcdg_zaf"]


if __name__ == "__main__":
    d = load_zaf()
    print(d.shape)
    print(d.head())
