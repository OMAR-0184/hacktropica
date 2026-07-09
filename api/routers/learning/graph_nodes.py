"""
Graph node CRUD endpoints — add, delete, expand.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.core import get_db
from api.database.models import User
from api.engine.runner import get_current_state, apply_state_updates
from api.routers.auth import get_current_user
from api.schemas.learning import (
    GraphNodeCreateRequest,
    GraphNodeMutationResponse,
)
from api.services.concurrency import acquire_progression_lock, release_progression_lock
from api.services.graph_helpers import (
    snapshot_next_nodes,
    normalize_node_list,
    normalize_children_map,
    is_journey_v2_enabled,
    build_node_catalog_list,
    derive_available_choices,
)
from api.services.graph_mutation_service import (
    build_add_node_updates,
    build_delete_node_updates,
    build_expand_node_updates,
)
from api.services.session_service import get_user_session

router = APIRouter()


@router.post("/{session_id}/nodes", response_model=GraphNodeMutationResponse)
async def add_graph_node(
    session_id: str,
    payload: GraphNodeCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Add a new node to the session knowledge graph."""
    db_session = await get_user_session(session_id, current_user.id, db)
    if db_session.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot modify graph while session is '{db_session.status}'.",
        )

    lock_ok, lock_key = await acquire_progression_lock(session_id)
    if not lock_ok:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Progression lock held."
        )
    try:
        snapshot = await get_current_state(session_id)
        if not snapshot or not snapshot.values:
            raise HTTPException(status_code=400, detail="Graph not initialized.")

        waiting_on = snapshot_next_nodes(snapshot)
        try:
            updates, added_node_id = build_add_node_updates(snapshot.values, payload)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
            )

        await apply_state_updates(session_id, updates)
        merged = {**snapshot.values, **updates}
        catalog = build_node_catalog_list(merged)
        added_node = next((m for m in catalog if m.node_id == added_node_id), None)
        options = derive_available_choices(
            merged,
            waiting_on=waiting_on,
            enable_backtracking=is_journey_v2_enabled(merged),
        )
        return GraphNodeMutationResponse(
            session_id=session_id,
            status="updated",
            message=f"Node '{added_node_id}' added successfully.",
            current_node=str(merged.get("current_node", "") or ""),
            added_node=added_node,
            removed_nodes=[],
            options=options,
            active_frontier=normalize_node_list(merged.get("active_frontier", [])),
            children_map=normalize_children_map(merged.get("children_map", {})),
            node_catalog=catalog,
        )
    finally:
        await release_progression_lock(lock_key)


@router.delete(
    "/{session_id}/nodes/{node_id}", response_model=GraphNodeMutationResponse
)
async def delete_graph_node(
    session_id: str,
    node_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    cascade: bool = Query(
        default=True, description="Delete child subtree recursively."
    ),
):
    """Delete a node (and optionally its descendants) from the graph."""
    db_session = await get_user_session(session_id, current_user.id, db)
    if db_session.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot modify graph while session is '{db_session.status}'.",
        )

    lock_ok, lock_key = await acquire_progression_lock(session_id)
    if not lock_ok:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Progression lock held."
        )
    try:
        snapshot = await get_current_state(session_id)
        if not snapshot or not snapshot.values:
            raise HTTPException(status_code=400, detail="Graph not initialized.")

        waiting_on = snapshot_next_nodes(snapshot)
        try:
            updates, removed_nodes = build_delete_node_updates(
                snapshot.values,
                node_id=node_id,
                cascade=cascade,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
            )

        await apply_state_updates(session_id, updates)
        merged = {**snapshot.values, **updates}
        options = derive_available_choices(
            merged,
            waiting_on=waiting_on,
            enable_backtracking=is_journey_v2_enabled(merged),
        )
        return GraphNodeMutationResponse(
            session_id=session_id,
            status="updated",
            message=f"Removed {len(removed_nodes)} node(s) from the graph.",
            current_node=str(merged.get("current_node", "") or ""),
            added_node=None,
            removed_nodes=removed_nodes,
            options=options,
            active_frontier=normalize_node_list(merged.get("active_frontier", [])),
            children_map=normalize_children_map(merged.get("children_map", {})),
            node_catalog=build_node_catalog_list(merged),
        )
    finally:
        await release_progression_lock(lock_key)


@router.post(
    "/{session_id}/nodes/{node_id}/expand", response_model=GraphNodeMutationResponse
)
async def expand_graph_node(
    session_id: str,
    node_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Expand a node by generating child nodes on demand."""
    db_session = await get_user_session(session_id, current_user.id, db)
    if db_session.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot modify graph while session is '{db_session.status}'.",
        )

    lock_ok, lock_key = await acquire_progression_lock(session_id)
    if not lock_ok:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Progression lock held."
        )
    try:
        snapshot = await get_current_state(session_id)
        if not snapshot or not snapshot.values:
            raise HTTPException(status_code=400, detail="Graph not initialized.")

        waiting_on = snapshot_next_nodes(snapshot)
        try:
            updates, added_node_ids = await build_expand_node_updates(
                snapshot.values,
                node_id=node_id,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
            )

        merged = {**snapshot.values, **(updates or {})}
        if updates:
            await apply_state_updates(session_id, updates)

        catalog = build_node_catalog_list(merged)
        added_set = set(added_node_ids)
        added_nodes = [m for m in catalog if m.node_id in added_set]
        options = derive_available_choices(
            merged,
            waiting_on=waiting_on,
            enable_backtracking=is_journey_v2_enabled(merged),
        )
        return GraphNodeMutationResponse(
            session_id=session_id,
            status="updated",
            message=f"Expanded '{node_id}'. Added {len(added_node_ids)} child node(s).",
            current_node=str(merged.get("current_node", "") or ""),
            added_node=added_nodes[0] if len(added_nodes) == 1 else None,
            added_nodes=added_nodes,
            removed_nodes=[],
            options=options,
            active_frontier=normalize_node_list(merged.get("active_frontier", [])),
            children_map=normalize_children_map(merged.get("children_map", {})),
            node_catalog=catalog,
        )
    finally:
        await release_progression_lock(lock_key)
