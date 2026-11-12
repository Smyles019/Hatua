"""Copy i18n/sw.json into the app (app/assets/i18n/sw.json), which carries its own copy so
it works offline. Run after changing the Swahili file, before building the app.
The backend and the website read i18n/sw.json directly and need nothing."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
target = ROOT / "app" / "assets" / "i18n" / "sw.json"
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(ROOT / "i18n" / "sw.json", target)
print("copied to", target)
