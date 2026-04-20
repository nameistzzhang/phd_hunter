"""FastAPI backend for PhD Hunter."""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio

from . import __version__
from .main import PhDHunter
from .models import SearchQuery, SearchResult, Professor, Report

app = FastAPI(
    title="PhD Hunter API",
    description="PhD advisor matching and analysis API",
    version=__version__,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global hunter instance
hunter: Optional[PhDHunter] = None
_search_results: dict[str, SearchResult] = {}


def get_hunter() -> PhDHunter:
    """Get or create PhDHunter instance."""
    global hunter
    if hunter is None:
        hunter = PhDHunter()
    return hunter


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": __version__}


@app.post("/api/search")
async def start_search(query: SearchQuery, background_tasks: BackgroundTasks):
    """Start a new professor search."""
    h = get_hunter()

    search_id = f"search_{hash(str(query.dict()))}"

    # Start search in background
    async def run_search():
        result = await h.search(
            universities=query.universities,
            research_area=query.research_area,
            keywords=query.keywords,
            max_professors=query.max_professors,
        )
        _search_results[search_id] = result

    background_tasks.add_task(run_search)

    return {
        "search_id": search_id,
        "status": "running",
        "estimated_time": 120,
        "results_url": f"/api/search/{search_id}/results"
    }


@app.get("/api/search/{search_id}/status")
async def get_search_status(search_id: str):
    """Get search status."""
    if search_id not in _search_results:
        return {"search_id": search_id, "status": "running", "progress": 0}
    result = _search_results[search_id]
    return {
        "search_id": search_id,
        "status": "completed",
        "progress": 100,
        "result_count": len(result.professors)
    }


@app.get("/api/search/{search_id}/results")
async def get_search_results(search_id: str):
    """Get search results."""
    result = _search_results.get(search_id)
    if not result:
        raise HTTPException(status_code=404, detail="Search not found")
    return result


@app.get("/api/professors")
async def list_professors(
    university: Optional[str] = None,
    min_score: Optional[float] = None,
    limit: int = 100
):
    """List cached professors."""
    # Implementation would query database/cache
    return {"message": "Not implemented yet"}


@app.get("/api/professors/{professor_id}")
async def get_professor(professor_id: str):
    """Get professor details."""
    # Implementation would fetch from cache/db
    return {"message": "Not implemented yet"}


@app.post("/api/reports/generate")
async def generate_report(professor_id: str, format: str = "html"):
    """Generate report for a professor."""
    return {"message": "Not implemented yet"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
