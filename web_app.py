"""AI Home Renovation Intelligence Platform - Enterprise FastAPI Web Gateway & SaaS Dashboard.

Provides high-performance REST APIs for multi-project management, spatial vision,
state-driven design editing, automated BOQ exports (CSV/HTML), regulatory RAG citations,
and an enterprise single-page SaaS dashboard.
"""

import os
import json
import logging
import uuid
from typing import Optional, List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response
import uvicorn

import tools
import agent
import database
from models import (
    Project,
    Currency,
    FactSource,
    DesignVersion,
    DesignState,
    RoomLayout3D,
    PlacedItem,
    Product,
    BOQItem,
)
import spatial_vision
import design_engine
import budget_optimizer
import permit_rag
import boq_engine
import timeline_engine
import critic_engine
import product_catalog

# Load environment
load_dotenv()
logger = logging.getLogger("renovation_platform")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="AI Home Renovation Intelligence Platform",
    description="Enterprise Multi-Agent Renovation Planning & Architectural Intelligence Platform",
    version="2.5.0",
)

# Ensure database tables exist
database.init_db()


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Verify backend and API readiness."""
    client = tools.get_genai_client()
    return {
        "status": "healthy",
        "platform": "AI Home Renovation Intelligence Platform v2.5",
        "api_key_configured": client is not None,
        "models_available": ["gemini-3.6-flash", "gemini-3.8-flash"],
        "database": "SQLite Initialized",
    }


@app.get("/api/projects")
async def get_projects():
    """Returns list of all saved renovation projects."""
    try:
        projects = database.list_projects()
        return {"success": True, "projects": projects}
    except Exception as e:
        logger.error("Error listing projects: %s", e)
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.post("/api/projects")
async def create_project_endpoint(request: Request):
    """Creates a new renovation project, runs full intelligence pipeline, and persists to DB."""
    try:
        data = await request.json()
        project_id = data.get("project_id") or f"proj-{uuid.uuid4().hex[:8]}"
        name = data.get("name") or f"{data.get('room_type', 'Kitchen').title()} Renovation"
        room_type = data.get("room_type", "kitchen")
        scope = data.get("scope", "moderate")
        sqft = int(data.get("square_footage", 180))
        location = data.get("location", "").strip() or "General Baseline"
        currency_str = data.get("currency", "INR").upper()
        currency = Currency.USD if currency_str == "USD" else Currency.INR
        target_budget = float(data.get("target_budget") or (800000.0 if currency == Currency.INR else 35000.0))
        style = data.get("style", "modern")
        user_notes = data.get("user_notes", "").strip()
        image_data = data.get("image_data")  # optional base64
        structural = bool(data.get("structural_changes", False))
        plumbing = bool(data.get("plumbing_changes", False))
        electrical = bool(data.get("electrical_changes", False))

        pipeline_trace = []

        # 1. Spatial Intelligence Pipeline
        pipeline_trace.append({"step": "Spatial Vision Analysis", "status": "processing"})
        spatial_model = await spatial_vision.analyze_room_spatial_image(
            image_base64=image_data,
            room_type=room_type,
            square_footage_hint=sqft,
            user_notes=user_notes,
        )
        pipeline_trace[-1]["status"] = "completed"

        # 2. Design State Engine
        pipeline_trace.append({"step": "Architectural Design Synthesis", "status": "processing"})
        current_design = design_engine.create_initial_design_state(
            room_type=room_type,
            style=style,
            target_budget=target_budget,
            currency=currency,
            user_notes=user_notes,
        )
        pipeline_trace[-1]["status"] = "completed"

        # 3. Budget Optimization Engine
        pipeline_trace.append({"step": "Budget & Value Engineering", "status": "processing"})
        budget_opt = budget_optimizer.optimize_renovation_budget(
            room_type=room_type,
            scope=scope,
            square_footage=sqft,
            target_budget=target_budget,
            currency=currency,
            current_design=current_design,
        )
        pipeline_trace[-1]["status"] = "completed"

        # 4. Automated Bill of Quantities (BOQ)
        pipeline_trace.append({"step": "Bill of Quantities (BOQ) Modeling", "status": "processing"})
        boq = boq_engine.generate_automated_boq(
            project_id=project_id,
            room_type=room_type,
            scope=scope,
            square_footage=sqft,
            spatial_model=spatial_model,
            design_state=current_design,
            currency=currency,
        )
        pipeline_trace[-1]["status"] = "completed"

        # 5. Regulatory RAG Permit Engine
        pipeline_trace.append({"step": "Building Code & Regulatory RAG", "status": "processing"})
        permit_assessment = permit_rag.query_regulatory_rag(
            room_type=room_type,
            scope=scope,
            structural_changes=structural,
            plumbing_changes=plumbing,
            electrical_changes=electrical,
            location=location,
        )
        pipeline_trace[-1]["status"] = "completed"

        # 6. Construction Timeline & DAG Scheduler
        pipeline_trace.append({"step": "Construction Timeline Scheduler", "status": "processing"})
        timeline = timeline_engine.build_construction_schedule(
            project_id=project_id,
            room_type=room_type,
            scope=scope,
            structural_changes=structural,
            plumbing_changes=plumbing,
            electrical_changes=electrical,
        )
        pipeline_trace[-1]["status"] = "completed"

        # 7. Multi-Agent Critic & Quality Scoring
        pipeline_trace.append({"step": "Multi-Agent Critic & Quality Validation", "status": "processing"})
        critic_report = critic_engine.evaluate_plan_critic(
            spatial_model=spatial_model,
            design_state=current_design,
            boq=boq,
            timeline=timeline,
            permit_assessment=permit_assessment,
            budget_opt=budget_opt,
            room_type=room_type,
            scope=scope,
            target_budget=target_budget,
        )
        risk_report = critic_engine.calculate_renovation_risk_report(
            room_type=room_type,
            scope=scope,
            structural_changes=structural,
            plumbing_changes=plumbing,
            electrical_changes=electrical,
            budget_overrun=budget_opt.overrun_amount,
            square_footage=sqft,
        )
        quality_score = critic_engine.calculate_design_quality_score(
            critic_report=critic_report,
            risk_report=risk_report,
            budget_opt=budget_opt,
            room_type=room_type,
            scope=scope,
        )
        pipeline_trace[-1]["status"] = "completed"

        # 8. Grounded Rendering Brief
        rendering_prompt = design_engine.build_grounded_rendering_prompt(
            design_state=current_design,
            spatial_model=spatial_model,
            room_type=room_type,
        )

        # 9. Spatial 3D Room Studio Setup
        import math
        room_w = 12.0
        room_l = 15.0
        ceiling_h = 9.0
        if spatial_model and spatial_model.dimensions:
            room_w = spatial_model.dimensions.width_ft or 12.0
            room_l = spatial_model.dimensions.length_ft or 15.0
            ceiling_h = spatial_model.dimensions.height_ft or 9.0
        elif sqft > 0:
            room_l = round(math.sqrt(sqft * 1.25), 1)
            room_w = round(sqft / room_l, 1)

        layout_3d = RoomLayout3D(
            project_id=project_id,
            room_width_ft=room_w,
            room_length_ft=room_l,
            ceiling_height_ft=ceiling_h,
            placed_items=[],
            total_products_cost=0.0,
            currency=currency,
            clearance_warnings=[],
        )

        # Build Project object
        project = Project(
            project_id=project_id,
            name=name,
            room_type=room_type,
            scope=scope,
            square_footage=sqft,
            location=location,
            currency=currency,
            target_budget=target_budget,
            style=style,
            current_version=1,
            original_image_path=image_data if image_data else None,
            latest_rendering_path=None,
            spatial_model=spatial_model,
            current_design=current_design,
            boq=boq,
            budget_optimization=budget_opt,
            timeline=timeline,
            permit_assessment=permit_assessment,
            critic_report=critic_report,
            risk_report=risk_report,
            quality_score=quality_score,
            layout_3d=layout_3d,
        )

        # Save to database
        database.create_project(project)

        return {
            "success": True,
            "project": project.model_dump(),
            "rendering_prompt": rendering_prompt,
            "pipeline_trace": pipeline_trace,
        }

    except Exception as e:
        logger.error("Error creating project: %s", e)
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.get("/api/projects/{project_id}")
async def get_project_endpoint(project_id: str):
    """Retrieves full project state by ID."""
    project = database.get_project(project_id)
    if not project:
        return JSONResponse(status_code=404, content={"success": False, "error": "Project not found"})
    return {"success": True, "project": project.model_dump()}


@app.post("/api/projects/{project_id}/camera-scan")
async def project_camera_scan_endpoint(project_id: str, request: Request):
    """Processes a live camera capture for an existing project.
    
    Extracts spatial dimensions, openings, and utility elements using multimodal
    spatial vision, updates project 3D room boundaries and rendering prompt,
    and returns the enriched project state.
    """
    try:
        project = database.get_project(project_id)
        if not project:
            return JSONResponse(status_code=404, content={"success": False, "error": "Project not found"})

        try:
            data = await request.json()
        except Exception:
            data = {}

        image_data = data.get("image_data")
        user_notes = (data.get("user_notes") or "").strip()

        if not image_data:
            return JSONResponse(status_code=400, content={"success": False, "error": "No camera image data received"})

        # Run spatial vision analysis
        spatial_model = await spatial_vision.analyze_room_spatial_image(
            image_base64=image_data,
            room_type=project.room_type,
            square_footage_hint=project.square_footage,
            user_notes=user_notes or "Live camera frame captured from user device",
        )

        project.original_image_path = image_data
        project.spatial_model = spatial_model

        # Update 3D room bounds if dimensions were inferred/detected
        layout = _ensure_project_layout(project)
        if spatial_model and spatial_model.dimensions:
            new_w = spatial_model.dimensions.width_ft
            new_l = spatial_model.dimensions.length_ft
            new_h = spatial_model.dimensions.height_ft
            if new_w and new_w > 0:
                layout.room_width_ft = float(new_w)
            if new_l and new_l > 0:
                layout.room_length_ft = float(new_l)
            if new_h and new_h > 0:
                layout.ceiling_height_ft = float(new_h)
            
            # Re-validate clearance warnings with new room dimensions
            _, warnings = product_catalog.validate_room_layout_clearance(layout)
            layout.clearance_warnings = warnings
            project.layout_3d = layout

        # Update grounded rendering prompt
        rendering_prompt = design_engine.build_grounded_rendering_prompt(
            design_state=project.current_design or design_engine.create_initial_design_state(
                room_type=project.room_type,
                style=project.style,
                target_budget=project.target_budget,
                currency=project.currency,
            ),
            spatial_model=spatial_model,
            room_type=project.room_type,
        )

        # Record assistant chat message
        summary_msg = (
            f"📸 Live camera scan processed! Inferred room dimensions: "
            f"{layout.room_width_ft}' W × {layout.room_length_ft}' L × {layout.ceiling_height_ft}' H. "
            f"Identified {len(spatial_model.openings)} opening(s) and {len(spatial_model.fixed_elements)} utility element(s). "
            f"3D Studio boundaries updated accordingly."
        )
        database.add_chat_message(
            project_id=project_id,
            role="assistant",
            message=summary_msg,
            intent="camera_spatial_scan",
        )

        database.update_project(project)

        return {
            "success": True,
            "project": project.model_dump(),
            "spatial_model": spatial_model.model_dump(),
            "rendering_prompt": rendering_prompt,
            "message": summary_msg,
        }

    except Exception as e:
        logger.error("Error processing camera scan for %s: %s", project_id, e)
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.post("/api/projects/{project_id}/location")
async def update_project_location_endpoint(project_id: str, request: Request):
    """Updates the project's location details according to the user.
    
    Re-evaluates local regulatory building codes (RAG), recalculates local contractor
    rates in the BOQ, adjusts currency if requested, re-optimizes budget, and syncs
    the 3D studio and marketplace availability.
    """
    try:
        project = database.get_project(project_id)
        if not project:
            return JSONResponse(status_code=404, content={"success": False, "error": "Project not found"})

        try:
            data = await request.json()
        except Exception:
            data = {}

        new_location = (data.get("location") or "").strip()
        requested_currency = data.get("currency")
        auto_adapt_currency = bool(data.get("auto_adapt_currency", True))

        if not new_location:
            return JSONResponse(status_code=400, content={"success": False, "error": "Location cannot be empty"})

        old_location = project.location
        old_currency = project.currency
        project.location = new_location

        # Determine target currency
        if requested_currency and requested_currency.upper() in ["INR", "USD"]:
            new_currency = Currency.USD if requested_currency.upper() == "USD" else Currency.INR
        elif auto_adapt_currency:
            loc_lower = new_location.lower()
            india_terms = [
                "india", "bengaluru", "bangalore", "mumbai", "delhi", "pune", "hyderabad",
                "chennai", "kolkata", "noida", "gurgaon", "gurugram", "ahmedabad", "jaipur"
            ]
            if any(term in loc_lower for term in india_terms):
                new_currency = Currency.INR
            elif any(term in loc_lower for term in ["us", "usa", "texas", "austin", "california", "ca", "ny", "york", "francisco", "seattle", "chicago", "miami"]):
                new_currency = Currency.USD
            else:
                new_currency = old_currency
        else:
            new_currency = old_currency

        # Handle currency conversion for target budget if currency changed
        if new_currency != old_currency:
            project.currency = new_currency
            if old_currency == Currency.USD and new_currency == Currency.INR:
                project.target_budget = round(project.target_budget * 86.0, -3)
            elif old_currency == Currency.INR and new_currency == Currency.USD:
                project.target_budget = round(project.target_budget / 86.0, -2)

        # 1. Re-evaluate Regulatory RAG for new municipal / national jurisdiction
        permit_assessment = permit_rag.query_regulatory_rag(
            room_type=project.room_type,
            scope=project.scope,
            structural_changes=bool(project.permit_assessment and any("structural" in (p or "").lower() for p in project.permit_assessment.permits_required)),
            plumbing_changes=bool(project.permit_assessment and any("plumbing" in (p or "").lower() for p in project.permit_assessment.trade_permits)),
            electrical_changes=True,
            location=project.location,
        )
        project.permit_assessment = permit_assessment

        # 2. Re-generate Automated BOQ for updated location & currency
        new_boq = boq_engine.generate_automated_boq(
            project_id=project.project_id,
            room_type=project.room_type,
            scope=project.scope,
            square_footage=project.square_footage,
            spatial_model=project.spatial_model,
            design_state=project.current_design,
            currency=project.currency,
        )
        project.boq = new_boq

        # 3. Synchronize 3D room layout currency and placed products
        if project.layout_3d:
            project.layout_3d.currency = project.currency
            _sync_layout_to_boq(project)

        # 4. Re-run Budget Optimization Engine
        project.budget_optimization = budget_optimizer.optimize_renovation_budget(
            room_type=project.room_type,
            scope=project.scope,
            square_footage=project.square_footage,
            target_budget=project.target_budget,
            currency=project.currency,
            current_design=project.current_design,
        )

        # 5. Persist updates
        database.update_project(project)

        sym = "₹" if project.currency == Currency.INR else "$"
        primary_code = permit_assessment.citations[0].code_standard if permit_assessment.citations else "Model Safety Codes"
        confirm_msg = (
            f"📍 Project location updated to **{project.location}** (from {old_location}). "
            f"Building safety codes re-evaluated: **{primary_code}** ({permit_assessment.jurisdiction_detected}). "
            f"Budget envelope set to **{sym}{project.target_budget:,.0f}**."
        )
        database.add_chat_message(
            project_id=project_id,
            role="assistant",
            message=confirm_msg,
            intent="location_update",
            metadata={"new_location": new_location, "jurisdiction": permit_assessment.jurisdiction_detected},
        )

        return {
            "success": True,
            "project": project.model_dump(),
            "message": confirm_msg,
            "jurisdiction": permit_assessment.jurisdiction_detected,
            "primary_code_standard": primary_code,
        }

    except Exception as e:
        logger.error("Error updating location for %s: %s", project_id, e)
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.post("/api/projects/{project_id}/edit")
async def edit_project_design(project_id: str, request: Request):
    """Applies non-destructive conversational delta-edit to design state and creates a new version."""
    try:
        project = database.get_project(project_id)
        if not project:
            return JSONResponse(status_code=404, content={"success": False, "error": "Project not found"})

        data = await request.json()
        instruction = data.get("instruction", "").strip()
        if not instruction:
            return JSONResponse(status_code=400, content={"success": False, "error": "Instruction is required"})

        # Apply edit
        current_state = project.current_design or design_engine.create_initial_design_state(
            room_type=project.room_type,
            style=project.style,
            target_budget=project.target_budget,
            currency=project.currency,
        )

        new_state, new_version, rationale = await design_engine.apply_conversational_design_edit(
            current_state=current_state,
            user_instruction=instruction,
            project_id=project_id,
            current_version=project.current_version,
        )

        # Update Project
        project.current_design = new_state
        project.current_version = new_version.version_id
        project.style = new_state.style
        project.target_budget = new_state.target_budget

        # Recompute BOQ & Budget with updated materials
        new_boq = boq_engine.generate_automated_boq(
            project_id=project_id,
            room_type=project.room_type,
            scope=project.scope,
            square_footage=project.square_footage,
            spatial_model=project.spatial_model,
            design_state=new_state,
            currency=project.currency,
        )
        new_budget_opt = budget_optimizer.optimize_renovation_budget(
            room_type=project.room_type,
            scope=project.scope,
            square_footage=project.square_footage,
            target_budget=project.target_budget,
            currency=project.currency,
            current_design=new_state,
        )

        project.boq = new_boq
        project.budget_optimization = new_budget_opt

        # Persist version and project updates
        database.save_design_version(new_version)
        database.update_project(project)
        database.add_chat_message(
            project_id=project_id,
            role="user",
            message=instruction,
            intent="design_edit",
            metadata={"modified_fields": new_version.modified_fields},
        )
        database.add_chat_message(
            project_id=project_id,
            role="assistant",
            message=rationale,
            intent="design_edit_response",
            metadata={"version_id": new_version.version_id},
        )

        return {
            "success": True,
            "version": new_version.model_dump(),
            "project": project.model_dump(),
            "designer_rationale": rationale,
        }

    except Exception as e:
        logger.error("Error editing design: %s", e)
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.get("/api/projects/{project_id}/versions")
async def get_project_versions(project_id: str):
    """Retrieves all historical design versions for comparison."""
    versions = database.get_design_versions(project_id)
    return {"success": True, "versions": [v.model_dump() for v in versions]}


@app.get("/api/projects/{project_id}/export-boq")
async def export_boq_endpoint(project_id: str, format: str = Query("csv", pattern="^(csv|html)$")):
    """Exports BOQ as downloadable CSV or printable HTML document."""
    project = database.get_project(project_id)
    if not project or not project.boq:
        return JSONResponse(status_code=404, content={"error": "Project or BOQ not found"})

    if format == "csv":
        csv_content = boq_engine.export_boq_to_csv(project.boq)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={project_id}_BOQ.csv"},
        )
    else:
        html_content = boq_engine.export_boq_to_html_printable(project.boq, project_name=project.name)
        return HTMLResponse(content=html_content)


@app.post("/api/projects/{project_id}/chat")
async def chat_project_endpoint(project_id: str, request: Request):
    """Context-aware conversational assistant with project memory."""
    try:
        project = database.get_project(project_id)
        if not project:
            return JSONResponse(status_code=404, content={"error": "Project not found"})

        data = await request.json()
        message = data.get("message", "").strip()
        if not message:
            return JSONResponse(status_code=400, content={"error": "Message is required"})

        client = tools.get_genai_client()

        # Build prompt grounded in project state
        sym = "₹" if project.currency == Currency.INR else "$"
        prompt = f"""You are the Principal AI Home Renovation Architect & Advisor for this project.

