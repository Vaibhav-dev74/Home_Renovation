"""SQLite persistence and repository layer for AI Home Renovation Intelligence Platform.

Provides clean CRUD operations for projects, spatial models, structured design states,
version history snapshots, and conversational audit trails. Uses standard library sqlite3
with automatic table migrations and JSON serialization for complex nested models.
"""

import sqlite3
import json
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from models import (
    Project,
    DesignState,
    DesignVersion,
    SpatialModel,
    BOQSummary,
    BudgetOptimizationResult,
    TimelineSchedule,
    PermitCheckResult,
    CriticReport,
    RiskReport,
    DesignQualityScore,
)

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent / "renovation_platform.db"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Creates a thread-safe connection with dictionary row access."""
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    """Initializes schema and tables if they do not exist."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # 1. Projects Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                room_type TEXT NOT NULL,
                scope TEXT NOT NULL,
                square_footage INTEGER NOT NULL,
                location TEXT NOT NULL,
                currency TEXT NOT NULL,
                target_budget REAL NOT NULL,
                style TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                current_version INTEGER NOT NULL DEFAULT 1,
                original_image_path TEXT,
                latest_rendering_path TEXT,
                spatial_model_json TEXT,
                current_design_json TEXT,
                boq_json TEXT,
                budget_opt_json TEXT,
                timeline_json TEXT,
                permit_json TEXT,
                critic_json TEXT,
                risk_json TEXT,
                quality_json TEXT
            )
        """)

        # 2. Design Versions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS design_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                version_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                change_summary TEXT NOT NULL,
                modified_fields_json TEXT,
                design_state_json TEXT NOT NULL,
                rendering_artifact_filename TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (project_id)
            )
        """)

        # 3. Conversational Memory Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                intent TEXT,
                metadata_json TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (project_id)
            )
        """)

        conn.commit()
    logger.info("Database initialized successfully at %s", db_path)


# ============================================================================
# Project Repository Operations
# ============================================================================

def create_project(project: Project, db_path: Path = DB_PATH) -> Project:
    """Inserts a new project record."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO projects (
                project_id, name, room_type, scope, square_footage, location,
                currency, target_budget, style, created_at, updated_at,
                current_version, original_image_path, latest_rendering_path,
                spatial_model_json, current_design_json, boq_json, budget_opt_json,
                timeline_json, permit_json, critic_json, risk_json, quality_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project.project_id,
            project.name,
            project.room_type,
            project.scope,
            project.square_footage,
            project.location,
            project.currency.value,
            project.target_budget,
            project.style,
            project.created_at,
            project.updated_at,
            project.current_version,
            project.original_image_path,
            project.latest_rendering_path,
            project.spatial_model.model_dump_json() if project.spatial_model else None,
            project.current_design.model_dump_json() if project.current_design else None,
            project.boq.model_dump_json() if project.boq else None,
            project.budget_optimization.model_dump_json() if project.budget_optimization else None,
            project.timeline.model_dump_json() if project.timeline else None,
            project.permit_assessment.model_dump_json() if project.permit_assessment else None,
            project.critic_report.model_dump_json() if project.critic_report else None,
            project.risk_report.model_dump_json() if project.risk_report else None,
            project.quality_score.model_dump_json() if project.quality_score else None,
        ))
        conn.commit()

        # Save initial version 1 snapshot
        if project.current_design:
            save_design_version(
                DesignVersion(
                    version_id=project.current_version,
                    project_id=project.project_id,
                    change_summary="Initial design generated from baseline project requirements",
                    modified_fields=["*"],
                    design_state=project.current_design,
                    rendering_artifact_filename=project.latest_rendering_path,
                ),
                db_path=db_path,
            )

    return project


