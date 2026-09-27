from fastapi import APIRouter

router = APIRouter()


@router.post("/")
def submit_assessment():
    """Validate, save, run inference and return the result. To be implemented."""
    raise NotImplementedError