PROJECT DETAILS:
- Room: {project.room_type.title()} ({project.square_footage} sq ft)
- Location: {project.location}
- Scope: {project.scope.title()}
- Budget Envelope: {sym}{project.target_budget:,.0f}
- Current Design Style: {project.style}
- Wall Paint: {project.current_design.wall_paint if project.current_design else 'N/A'}
- Cabinetry: {project.current_design.cabinet_color if project.current_design else 'N/A'} ({project.current_design.cabinet_style if project.current_design else 'N/A'})
- Countertops: {project.current_design.countertop_material if project.current_design else 'N/A'}
- Estimated BOQ Total: {sym}{project.boq.grand_total:,.0f if project.boq else 0}
- Construction Timeline: {project.timeline.total_calendar_weeks if project.timeline else '6-8'} calendar weeks

USER MESSAGE:
"{message}"

GUIDELINES:
- Provide concise, practical, architecturally sound advice (3-5 sentences).
- If the user asks about costs, reference the BOQ and budget envelope.
- If the user asks about permits, reference local {project.location} building codes.
- If the user asks to modify design elements (e.g., colors, materials), acknowledge the change and inform them they can also click the quick-edit button.
"""

        reply = ""
        if client:
            for m in ["gemini-3.6-flash", "gemini-3.8-flash"]:
                try:
                    resp = client.models.generate_content(model=m, contents=prompt)
                    reply = resp.text
                    break
                except Exception as e:
                    logger.warning("Gemini chat attempt on %s failed: %s", m, e)

        if not reply:
            reply = (
                f"Regarding your {project.room_type} renovation: Your project envelope is currently {sym}{project.target_budget:,.0f} "
                f"with {project.current_design.cabinet_color if project.current_design else 'custom'} cabinetry and "
                f"{project.current_design.countertop_material if project.current_design else 'quartz'} countertops. "
                f"To adjust any finish or color, feel free to use our quick-edit tools or ask for specific material comparisons."
            )

        # Log conversation
        database.add_chat_message(project_id=project_id, role="user", message=message)
        database.add_chat_message(project_id=project_id, role="assistant", message=reply)

        return {"success": True, "reply": reply}

    except Exception as e:
        logger.error("Error in chat: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


# ============================================================================
# 3D / VR Spatial Room Planner & Real-Time Product Catalog Endpoints
# ============================================================================

def _ensure_project_layout(project: Project) -> RoomLayout3D:
    """Ensures a project has an initialized RoomLayout3D matching room boundaries."""
    if project.layout_3d:
        return project.layout_3d
    import math
    room_w = 12.0
    room_l = 15.0
    ceiling_h = 9.0
    if project.spatial_model and project.spatial_model.dimensions:
        room_w = project.spatial_model.dimensions.width_ft or 12.0
        room_l = project.spatial_model.dimensions.length_ft or 15.0
        ceiling_h = project.spatial_model.dimensions.height_ft or 9.0
    elif project.square_footage > 0:
        room_l = round(math.sqrt(project.square_footage * 1.25), 1)
        room_w = round(project.square_footage / room_l, 1)

    layout = RoomLayout3D(
        project_id=project.project_id,
        room_width_ft=room_w,
        room_length_ft=room_l,
        ceiling_height_ft=ceiling_h,
        placed_items=[],
        total_products_cost=0.0,
        currency=project.currency,
        clearance_warnings=[],
    )
    project.layout_3d = layout
    return layout


def _sync_layout_to_boq(project: Project) -> None:
    """Synchronizes placed 3D items directly into the project's Bill of Quantities (BOQ)."""
    if not project.layout_3d:
        return

    # Calculate total placed products cost
    total_prod = sum(it.price for it in project.layout_3d.placed_items)
    project.layout_3d.total_products_cost = round(total_prod, 2)

    if not project.boq:
        return

    # Filter out previous placed product line items
    clean_items = [it for it in project.boq.items if it.category != "Placed Products & Fixtures"]

    # Append fresh line items for each placed product
    for it in project.layout_3d.placed_items:
        clean_items.append(
            BOQItem(
                item_id=f"boq-{it.item_id}",
                category="Placed Products & Fixtures",
                item_name=it.name,
                description=f"{it.brand_or_retailer} [{it.width_ft}'W × {it.depth_ft}'D × {it.height_ft}'H] - {it.location_availability}",
                quantity=1.0,
                unit="units",
                material_unit_rate=it.price,
                labor_unit_rate=0.0,
                material_subtotal=it.price,
                labor_subtotal=0.0,
                total_amount=it.price,
                currency=project.currency,
                is_essential=True,
                assumption_notes=f"Physical size: {it.width_ft}x{it.depth_ft}x{it.height_ft} ft. Sourced from {it.brand_or_retailer}.",
            )
        )

    project.boq.items = clean_items

    # Recalculate totals
    mat_subtotal = sum(i.material_subtotal for i in clean_items)
    labor_subtotal = sum(i.labor_subtotal for i in clean_items)
    permits = project.boq.permits_and_fees
    raw_sub = mat_subtotal + labor_subtotal + permits

    contingency_rate = (project.boq.contingency_rate_pct or 10.0) / 100.0
    contingency = round(raw_sub * contingency_rate, 2)
    grand_total = round(raw_sub + contingency, 2)

    project.boq.subtotal_materials = round(mat_subtotal, 2)
    project.boq.subtotal_labor = round(labor_subtotal, 2)
    project.boq.contingency_amount = contingency
    project.boq.grand_total = grand_total

    # Update Budget Optimization result
    if project.budget_optimization:
        project.budget_optimization.optimized_total = grand_total
        project.budget_optimization.overrun_amount = max(0.0, round(grand_total - project.target_budget, 2))
        project.budget_optimization.is_over_budget = grand_total > project.target_budget