def get_project(project_id: str, db_path: Path = DB_PATH) -> Optional[Project]:
    """Retrieves a project by ID and parses nested domain models."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
        row = cursor.fetchone()
        if not row:
            return None

        data = dict(row)

        # Parse nested models from JSON safely
        spatial_model = SpatialModel.model_validate_json(data["spatial_model_json"]) if data["spatial_model_json"] else None
        current_design = DesignState.model_validate_json(data["current_design_json"]) if data["current_design_json"] else None
        boq = BOQSummary.model_validate_json(data["boq_json"]) if data["boq_json"] else None
        budget_opt = BudgetOptimizationResult.model_validate_json(data["budget_opt_json"]) if data["budget_opt_json"] else None
        timeline = TimelineSchedule.model_validate_json(data["timeline_json"]) if data["timeline_json"] else None
        permit = PermitCheckResult.model_validate_json(data["permit_json"]) if data["permit_json"] else None
        critic = CriticReport.model_validate_json(data["critic_json"]) if data["critic_json"] else None
        risk = RiskReport.model_validate_json(data["risk_json"]) if data["risk_json"] else None
        quality = DesignQualityScore.model_validate_json(data["quality_json"]) if data["quality_json"] else None

        return Project(
            project_id=data["project_id"],
            name=data["name"],
            room_type=data["room_type"],
            scope=data["scope"],
            square_footage=data["square_footage"],
            location=data["location"],
            currency=data["currency"],
            target_budget=data["target_budget"],
            style=data["style"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            current_version=data["current_version"],
            original_image_path=data["original_image_path"],
            latest_rendering_path=data["latest_rendering_path"],
            spatial_model=spatial_model,
            current_design=current_design,
            boq=boq,
            budget_optimization=budget_opt,
            timeline=timeline,
            permit_assessment=permit,
            critic_report=critic,
            risk_report=risk,
            quality_score=quality,
        )


def list_projects(db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """Returns summarized list of all projects ordered by last update."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT project_id, name, room_type, scope, square_footage,
                   location, currency, target_budget, style, current_version,
                   created_at, updated_at, latest_rendering_path
            FROM projects
            ORDER BY updated_at DESC
        """)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def update_project(project: Project, db_path: Path = DB_PATH) -> Project:
    """Updates an existing project record."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE projects SET
                name = ?, room_type = ?, scope = ?, square_footage = ?,
                location = ?, currency = ?, target_budget = ?, style = ?,
                updated_at = ?, current_version = ?, original_image_path = ?,
                latest_rendering_path = ?, spatial_model_json = ?,
                current_design_json = ?, boq_json = ?, budget_opt_json = ?,
                timeline_json = ?, permit_json = ?, critic_json = ?,
                risk_json = ?, quality_json = ?
            WHERE project_id = ?
        """, (
            project.name,
            project.room_type,
            project.scope,
            project.square_footage,
            project.location,
            project.currency.value,
            project.target_budget,
            project.style,
            project.updated_at,
            project.current_version,
            project.original_image_path,
            project.latest_rendering_path,
            project.spatial_model.model_dump_json() if project.spatial_model else None,
            project.current_design.model_dump_json() if project.current_design else None,
            project.boq.model_dump_json() if project.boq else None,
            project.budget_optimization.model_dump_json() if project.budget_optimization else None,
            project.timeline.model_dump_json() if project.timeline else None,
            project.permit_assessment.model_dump_json() if project.permit_assessment else None,
            project.critic_report.model_dump_json() if project.critic_report else None,
            project.risk_report.model_dump_json() if project.risk_report else None,
            project.quality_score.model_dump_json() if project.quality_score else None,
            project.project_id,
        ))
        conn.commit()
    return project


# ============================================================================
# Version History Operations
# ============================================================================

def save_design_version(version: DesignVersion, db_path: Path = DB_PATH) -> DesignVersion:
    """Persists a design version snapshot."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO design_versions (
                project_id, version_id, created_at, change_summary,
                modified_fields_json, design_state_json, rendering_artifact_filename
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            version.project_id,
            version.version_id,
            version.created_at,
            version.change_summary,
            json.dumps(version.modified_fields),
            version.design_state.model_dump_json(),
            version.rendering_artifact_filename,
        ))
        conn.commit()
    return version


def get_design_versions(project_id: str, db_path: Path = DB_PATH) -> List[DesignVersion]:
    """Retrieves all version snapshots for a given project."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM design_versions
            WHERE project_id = ?
            ORDER BY version_id ASC
        """, (project_id,))
        rows = cursor.fetchall()
        versions = []
        for r in rows:
            versions.append(
                DesignVersion(
                    version_id=r["version_id"],
                    project_id=r["project_id"],
                    created_at=r["created_at"],
                    change_summary=r["change_summary"],
                    modified_fields=json.loads(r["modified_fields_json"] or "[]"),
                    design_state=DesignState.model_validate_json(r["design_state_json"]),
                    rendering_artifact_filename=r["rendering_artifact_filename"],
                )
            )
        return versions


# ============================================================================
# Conversational Audit Trail
# ============================================================================

def add_chat_message(
    project_id: str,
    role: str,
    message: str,
    intent: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Records an entry in the conversational audit trail."""
    import datetime
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO project_chat (
                project_id, timestamp, role, message, intent, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
            role,
            message,
            intent,
            json.dumps(metadata or {}),
        ))
        conn.commit()


def get_chat_history(project_id: str, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """Retrieves chronological chat log for a project."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, role, message, intent, metadata_json
            FROM project_chat
            WHERE project_id = ?
            ORDER BY id ASC
        """, (project_id,))
        rows = cursor.fetchall()
        history = []
        for r in rows:
            entry = dict(r)
            entry["metadata"] = json.loads(entry.pop("metadata_json") or "{}")
            history.append(entry)
        return history


# Automatically ensure tables exist on module load
init_db()
