from fastapi import FastAPI

from app.api.routes import assessments

app = FastAPI(title="Hatua API", version="0.1.0")
app.include_router(assessments.router, prefix="/assessments", tags=["assessments"])


@app.get("/health")
def health():
    return {"status": "ok"}