@app.get("/api/products")
async def get_products_endpoint(
    category: Optional[str] = None,
    location: Optional[str] = None,
    country: Optional[str] = None,
    search: Optional[str] = None,
    room_type: Optional[str] = None,
):
    """Catalog endpoint providing real products with authentic physical dimensions and pricing."""
    prods = product_catalog.get_all_products(
        category=category,
        room_type=room_type,
        location=location,
        country=country,
        search=search,
    )
    return {
        "success": True,
        "count": len(prods),
        "products": [p.model_dump() for p in prods],
        "available_categories": product_catalog.get_available_categories(),
        "available_locations": product_catalog.get_available_locations(),
    }


@app.get("/api/projects/{project_id}/layout3d")
async def get_project_layout3d_endpoint(project_id: str):
    """Retrieves 3D room layout and placed items with clearance analysis."""
    project = database.get_project(project_id)
    if not project:
        return JSONResponse(status_code=404, content={"error": "Project not found"})

    layout = _ensure_project_layout(project)
    _, warnings = product_catalog.validate_room_layout_clearance(layout)
    layout.clearance_warnings = warnings
    return {"success": True, "layout_3d": layout.model_dump()}


@app.post("/api/projects/{project_id}/layout3d")
async def update_project_layout3d_endpoint(project_id: str, request: Request):
    """Saves updated 3D layout (placed items, dimensions), runs clearance checks, and syncs BOQ."""
    try:
        project = database.get_project(project_id)
        if not project:
            return JSONResponse(status_code=404, content={"error": "Project not found"})

        data = await request.json()
        layout = _ensure_project_layout(project)

        if "room_width_ft" in data:
            layout.room_width_ft = float(data["room_width_ft"])
        if "room_length_ft" in data:
            layout.room_length_ft = float(data["room_length_ft"])
        if "ceiling_height_ft" in data:
            layout.ceiling_height_ft = float(data["ceiling_height_ft"])

        if "placed_items" in data:
            items = []
            for raw_it in data["placed_items"]:
                if isinstance(raw_it, dict):
                    items.append(PlacedItem.model_validate(raw_it))
            layout.placed_items = items

        is_valid, warnings = product_catalog.validate_room_layout_clearance(layout)
        layout.clearance_warnings = warnings
        project.layout_3d = layout

        _sync_layout_to_boq(project)
        database.update_project(project)

        return {
            "success": True,
            "layout_3d": layout.model_dump(),
            "boq": project.boq.model_dump() if project.boq else None,
            "budget_optimization": project.budget_optimization.model_dump() if project.budget_optimization else None,
            "is_valid": is_valid,
        }
    except Exception as e:
        logger.error("Error updating 3D layout: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/projects/{project_id}/layout3d/place")
