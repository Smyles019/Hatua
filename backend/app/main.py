import json
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, assessments, auth, children, chw, dev, messages
from app.core.config import settings
from app.services.i18n import _swahili

settings.check()

app = FastAPI(title="Hatua API", version="0.2.0",
              description="Developmental risk prediction and milestone monitoring for "
                          "children under five. Sign in with Authorize (username = email).")
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(children.router, prefix="/children", tags=["children"])
app.include_router(assessments.router, prefix="/assessments", tags=["assessments"])
app.include_router(chw.router, prefix="/chw", tags=["chw"])
app.include_router(messages.router, prefix="/messages", tags=["ask a CHW"])
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


# Hatua on the web (web/ at the repository root): one website for administrators, CHWs
# and caregivers, with the same accounts as the phone app. Plain files, no build step.
WEB = Path(__file__).resolve().parents[2] / "web"
if WEB.is_dir():
    app.mount("/web", StaticFiles(directory=WEB, html=True), name="web")

    # Browsers also ask for /favicon.ico on their own, so answer it with the same icon.
    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        return FileResponse(WEB / "favicon.svg", media_type="image/svg+xml")

    # Outside development the bare domain opens the website (in development / is the test UI).
    if not settings.dev_mode:
        @app.get("/", include_in_schema=False)
        def home():
            return RedirectResponse("/web/")


@app.get("/i18n/sw.js", include_in_schema=False)
def swahili_for_the_website():
    """The Swahili lines (i18n/sw.json) as a script the website loads before app.js."""
    body = "window.HATUA_SW = " + json.dumps(_swahili(), ensure_ascii=False) + ";\n"
    return Response(body, media_type="text/javascript; charset=utf-8",
                    headers={"Cache-Control": "no-cache"})


@app.get("/health")
def health():
    return {"status": "ok"}
