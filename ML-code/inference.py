"""
FastAPI app: load model from path (env MODEL_PATH or GCS), serve /predict.
"""
import os
import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from config_loader import load_config

_cfg = load_config()
PROJECT_ID = _cfg["project_id"]
FEATURE_COLUMNS = _cfg["feature_columns"]
ARTIFACTS_BUCKET = _cfg["artifacts_bucket"]
MODELS_GCS_PREFIX = _cfg["models_gcs_prefix"]
LATEST_SUBFOLDER = _cfg["latest_subfolder"]
MODEL_FILENAME = _cfg["model_filename"]

app = FastAPI(title="ML Inference API")
_model = None


def get_model_path() -> str:
    """Model path from env (local or gs://). Default: GCS latest."""
    path = os.environ.get("MODEL_PATH")
    if path:
        return path
    return f"gs://{ARTIFACTS_BUCKET}/{MODELS_GCS_PREFIX}/{LATEST_SUBFOLDER}/{MODEL_FILENAME}"


def load_model():
    """Load joblib model from MODEL_PATH or GCS latest."""
    global _model
    if _model is not None:
        return _model
    path = get_model_path()
    if path.startswith("gs://"):
        from google.cloud import storage
        parts = path.replace("gs://", "").split("/", 1)
        bucket_name, blob_name = parts[0], parts[1]
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        local = "/tmp/model.joblib"
        blob.download_to_filename(local)
        path = local
    _model = joblib.load(path)
    return _model


class PredictRequest(BaseModel):
    f1: float
    f2: float
    f3: float
    f4: float
    f5: float


class PredictResponse(BaseModel):
    prediction: float


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    try:
        model = load_model()
        X = [[req.f1, req.f2, req.f3, req.f4, req.f5]]
        pred = model.predict(X)[0]
        return PredictResponse(prediction=float(pred))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve frontend from same app (for single Cloud Run service)
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")


@app.get("/")
def serve_frontend():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.isfile(index_path):
        from fastapi.responses import FileResponse
        return FileResponse(index_path)
    return {"message": "Set FRONTEND_DIR or deploy with ML-code/frontend/index.html"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
