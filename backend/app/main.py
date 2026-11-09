from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, assessments, auth, children, chw, dev
from app.core.config import settings

settings.check()

app = FastAPI(title="Hatua API", version="0.2.0",
              description="Developmental risk prediction and milestone monitoring for "
                          "children under five. Sign in with Authorize (username = phone).")
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(children.router, prefix="/children", tags=["children"])
app.include_router(assessments.router, prefix="/assessments", tags=["assessments"])
app.include_router(chw.router, prefix="/chw", tags=["chw"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])

app.add_middleware(CORSMiddleware,
                   allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                   allow_methods=["*"], allow_headers=["*"])

# Development only: the throwaway test UI at /test-ui (a stand-in until the Flutter app
# exists) and the helper it uses to sign in as an administrator.
TEST_UI = Path(__file__).resolve().parents[1] / "test_ui"
if settings.dev_mode:
    app.include_router(dev.router, prefix="/dev", tags=["development only"])
    if TEST_UI.is_dir():
        app.mount("/test-ui", StaticFiles(directory=TEST_UI, html=True), name="test-ui")

        @app.get("/", include_in_schema=False)
        def root():
            return RedirectResponse("/test-ui/")


@app.get("/health")
def health():
    return {"status": "ok"}
