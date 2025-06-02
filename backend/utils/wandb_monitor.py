import os, time
import wandb
from ..config import settings

# Initialise once per worker
_run = wandb.init(
    project=settings.WANDB_PROJECT,
    entity=settings.WANDB_ENTITY,
    config={
        "llm_model": settings.LLM_MODEL_NAME,
        "dataset": f"{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}",
        "handler_type": settings.QUERY_HANDLER_TYPE,
    },
    mode="disabled" if settings.WANDB_DISABLED == "true" else "online",
)

def log_event(name: str, payload: dict):
    """
    Thin wrapper so production code never crashes if W&B is off.
    """
    if _run:
        wandb.log({name: payload, f"{name}/timestamp": time.time()})
