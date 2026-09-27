"""Project paths. All paths resolve from the repository root."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
ARTEFACTS = ROOT / "ml" / "artefacts"

KDHS_FILE = RAW / "kdhs_2022" / "KEKR8CFL.DTA"
MICS_FILES = {
    "eswatini": RAW / "mics" / "eswatini" / "ch.sav",
    "comoros": RAW / "mics" / "comoros" / "ch.sav",
}
CHILDDEV_ZAF = RAW / "childdevdata" / "gcdg_zaf.rda"
