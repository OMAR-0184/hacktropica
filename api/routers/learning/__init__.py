"""
Learning router package — domain-focused sub-routers composed into one.

Previously a single 696-line file, now split into focused modules:
  - sessions:        Session lifecycle (create, list, poll, archive)
  - lessons:         Lesson retrieval
  - evaluation:      Quiz & evaluation
  - journey:         Journey orchestration (continue, next-action, choices)
  - progress:        Progress & workflow snapshots
  - graph_nodes:     Graph node CRUD (add, delete, expand)
  - websocket_route: Real-time WebSocket updates
"""

from fastapi import APIRouter

from api.routers.learning.sessions import router as sessions_router
from api.routers.learning.lessons import router as lessons_router
from api.routers.learning.evaluation import router as evaluation_router
from api.routers.learning.journey import router as journey_router
from api.routers.learning.progress import router as progress_router
from api.routers.learning.graph_nodes import router as graph_nodes_router
from api.routers.learning.websocket_route import router as websocket_router

router = APIRouter()

router.include_router(sessions_router)
router.include_router(lessons_router)
router.include_router(evaluation_router)
router.include_router(journey_router)
router.include_router(progress_router)
router.include_router(graph_nodes_router)
router.include_router(websocket_router)