async def place_product_in_3d_endpoint(project_id: str, request: Request):
    """Instantiates and places a catalog product into the 3D room with physical dimensions."""
    try:
        project = database.get_project(project_id)
        if not project:
            return JSONResponse(status_code=404, content={"error": "Project not found"})

        data = await request.json()
        product_id = data.get("product_id")
        if not product_id:
            return JSONResponse(status_code=400, content={"error": "product_id is required"})

        prod = product_catalog.get_product_by_id(product_id)
        if not prod:
            return JSONResponse(status_code=404, content={"error": f"Product '{product_id}' not found"})

        x = float(data.get("x", 0.0))
        z = float(data.get("z", 0.0))
        rotation_deg = float(data.get("rotation_deg", 0.0))

        placed_item = product_catalog.create_placed_item_from_product(
            product=prod,
            x=x,
            z=z,
            rotation_deg=rotation_deg,
        )

        layout = _ensure_project_layout(project)
        layout.placed_items.append(placed_item)

        is_valid, warnings = product_catalog.validate_room_layout_clearance(layout)
        layout.clearance_warnings = warnings
        project.layout_3d = layout

        _sync_layout_to_boq(project)
        database.update_project(project)

        return {
            "success": True,
            "placed_item": placed_item.model_dump(),
            "layout_3d": layout.model_dump(),
            "boq": project.boq.model_dump() if project.boq else None,
            "budget_optimization": project.budget_optimization.model_dump() if project.budget_optimization else None,
        }
    except Exception as e:
        logger.error("Error placing product in 3D: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/projects/{project_id}/layout3d/items/{item_id}")
