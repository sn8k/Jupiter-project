"""
server/api.py – Endpoints API du plugin (enregistrés via Bridge).
Version: 0.3.0

Conforme à plugins_architecture.md v0.4.0
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncio

router = APIRouter(prefix="/example", tags=["example_plugin"])

# Référence au Bridge (injectée via register_api_contribution)
_bridge = None


@router.get("/")
async def get_example():
    """
    Retourne un exemple de données.
    """
    return {"message": "Hello from Example Plugin", "status": "ok"}


@router.post("/")
async def post_example(payload: dict):
    """
    Reçoit des données et retourne une confirmation.
    """
    return {"received": payload, "status": "ok"}


@router.get("/health")
async def health():
    """
    Endpoint de healthcheck exposé pour le Bridge et /health global.
    Doit être rapide et idempotent (§3.5).
    """
    return {"status": "ok", "plugin": "example_plugin"}


@router.get("/metrics")
async def get_metrics():
    """
    Retourne les métriques du plugin (§10.2).
    Le Bridge collecte ces métriques et les expose via /metrics global.
    """
    from .. import metrics
    return metrics()


# === Logs endpoints (§10.3) ===

@router.get("/logs")
async def download_logs():
    """
    Télécharge le fichier log complet du plugin.
    """
    import os
    log_path = "jupiter/plugins/example_plugin/logs/plugin.log"
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="Log file not found")
    
    def iter_file():
        with open(log_path, "r") as f:
            yield from f
    
    return StreamingResponse(
        iter_file(),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=example_plugin.log"}
    )


@router.get("/logs/stream")
async def stream_logs():
    """
    WebSocket pour logs temps réel.
    Note: En production, utiliser un vrai WebSocket handler.
    """
    # Placeholder - en production, utiliser websocket
    return {"message": "Use WebSocket connection for real-time logs"}


# === Jobs endpoints (§10.6) ===

@router.get("/jobs")
async def list_jobs():
    """
    Liste les jobs du plugin (en cours, terminés récemment).
    """
    if not _bridge:
        raise HTTPException(status_code=503, detail="Plugin not initialized")
    
    jobs = await _bridge.jobs.list(plugin_id="example_plugin")
    return {"jobs": jobs}


@router.post("/jobs")
async def create_job(payload: dict):
    """
    Crée un nouveau job asynchrone (§10.6).
    
    Le job est suivi via WebSocket (événements JOB_STARTED, JOB_PROGRESS, JOB_COMPLETED, JOB_FAILED).
    """
    if not _bridge:
        raise HTTPException(status_code=503, detail="Plugin not initialized")
    
    from .. import submit_long_task
    job_id = await submit_long_task(payload)
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Job submitted. Track progress via WebSocket."
    }


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """
    Annule un job en cours (pattern coopératif §10.6).
    """
    if not _bridge:
        raise HTTPException(status_code=503, detail="Plugin not initialized")
    
    success = await _bridge.jobs.cancel(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or already completed")
    
    return {"job_id": job_id, "status": "cancelling"}


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Retourne le statut d'un job spécifique.
    """
    if not _bridge:
        raise HTTPException(status_code=503, detail="Plugin not initialized")
    
    job = await _bridge.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


# === Settings endpoints ===

@router.post("/reset-settings")
async def reset_settings():
    """
    Réinitialise les paramètres du plugin (§8 remote reset support).
    """
    from .. import reset_settings as do_reset
    result = do_reset()
    return result


@router.get("/changelog")
async def get_changelog():
    """
    Retourne le changelog du plugin (§10.4).
    """
    import os
    changelog_path = "jupiter/plugins/example_plugin/changelog.md"
    if not os.path.exists(changelog_path):
        # Fallback sur le changelog du plugin_model
        changelog_path = "docs/plugin_model/changelog.md"
    
    if os.path.exists(changelog_path):
        with open(changelog_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    
    return {"content": "No changelog available."}


def register_api_contribution(app, bridge=None):
    """
    Appelé par le Bridge pour monter les routes.
    
    Args:
        app: Instance FastAPI principale.
        bridge: Instance du Bridge (optionnel, pour accès aux services).
    """
    global _bridge
    _bridge = bridge
    app.include_router(router)