async def remove_placed_item_endpoint(project_id: str, item_id: str):
    """Removes a placed item from the 3D room, recalculates clearance and BOQ cart total."""
    try:
        project = database.get_project(project_id)
        if not project:
            return JSONResponse(status_code=404, content={"error": "Project not found"})

        layout = _ensure_project_layout(project)
        layout.placed_items = [it for it in layout.placed_items if it.item_id != item_id]

        is_valid, warnings = product_catalog.validate_room_layout_clearance(layout)
        layout.clearance_warnings = warnings
        project.layout_3d = layout

        _sync_layout_to_boq(project)
        database.update_project(project)

        return {
            "success": True,
            "layout_3d": layout.model_dump(),
            "boq": project.boq.model_dump() if project.boq else None,
            "budget_optimization": project.budget_optimization.model_dump() if project.budget_optimization else None,
        }
    except Exception as e:
        logger.error("Error removing placed item: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


# ============================================================================
# Backwards-Compatible Legacy Endpoint (/api/plan)
# ============================================================================

@app.post("/api/plan")
async def generate_legacy_plan(request: Request):
    """Backwards-compatible endpoint mapping legacy form input to V2 project engine."""
    data = await request.json()
    resp = await create_project_endpoint(request)
    if isinstance(resp, JSONResponse):
        return resp
    project_dict = resp.get("project", {})

    # Map legacy KPI format for existing scripts
    curr = project_dict.get("currency", "INR")
    sym = "₹" if curr == "INR" else "$"
    boq = project_dict.get("boq", {})
    grand_tot = boq.get("grand_total", 500000.0)

    legacy_kpis = {
        "cost_low": f"{sym}{int(grand_tot * 0.9):,}",
        "cost_high": f"{sym}{int(grand_tot * 1.15):,}",
        "cost_mid": f"{sym}{int(grand_tot):,}",
        "materials_pct": "42%",
        "materials_val": f"{sym}{int(grand_tot * 0.42):,}",
        "labor_pct": "45%",
        "labor_val": f"{sym}{int(grand_tot * 0.45):,}",
        "permits_pct": "3%",
        "permits_val": f"{sym}{int(grand_tot * 0.03):,}",
        "contingency_pct": "10%",
        "contingency_val": f"{sym}{int(grand_tot * 0.10):,}",
        "duration": f"{project_dict.get('timeline', {}).get('total_calendar_weeks', 6)} weeks",
        "permits_needed": "Required (Trade/Building)",
        "roi_potential": "70% - 85%",
    }

    return {
        "success": True,
        "room_type": project_dict.get("room_type"),
        "scope": project_dict.get("scope"),
        "square_footage": project_dict.get("square_footage"),
        "location": project_dict.get("location"),
        "style": project_dict.get("style"),
        "kpis": legacy_kpis,
        "project": project_dict,
        "rendering_prompt": resp.get("rendering_prompt"),
        "rendering_status": "Brief Grounded with Layout Directives",
    }


# ============================================================================
# Frontend UI (Enterprise SaaS Single-Page Dashboard)
# ============================================================================

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Renders the streamlined 3D Spatial Room Studio, Live Marketplace & Renovation Intelligence Dashboard."""
    template_path = TEMPLATE_DIR / "dashboard.html"
    if template_path.exists():
        return HTMLResponse(content=template_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Dashboard template not found.</h1>", status_code=500)


def _unused_legacy_template():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Home Renovation Intelligence Platform</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090d16;
      --sidebar: #0f172a;
      --card-bg: rgba(30, 41, 59, 0.7);
      --card-border: rgba(255, 255, 255, 0.08);
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --accent: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --surface: #1e293b;
      --surface-light: #334155;
      --radius: 12px;
      --radius-sm: 8px;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Plus Jakarta Sans', sans-serif;
      background-color: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
      background-image: 
        radial-gradient(circle at 10% 10%, rgba(59, 130, 246, 0.08) 0%, transparent 40%),
        radial-gradient(circle at 90% 90%, rgba(16, 185, 129, 0.06) 0%, transparent 45%);
      background-attachment: fixed;
    }

    /* Top Navigation Header */
    header {
      backdrop-filter: blur(16px);
      background: rgba(15, 23, 42, 0.85);
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 50;
      padding: 0.85rem 1.75rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-weight: 700;
      font-size: 1.15rem;
      letter-spacing: -0.02em;
    }
    .brand-badge {
      font-size: 0.7rem;
      font-weight: 600;
      background: rgba(59, 130, 246, 0.15);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.3);
      padding: 2px 8px;
      border-radius: 9999px;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .btn {
      font-family: inherit;
      font-size: 0.85rem;
      font-weight: 600;
      padding: 0.55rem 1.1rem;
      border-radius: var(--radius-sm);
      border: none;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      transition: all 0.2s ease;
      text-decoration: none;
    }
    .btn-primary {
      background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
    }
    .btn-primary:hover { opacity: 0.92; transform: translateY(-1px); }
    .btn-secondary {
      background: var(--surface);
      color: var(--text);
      border: 1px solid var(--card-border);
    }
    .btn-secondary:hover { background: var(--surface-light); }

    /* Layout Frame */
    .app-frame {
      display: flex;
      flex: 1;
      height: calc(100vh - 61px);
    }

    /* Sidebar Navigation */
    .sidebar {
      width: 250px;
      background: var(--sidebar);
      border-right: 1px solid var(--card-border);
      display: flex;
      flex-direction: column;
      padding: 1rem 0.75rem;
      overflow-y: auto;
    }
    .nav-label {
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin: 1rem 0.5rem 0.4rem 0.5rem;
      font-weight: 700;
    }
    .nav-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.65rem 0.85rem;
      border-radius: var(--radius-sm);
      color: var(--text-muted);
      font-size: 0.88rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s ease;
      margin-bottom: 2px;
    }
    .nav-item:hover { color: var(--text); background: rgba(255, 255, 255, 0.04); }
    .nav-item.active {
      color: #ffffff;
      background: rgba(59, 130, 246, 0.15);
      border-left: 3px solid var(--primary);
      font-weight: 600;
    }

    /* Main Content Area */
    .main-viewport {
      flex: 1;
      padding: 1.5rem 2rem;
      overflow-y: auto;
    }

    /* KPI Summary Row */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    .kpi-card {
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 1.1rem 1.25rem;
      position: relative;
    }
    .kpi-label { font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; }
    .kpi-value { font-size: 1.65rem; font-weight: 800; margin: 0.3rem 0; letter-spacing: -0.02em; }
    .kpi-sub { font-size: 0.75rem; color: var(--text-muted); }

    /* Content Cards */
    .dashboard-card {
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }
    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1.25rem;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 0.85rem;
    }
    .card-title {
      font-size: 1.1rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    /* Comparison Before / After */
    .comparison-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
    }
    .comparison-box {
      border: 1px dashed var(--card-border);
      border-radius: var(--radius);
      padding: 1rem;
      text-align: center;
      min-height: 280px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, 0.2);
    }
    .comparison-img {
      max-width: 100%;
      max-height: 320px;
      border-radius: var(--radius-sm);
      object-fit: cover;
    }

    /* Tables */
    .data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.88rem;
    }
    .data-table th {
      text-align: left;
      padding: 0.75rem 1rem;
      background: rgba(15, 23, 42, 0.6);
      color: var(--text-muted);
      font-weight: 600;
      border-bottom: 1px solid var(--card-border);
    }
    .data-table td {
      padding: 0.75rem 1rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      vertical-align: top;
    }

    /* Tags & Badges */
    .badge {
      display: inline-block;
      font-size: 0.72rem;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 9999px;
      background: var(--surface-light);
      color: var(--text);
    }
    .badge-observed { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-inferred { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-critical { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }

    /* Modals & Inputs */
    .modal-overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(8px);
      z-index: 100;
      align-items: center;
      justify-content: center;
    }
    .modal-card {
      background: var(--sidebar);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      width: 90%;
      max-width: 600px;
      padding: 2rem;
      max-height: 90vh;
      overflow-y: auto;
    }
    .form-group { margin-bottom: 1rem; }
    .form-group label {
      display: block;
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 0.35rem;
    }
    .form-control {
      width: 100%;
      padding: 0.65rem 0.85rem;
      border-radius: var(--radius-sm);
      background: var(--surface);
      border: 1px solid var(--card-border);
      color: var(--text);
      font-family: inherit;
      font-size: 0.9rem;
    }
    .form-control:focus { outline: none; border-color: var(--primary); }

    /* Chat Drawer */
    .chat-panel {
      display: flex;
      flex-direction: column;
      height: 480px;
    }
    .chat-log {
      flex: 1;
      overflow-y: auto;
      padding: 1rem;
      background: rgba(0, 0, 0, 0.2);
      border-radius: var(--radius-sm);
      margin-bottom: 1rem;
    }
    .chat-msg {
      margin-bottom: 0.85rem;
      max-width: 85%;
      padding: 0.75rem 1rem;
      border-radius: var(--radius-sm);
      font-size: 0.88rem;
      line-height: 1.5;
    }
    .chat-msg.user {
      margin-left: auto;
      background: var(--primary);
      color: #ffffff;
    }
    .chat-msg.assistant {
      margin-right: auto;
      background: var(--surface);
      border: 1px solid var(--card-border);
    }

    /* Tab switcher */
    .tab-content { display: none; }
    .tab-content.active { display: block; }
  </style>
</head>
<body>

  <!-- Top Header -->
  <header>
    <div class="brand">
      <span>🏚️ RenovAI Intelligence</span>
      <span class="brand-badge">Enterprise V2.5</span>
    </div>
    <div class="header-actions">
      <select id="project-selector" class="form-control" style="width: 220px;" onchange="loadSelectedProject(this.value)">
        <option value="">Select Project...</option>
      </select>
      <button class="btn btn-primary" onclick="openNewProjectModal()">✨ New Renovation</button>
    </div>
  </header>

  <!-- App Layout Frame -->
  <div class="app-frame">
    <!-- Sidebar Navigation -->
    <nav class="sidebar">
      <div class="nav-label">Core Modules</div>
      <div class="nav-item active" onclick="switchTab('overview', this)">📊 Project Overview</div>
      <div class="nav-item" onclick="switchTab('before-after', this)">🖼️ Before / After Studio</div>
      <div class="nav-item" onclick="switchTab('spatial', this)">📐 Spatial Intelligence</div>
      <div class="nav-item" onclick="switchTab('design-state', this)">🎨 Design Specifications</div>

      <div class="nav-label">Cost & Compliance</div>
      <div class="nav-item" onclick="switchTab('boq', this)">💰 Bill of Quantities (BOQ)</div>
      <div class="nav-item" onclick="switchTab('budget-opt', this)">⚖️ Value Engineering</div>
      <div class="nav-item" onclick="switchTab('timeline', this)">⏱️ Timeline & Tasks DAG</div>
      <div class="nav-item" onclick="switchTab('permits', this)">📋 Regulatory RAG (Codes)</div>

      <div class="nav-label">Auditing & Copilot</div>
      <div class="nav-item" onclick="switchTab('critic-risks', this)">🛡️ Critic & Risk Matrix</div>
      <div class="nav-item" onclick="switchTab('copilot', this)">🤖 AI Design Copilot</div>
    </nav>

    <!-- Main Viewport -->
    <main class="main-viewport">
      
      <!-- Top KPIs -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Target Envelope</div>
          <div class="kpi-value" id="kpi-budget">₹8,00,000</div>
          <div class="kpi-sub" id="kpi-currency">INR Baseline</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Estimated Calendar Time</div>
          <div class="kpi-value" id="kpi-duration">7 Weeks</div>
          <div class="kpi-sub">Critical Path Resolved</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Design Quality Score</div>
          <div class="kpi-value" id="kpi-score" style="color: #34d399;">92 / 100</div>
          <div class="kpi-sub">Verified Architectural Flow</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Renovation Risk Index</div>
          <div class="kpi-value" id="kpi-risk" style="color: #60a5fa;">LOW (27)</div>
          <div class="kpi-sub">Structural Load Undisturbed</div>
        </div>
      </div>

      <!-- 1. Overview Tab -->
      <div id="tab-overview" class="tab-content active">
        <div class="dashboard-card">
          <div class="card-header">
            <div class="card-title">📋 Executive Project Charter</div>
            <span class="badge" id="overview-version-badge">Version 1.0</span>
          </div>
          <p id="overview-summary" style="line-height: 1.6; color: var(--text-muted); margin-bottom: 1.25rem;">
            Loading project details...
          </p>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
            <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px;">
              <div style="font-size: 0.75rem; color: var(--text-muted);">ROOM & FOOTPRINT</div>
              <div style="font-weight: 700; font-size: 1rem; margin-top: 4px;" id="ov-room-sqft">Kitchen (180 sq ft)</div>
            </div>
            <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px;">
              <div style="font-size: 0.75rem; color: var(--text-muted);">JURISDICTION / AHJ</div>
              <div style="font-weight: 700; font-size: 1rem; margin-top: 4px;" id="ov-location">Austin, TX (IRC/NEC)</div>
            </div>
            <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px;">
              <div style="font-size: 0.75rem; color: var(--text-muted);">PRIMARY STYLE PROFILE</div>
              <div style="font-weight: 700; font-size: 1rem; margin-top: 4px;" id="ov-style">Modern Farmhouse</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 2. Before / After Tab -->
      <div id="tab-before-after" class="tab-content">
        <div class="dashboard-card">
          <div class="card-header">
            <div class="card-title">🖼️ Before & After Visualizer</div>
            <span class="badge">Preserved Openings & Utilities</span>
          </div>
          <div class="comparison-grid">
            <div class="comparison-box">
              <h4 style="margin-bottom: 0.75rem; color: var(--text-muted);">EXISTING ROOM SPACE (BEFORE)</h4>
              <img id="img-before" class="comparison-img" src="" alt="Upload a photo to inspect space" style="display:none;">
              <div id="img-before-placeholder" style="color: var(--text-muted); font-size: 0.85rem;">
                No room photo uploaded yet.<br>Click "✨ New Renovation" to upload your room picture.
              </div>
            </div>
            <div class="comparison-box">
              <h4 style="margin-bottom: 0.75rem; color: #60a5fa;">GROUNDED ARCHITECTURAL RENDERING (AFTER)</h4>
              <div style="padding: 1.5rem; text-align: left; background: rgba(15,23,42,0.6); border-radius: 8px; width: 100%;">
                <div style="font-size: 0.75rem; font-weight: 700; color: #60a5fa; margin-bottom: 0.5rem;">SLC ARCHITECTURAL PHOTOGRAPHY BRIEF:</div>
                <div id="render-brief-text" style="font-family:'JetBrains Mono', monospace; font-size: 0.8rem; line-height: 1.5; color: #e2e8f0; max-height: 220px; overflow-y: auto;">
                  Brief will appear here after project generation...
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 3. Spatial Intelligence Tab -->
      <div id="tab-spatial" class="tab-content">
        <div class="dashboard-card">
          <div class="card-header">
            <div class="card-title">📐 Spatial Model & Constraints</div>
            <span class="badge" id="spatial-confidence-badge">Confidence: 85%</span>
          </div>
          <h4 style="margin-bottom: 0.75rem;">Verified Openings (Windows, Doors & Thresholds)</h4>
          <table class="data-table" id="table-openings">
            <thead>
              <tr><th>Type</th><th>Wall</th><th>Position</th><th>Preserve Rule</th><th>Notes</th></tr>
            </thead>
            <tbody></tbody>
          </table>
          <h4 style="margin-top: 1.5rem; margin-bottom: 0.75rem;">Fixed Utility Points</h4>
          <table class="data-table" id="table-fixed-elements">
            <thead>
              <tr><th>Element</th><th>Location</th><th>Source</th><th>Relocation Risk</th></tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>

      <!-- 4. Design State Tab -->
      <div id="tab-design-state" class="tab-content">
        <div class="dashboard-card">
          <div class="card-header">
            <div class="card-title">🎨 Granular Design Specifications</div>
            <span class="badge">Non-Destructive State</span>
          </div>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem;" id="design-cards-grid">
            <!-- Populated via JS -->
          </div>
        </div>
      </div>

      <!-- 5. BOQ Tab -->
      <div id="tab-boq" class="tab-content">
        <div class="dashboard-card">
          <div class="card-header">
            <div class="card-title">💰 Itemized Bill of Quantities (BOQ)</div>
            <div style="display: flex; gap: 0.5rem;">
              <button class="btn btn-secondary" onclick="exportBOQ('csv')">📥 Export CSV (Excel)</button>
              <button class="btn btn-secondary" onclick="exportBOQ('html')">🖨️ Printable PDF</button>
            </div>
          </div>
          <table class="data-table" id="table-boq">
            <thead>
              <tr>
                <th>Item ID</th>
                <th>Category</th>
                <th>Description</th>
                <th>Quantity</th>
                <th>Material Rate</th>
                <th>Labor Rate</th>
                <th>Total Subtotal</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>

      <!-- 6. Value Engineering Tab -->
      <div id="tab-budget-opt" class="tab-content">
        <div class="dashboard-card">
          <div class="card-header">
            <div class="card-title">⚖️ Value Engineering & Budget Optimization</div>
            <span class="badge" id="badge-opt-status">Optimized</span>
          </div>
          <p id="opt-summary-text" style="color: var(--text-muted); line-height: 1.6; margin-bottom: 1.25rem;"></p>
          <h4>Recommended Material Trade-offs</h4>
          <table class="data-table" id="table-tradeoffs">
            <thead>
              <tr>
                <th>Category</th>
                <th>Original Specification</th>
                <th>Value Engineered Alternative</th>
                <th>Potential Savings</th>
                <th>Architectural Compromise</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>

      <!-- 7. Timeline Tab -->
      <div id="tab-timeline" class="tab-content">
        <div class="dashboard-card">
          <div class="card-header">
            <div class="card-title">⏱️ Phased Schedule & Dependency DAG</div>
            <span class="badge" id="badge-timeline-weeks">Total: 7 Weeks</span>
          </div>
          <table class="data-table" id="table-timeline">
            <thead>
              <tr>
                <th>Task ID</th>
                <th>Phase</th>
                <th>Task Description</th>
                <th>Days</th>
                <th>Prerequisites</th>
                <th>Trade</th>
                <th>Inspection</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>

      <!-- 8. Permits Tab -->
      <div id="tab-permits" class="tab-content">
        <div class="dashboard-card">
          <div class="card-header">
            <div class="card-title">📋 Grounded Regulatory RAG & Building Codes</div>
            <span class="badge" id="badge-jurisdiction">Jurisdiction: IRC / NEC</span>
          </div>
          <div id="permits-guidance" style="background: rgba(59,130,246,0.1); border-left: 3px solid var(--primary); padding: 1rem; border-radius: 6px; margin-bottom: 1.25rem; font-size: 0.88rem; line-height: 1.5;"></div>
          <h4>Verified Regulatory Citations (IRC, NEC, NBC)</h4>
          <table class="data-table" id="table-citations">
            <thead>
              <tr>
                <th>Standard</th>
                <th>Section</th>
                <th>Title & Requirement</th>
                <th>Source Document</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>

      <!-- 9. Critic & Risk Tab -->
      <div id="tab-critic-risks" class="tab-content">
        <div class="dashboard-card">
          <div class="card-header">
            <div class="card-title">🛡️ Critic Findings & Risk Matrix</div>
            <span class="badge" id="badge-critic-status">VALIDATED</span>
          </div>
          <h4 style="margin-bottom: 0.75rem;">Architectural Critic Findings</h4>
          <div id="critic-findings-list" style="margin-bottom: 1.5rem;"></div>
          <h4 style="margin-bottom: 0.75rem;">Domain Risk Assessment</h4>
          <table class="data-table" id="table-risks">
            <thead>
              <tr>
                <th>Domain</th>
                <th>Risk Level</th>
                <th>Reason & Sourcing Evidence</th>
                <th>Recommended Action</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>

      <!-- 10. AI Copilot Tab -->
      <div id="tab-copilot" class="tab-content">
        <div class="dashboard-card chat-panel">
          <div class="card-header">
            <div class="card-title">🤖 AI Design Copilot & Conversational Editor</div>
            <span class="badge">Non-Destructive Delta-Updates</span>
          </div>
          <div class="chat-log" id="chat-box">
            <div class="chat-msg assistant">
              Hello! I'm your AI Interior Architect. You can ask me renovation questions or instruct edits like <strong>"Make the cabinets sage green"</strong> or <strong>"Change the countertop to white quartz"</strong>, and I will update your design state non-destructively.
            </div>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <input type="text" id="chat-input" class="form-control" placeholder="Ask a question or enter a design edit (e.g. 'Switch cabinets to dark oak')..." onkeydown="if(event.key==='Enter') sendChatMessage()">
            <button class="btn btn-primary" onclick="sendChatMessage()">Send</button>
          </div>
        </div>
      </div>

    </main>
  </div>

  <!-- New Project Modal -->
  <div id="new-project-modal" class="modal-overlay">
    <div class="modal-card">
      <h3 style="margin-bottom: 1.25rem;">✨ Start New Renovation Project</h3>
      <div class="form-group">
        <label>Project Name</label>
        <input type="text" id="new-name" class="form-control" value="Chef's Kitchen Renovation">
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
        <div class="form-group">
          <label>Room Type</label>
          <select id="new-room" class="form-control">
            <option value="kitchen">Kitchen</option>
            <option value="bathroom">Bathroom</option>
            <option value="master_bedroom">Master Bedroom</option>
            <option value="living_room">Living Room</option>
            <option value="basement">Basement</option>
          </select>
        </div>
        <div class="form-group">
          <label>Renovation Scope</label>
          <select id="new-scope" class="form-control">
            <option value="cosmetic">Cosmetic (Surface)</option>
            <option value="moderate" selected>Moderate (Fixtures & Cabinets)</option>
            <option value="full">Full (Down to Studs)</option>
            <option value="luxury">Luxury Bespoke</option>
          </select>
        </div>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
        <div class="form-group">
          <label>Square Footage (sq ft)</label>
          <input type="number" id="new-sqft" class="form-control" value="180">
        </div>
        <div class="form-group">
          <label>Location / City</label>
          <input type="text" id="new-location" class="form-control" value="Austin, TX">
        </div>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
        <div class="form-group">
          <label>Target Budget</label>
          <input type="number" id="new-budget" class="form-control" value="800000">
        </div>
        <div class="form-group">
          <label>Currency</label>
          <select id="new-currency" class="form-control">
            <option value="INR" selected>INR (₹)</option>
            <option value="USD">USD ($)</option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label>Aesthetic Style</label>
        <select id="new-style" class="form-control">
          <option value="modern" selected>Modern Clean</option>
          <option value="contemporary_indian">Contemporary Indian</option>
          <option value="minimalist">Minimalist</option>
          <option value="farmhouse">Modern Farmhouse</option>
        </select>
      </div>
      <div class="form-group">
        <label>Room Photo (Optional for Vision Analysis)</label>
        <input type="file" id="new-image" class="form-control" accept="image/*">
      </div>
      <div style="display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem;">
        <button class="btn btn-secondary" onclick="closeNewProjectModal()">Cancel</button>
        <button class="btn btn-primary" id="btn-submit-project" onclick="submitNewProject()">Launch Plan</button>
      </div>
    </div>
  </div>

  <script>
    let currentProject = null;

    // Tab Switching
    function switchTab(tabId, el) {
      document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
      el.classList.add('active');
      document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
      document.getElementById('tab-' + tabId).classList.add('active');
    }

    // Modal Control
    function openNewProjectModal() { document.getElementById('new-project-modal').style.display = 'flex'; }
    function closeNewProjectModal() { document.getElementById('new-project-modal').style.display = 'none'; }

    // Initial Load
    window.addEventListener('DOMContentLoaded', async () => {
      await loadProjectList();
    });

    async function loadProjectList() {
      try {
        const res = await fetch('/api/projects');
        const data = await res.json();
        const sel = document.getElementById('project-selector');
        sel.innerHTML = '<option value="">Select Project...</option>';
        if (data.projects && data.projects.length > 0) {
          data.projects.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.project_id;
            opt.innerText = `${p.name} (${p.room_type}) [v${p.current_version}]`;
            sel.appendChild(opt);
          });
          // Load the latest project automatically
          loadSelectedProject(data.projects[0].project_id);
          sel.value = data.projects[0].project_id;
        } else {
          // Trigger default baseline creation
          console.log("No projects yet.");
        }
      } catch (err) {
        console.error("Failed to load projects", err);
      }
    }

    async function loadSelectedProject(projectId) {
      if (!projectId) return;
      try {
        const res = await fetch(`/api/projects/${projectId}`);
        const data = await res.json();
        if (data.success && data.project) {
          currentProject = data.project;
          renderProjectUI(currentProject);
        }
      } catch (err) {
        console.error("Error loading project", err);
      }
    }

    function renderProjectUI(p) {
      const sym = p.currency === "INR" ? "₹" : "$";

      // 1. KPIs
      document.getElementById('kpi-budget').innerText = `${sym}${p.target_budget.toLocaleString()}`;
      document.getElementById('kpi-currency').innerText = `${p.currency} Baseline`;
      if (p.timeline) {
        document.getElementById('kpi-duration').innerText = `${p.timeline.total_calendar_weeks} Weeks`;
      }
      if (p.quality_score) {
        document.getElementById('kpi-score').innerText = `${p.quality_score.overall_score} / 100`;
      }
      if (p.risk_report) {
        document.getElementById('kpi-risk').innerText = `${p.risk_report.overall_rating} (${p.risk_report.overall_score})`;
      }

      // 2. Overview
      document.getElementById('overview-version-badge').innerText = `Version ${p.current_version}.0`;
      document.getElementById('ov-room-sqft').innerText = `${p.room_type.replace('_',' ').toUpperCase()} (${p.square_footage} sq ft)`;
      document.getElementById('ov-location').innerText = p.location;
      document.getElementById('ov-style').innerText = p.style.replace('_',' ').toUpperCase();
      document.getElementById('overview-summary').innerText = 
        `Renovation plan formulated for a ${p.scope} ${p.room_type} in ${p.location}. Includes itemized BOQ, task DAG schedule, and regulatory compliance citations.`;

      // 3. Before / After
      if (p.original_image_path) {
        const img = document.getElementById('img-before');
        img.src = p.original_image_path;
        img.style.display = 'block';
        document.getElementById('img-before-placeholder').style.display = 'none';
      }
      if (p.current_design) {
        document.getElementById('render-brief-text').innerText = 
          `SUBJECT: ${p.style.toUpperCase()} ${p.room_type.toUpperCase()}\\n` +
          `Cabinetry: ${p.current_design.cabinet_color} (${p.current_design.cabinet_style})\\n` +
          `Countertops: ${p.current_design.countertop_material} (${p.current_design.countertop_finish})\\n` +
          `Flooring: ${p.current_design.flooring_type} (${p.current_design.flooring_finish})\\n` +
          `Wall Paint: ${p.current_design.wall_paint}\\n` +
          `Lighting: ${p.current_design.lighting_types.join(', ')}`;
      }

      // 4. Spatial Openings
      if (p.spatial_model) {
        const tbodyOp = document.querySelector('#table-openings tbody');
        tbodyOp.innerHTML = '';
        (p.spatial_model.openings || []).forEach(op => {
          tbodyOp.innerHTML += `<tr>
            <td><strong>${op.opening_type}</strong></td>
            <td>${op.wall}</td>
            <td>${op.position}</td>
            <td><span class="badge ${op.must_preserve ? 'badge-observed':'badge-inferred'}">${op.must_preserve ? 'STRICT PRESERVE':'ADAPTABLE'}</span></td>
            <td style="color:var(--text-muted);">${op.notes || 'Natural boundary'}</td>
          </tr>`;
        });

        const tbodyFx = document.querySelector('#table-fixed-elements tbody');
        tbodyFx.innerHTML = '';
        (p.spatial_model.fixed_elements || []).forEach(fx => {
          tbodyFx.innerHTML += `<tr>
            <td><strong>${fx.name}</strong></td>
            <td>${fx.location_description}</td>
            <td><span class="badge badge-inferred">${fx.source}</span></td>
            <td><span class="badge badge-critical">${fx.relocation_difficulty}</span></td>
          </tr>`;
        });
      }

      // 5. Design Cards Grid
      if (p.current_design) {
        const d = p.current_design;
        const grid = document.getElementById('design-cards-grid');
        grid.innerHTML = `
          <div style="background:rgba(0,0,0,0.2); padding:1rem; border-radius:8px;">
            <div style="font-size:0.75rem; color:var(--text-muted);">CABINETRY FINISH</div>
            <div style="font-weight:700; margin-top:4px;">${d.cabinet_color}</div>
            <div style="font-size:0.8rem; color:var(--text-muted);">${d.cabinet_style}</div>
          </div>
          <div style="background:rgba(0,0,0,0.2); padding:1rem; border-radius:8px;">
            <div style="font-size:0.75rem; color:var(--text-muted);">COUNTERTOPS</div>
            <div style="font-weight:700; margin-top:4px;">${d.countertop_material}</div>
            <div style="font-size:0.8rem; color:var(--text-muted);">${d.countertop_finish}</div>
          </div>
          <div style="background:rgba(0,0,0,0.2); padding:1rem; border-radius:8px;">
            <div style="font-size:0.75rem; color:var(--text-muted);">FLOORING</div>
            <div style="font-weight:700; margin-top:4px;">${d.flooring_type}</div>
            <div style="font-size:0.8rem; color:var(--text-muted);">${d.flooring_finish}</div>
          </div>
          <div style="background:rgba(0,0,0,0.2); padding:1rem; border-radius:8px;">
            <div style="font-size:0.75rem; color:var(--text-muted);">WALL PAINT</div>
            <div style="font-weight:700; margin-top:4px;">${d.wall_paint}</div>
          </div>
          <div style="background:rgba(0,0,0,0.2); padding:1rem; border-radius:8px;">
            <div style="font-size:0.75rem; color:var(--text-muted);">FIXTURES & HARDWARE</div>
            <div style="font-weight:700; margin-top:4px;">${d.fixtures_hardware}</div>
          </div>
        `;
      }

      // 6. BOQ Table
      if (p.boq && p.boq.items) {
        const tbodyBOQ = document.querySelector('#table-boq tbody');
        tbodyBOQ.innerHTML = '';
        p.boq.items.forEach(i => {
          tbodyBOQ.innerHTML += `<tr>
            <td style="font-family:monospace;">${i.item_id}</td>
            <td><strong>${i.category}</strong></td>
            <td>${i.item_name}<br><span style="font-size:0.75rem; color:var(--text-muted);">${i.description}</span></td>
            <td>${i.quantity} ${i.unit}</td>
            <td>${sym}${i.material_unit_rate.toLocaleString()}</td>
            <td>${sym}${i.labor_unit_rate.toLocaleString()}</td>
            <td style="font-weight:700;">${sym}${i.total_amount.toLocaleString()}</td>
          </tr>`;
        });
        tbodyBOQ.innerHTML += `<tr style="background:rgba(59,130,246,0.1); font-weight:700;">
          <td colspan="6">GRAND TOTAL ESTIMATE (with 10% Contingency Reserve)</td>
          <td>${sym}${p.boq.grand_total.toLocaleString()}</td>
        </tr>`;
      }

      // 7. Value Engineering Table
      if (p.budget_optimization) {
        const b = p.budget_optimization;
        document.getElementById('opt-summary-text').innerText = b.summary_advice;
        const tbodyTr = document.querySelector('#table-tradeoffs tbody');
        tbodyTr.innerHTML = '';
        (b.trade_offs || []).forEach(tr => {
          tbodyTr.innerHTML += `<tr>
            <td><strong>${tr.category}</strong></td>
            <td style="color:#f87171;">${tr.original_item} (${sym}${tr.original_cost.toLocaleString()})</td>
            <td style="color:#34d399;">${tr.suggested_alternative} (${sym}${tr.alternative_cost.toLocaleString()})</td>
            <td style="font-weight:700; color:#60a5fa;">${sym}${tr.savings.toLocaleString()}</td>
            <td style="font-size:0.8rem; color:var(--text-muted);">${tr.compromise_description}</td>
          </tr>`;
        });
      }

      // 8. Timeline Table
      if (p.timeline && p.timeline.tasks) {
        document.getElementById('badge-timeline-weeks').innerText = `Total: ${p.timeline.total_calendar_weeks} Calendar Weeks`;
        const tbodyTl = document.querySelector('#table-timeline tbody');
        tbodyTl.innerHTML = '';
        p.timeline.tasks.forEach(t => {
          tbodyTl.innerHTML += `<tr>
            <td style="font-family:monospace;">${t.task_id}</td>
            <td><span class="badge">${t.phase_name.split(':')[0]}</span></td>
            <td><strong>${t.title}</strong><br><span style="font-size:0.75rem; color:var(--text-muted);">${t.description}</span></td>
            <td>${t.duration_days}d</td>
            <td style="font-family:monospace; font-size:0.75rem;">${t.depends_on.join(', ') || 'Start'}</td>
            <td>${t.trade_required}</td>
            <td>${t.inspection_required ? '<span class="badge badge-critical">REQUIRED</span>':'None'}</td>
          </tr>`;
        });
      }

      // 9. Permits & Regulatory Table
      if (p.permit_assessment) {
        document.getElementById('badge-jurisdiction').innerText = p.permit_assessment.jurisdiction_detected;
        document.getElementById('permits-guidance').innerText = p.permit_assessment.local_ahj_guidance;
        const tbodyCt = document.querySelector('#table-citations tbody');
        tbodyCt.innerHTML = '';
        (p.permit_assessment.citations || []).forEach(c => {
          tbodyCt.innerHTML += `<tr>
            <td><strong>${c.code_standard}</strong></td>
            <td style="font-family:monospace; color:#60a5fa;">${c.section_reference}</td>
            <td><strong>${c.title}</strong><br><span style="font-size:0.75rem; color:var(--text-muted);">${c.requirement_summary}</span></td>
            <td style="font-size:0.75rem; color:var(--text-muted);">${c.source_document}</td>
          </tr>`;
        });
      }

      // 10. Critic Findings & Risks
      if (p.critic_report) {
        document.getElementById('badge-critic-status').innerText = p.critic_report.approval_stamp;
        const flist = document.getElementById('critic-findings-list');
        flist.innerHTML = '';
        p.critic_report.findings.forEach(f => {
          flist.innerHTML += `
            <div style="background:rgba(0,0,0,0.2); border-left:3px solid ${f.severity==='BLOCKER'?'#ef4444':'#f59e0b'}; padding:0.75rem 1rem; border-radius:6px; margin-bottom:0.5rem;">
              <div style="font-weight:700; font-size:0.88rem;">${f.title} <span class="badge" style="margin-left:6px;">${f.severity}</span></div>
              <div style="font-size:0.8rem; color:var(--text-muted); margin-top:2px;">${f.description}</div>
              <div style="font-size:0.75rem; color:#60a5fa; margin-top:4px;">Fix: ${f.suggested_fix}</div>
            </div>`;
        });
      }
      if (p.risk_report) {
        const tbodyRk = document.querySelector('#table-risks tbody');
        tbodyRk.innerHTML = '';
        (p.risk_report.risks || []).forEach(rk => {
          tbodyRk.innerHTML += `<tr>
            <td style="text-transform:capitalize;"><strong>${rk.category}</strong></td>
            <td><span class="badge ${rk.level==='HIGH'?'badge-critical':(rk.level==='MEDIUM'?'badge-inferred':'badge-observed')}">${rk.level}</span></td>
            <td><strong>${rk.reason}</strong><br><span style="font-size:0.75rem; color:var(--text-muted);">${rk.evidence}</span></td>
            <td style="font-size:0.8rem; color:#34d399;">${rk.recommended_action}</td>
          </tr>`;
        });
      }
    }

    // Submit New Project
    async function submitNewProject() {
      const btn = document.getElementById('btn-submit-project');
      btn.innerText = "Analyzing & Synthesizing Plan...";
      btn.disabled = true;

      const payload = {
        name: document.getElementById('new-name').value,
        room_type: document.getElementById('new-room').value,
        scope: document.getElementById('new-scope').value,
        square_footage: parseInt(document.getElementById('new-sqft').value),
        location: document.getElementById('new-location').value,
        target_budget: parseFloat(document.getElementById('new-budget').value),
        currency: document.getElementById('new-currency').value,
        style: document.getElementById('new-style').value,
      };

      const fileInput = document.getElementById('new-image');
      if (fileInput.files.length > 0) {
        const reader = new FileReader();
        reader.onload = async function() {
          payload.image_data = reader.result;
          await executeCreateProject(payload);
        };
        reader.readAsDataURL(fileInput.files[0]);
      } else {
        await executeCreateProject(payload);
      }
    }

    async function executeCreateProject(payload) {
      try {
        const res = await fetch('/api/projects', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success && data.project) {
          closeNewProjectModal();
          await loadProjectList();
          loadSelectedProject(data.project.project_id);
          document.getElementById('project-selector').value = data.project.project_id;
        } else {
          alert("Error creating project: " + (data.error || "Unknown"));
        }
      } catch (err) {
        alert("Failed to create project: " + err);
      } finally {
        const btn = document.getElementById('btn-submit-project');
        btn.innerText = "Launch Plan";
        btn.disabled = false;
      }
    }

    // Export BOQ
    function exportBOQ(format) {
      if (!currentProject) return;
      window.open(`/api/projects/${currentProject.project_id}/export-boq?format=${format}`, '_blank');
    }

    // Chat Copilot
    async function sendChatMessage() {
      if (!currentProject) {
        alert("Please select or create a project first.");
        return;
      }
      const inp = document.getElementById('chat-input');
      const msg = inp.value.trim();
      if (!msg) return;

      const chatBox = document.getElementById('chat-box');
      chatBox.innerHTML += `<div class="chat-msg user">${msg}</div>`;
      inp.value = '';
      chatBox.scrollTop = chatBox.scrollHeight;

      // Detect if user is asking for a design edit
      const lower = msg.toLowerCase();
      const isEdit = lower.startsWith("make") || lower.startsWith("change") || lower.startsWith("switch") || lower.startsWith("replace") || lower.includes("cabinet") || lower.includes("countertop") || lower.includes("flooring") || lower.includes("paint");

      if (isEdit) {
        try {
          const res = await fetch(`/api/projects/${currentProject.project_id}/edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instruction: msg })
          });
          const data = await res.json();
          if (data.success) {
            chatBox.innerHTML += `<div class="chat-msg assistant">✨ <strong>Design Updated (Version ${data.version.version_id}):</strong><br>${data.designer_rationale}</div>`;
            currentProject = data.project;
            renderProjectUI(currentProject);
          } else {
            chatBox.innerHTML += `<div class="chat-msg assistant" style="color:#ef4444;">Error applying edit: ${data.error}</div>`;
          }
        } catch (err) {
          chatBox.innerHTML += `<div class="chat-msg assistant" style="color:#ef4444;">Network error: ${err}</div>`;
        }
      } else {
        try {
          const res = await fetch(`/api/projects/${currentProject.project_id}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg })
          });
          const data = await res.json();
          chatBox.innerHTML += `<div class="chat-msg assistant">${data.reply || data.error}</div>`;
        } catch (err) {
          chatBox.innerHTML += `<div class="chat-msg assistant" style="color:#ef4444;">Network error: ${err}</div>`;
        }
      }
      chatBox.scrollTop = chatBox.scrollHeight;
    }
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)


# ============================================================================
# Server Runner
# ============================================================================

def run_server(port: int = 8000, host: str = "127.0.0.1"):
    """Starts the FastAPI Web Application with port conflict handling."""
    import socket

    def is_port_in_use(p: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((host, p)) == 0

    target_port = port
    while is_port_in_use(target_port):
        logger.warning("Port %d is in use. Trying %d...", target_port, target_port + 1)
        target_port += 1

    print("\n" + "=" * 74)
    print("   [AI HOME RENOVATION INTELLIGENCE PLATFORM] - ENTERPRISE V2.5")
    print("   Powered by Google Gemini 3.6 / 3.8 Flash & Google ADK Multi-Agent")
    print("=" * 74)
    print(f"\n🚀 Server started successfully on port {target_port}!")
    print(f"👉 Web Dashboard: http://localhost:{target_port}")
    print("\nPress Ctrl+C to stop the server.\n")

    uvicorn.run(app, host=host, port=target_port, log_level="warning")


if __name__ == "__main__":
    run_server()
