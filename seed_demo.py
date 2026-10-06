"""Seeds realistic showcase demonstration projects for AI Home Renovation Intelligence Platform.

Adds:
1. Austin Chef's Modern Kitchen ($42,000 USD, Austin TX)
2. Bengaluru Contemporary Indian Villa (₹8,50,000 INR, Bengaluru India)
3. Pacific Heights Spa Bathroom ($28,000 USD, San Francisco CA)
"""

import sys
import asyncio

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from models import Project, Currency
import database
import spatial_vision
import design_engine
import budget_optimizer
import permit_rag
import boq_engine
import timeline_engine
import critic_engine


async def seed_showcase_projects():
    database.init_db()

    showcase_configs = [
        {
            "project_id": "demo-austin-kitchen",
            "name": "Austin Chef's Modern Kitchen",
            "room_type": "kitchen",
            "scope": "moderate",
            "square_footage": 180,
            "location": "Austin, TX",
            "currency": Currency.USD,
            "target_budget": 38000.0,
            "style": "modern",
            "user_notes": "Preserve existing window above sink. Desires Calacatta quartz countertops and two-tone cabinets.",
        },
        {
            "project_id": "demo-bengaluru-villa",
            "name": "Bengaluru Contemporary Indian Villa",
            "room_type": "kitchen",
            "scope": "full",
            "square_footage": 220,
            "location": "Bengaluru, India",
            "currency": Currency.INR,
            "target_budget": 850000.0,
            "style": "contemporary_indian",
            "user_notes": "Needs boiling water resistant modular cabinetry, fluted teak details, and NBC-compliant exhaust.",
        },
        {
            "project_id": "demo-spa-bathroom",
            "name": "Pacific Heights Spa Bathroom",
            "room_type": "bathroom",
            "scope": "moderate",
            "square_footage": 95,
            "location": "San Francisco, CA",
            "currency": Currency.USD,
            "target_budget": 28000.0,
            "style": "minimalist",
            "user_notes": "Walk-in curbless shower, anti-scald thermostatic valve, floating vanity with quartz top.",
        },
    ]

    print("[*] Seeding showcase demonstration projects into database...")
    for cfg in showcase_configs:
        pid = cfg["project_id"]
        # Check if already exists
        existing = database.get_project(pid)
        if existing:
            print(f"  [i] {cfg['name']} already exists. Skipping.")
            continue

        spatial_model = spatial_vision.build_fallback_spatial_model(
            room_type=cfg["room_type"],
            square_footage=cfg["square_footage"],
        )
        current_design = design_engine.create_initial_design_state(
            room_type=cfg["room_type"],
            style=cfg["style"],
            target_budget=cfg["target_budget"],
            currency=cfg["currency"],
            user_notes=cfg["user_notes"],
        )
        budget_opt = budget_optimizer.optimize_renovation_budget(
            room_type=cfg["room_type"],
            scope=cfg["scope"],
            square_footage=cfg["square_footage"],
            target_budget=cfg["target_budget"],
            currency=cfg["currency"],
            current_design=current_design,
        )
        boq = boq_engine.generate_automated_boq(
            project_id=pid,
            room_type=cfg["room_type"],
            scope=cfg["scope"],
            square_footage=cfg["square_footage"],
            spatial_model=spatial_model,
            design_state=current_design,
            currency=cfg["currency"],
        )
        permit_assessment = permit_rag.query_regulatory_rag(
            room_type=cfg["room_type"],
            scope=cfg["scope"],
            structural_changes=cfg["scope"] == "full",
            plumbing_changes=True,
            electrical_changes=True,
            location=cfg["location"],
        )
        timeline = timeline_engine.build_construction_schedule(
            project_id=pid,
            room_type=cfg["room_type"],
            scope=cfg["scope"],
            structural_changes=cfg["scope"] == "full",
            plumbing_changes=True,
            electrical_changes=True,
        )
        critic_report = critic_engine.evaluate_plan_critic(
            spatial_model=spatial_model,
            design_state=current_design,
            boq=boq,
            timeline=timeline,
            permit_assessment=permit_assessment,
            budget_opt=budget_opt,
            room_type=cfg["room_type"],
            scope=cfg["scope"],
            target_budget=cfg["target_budget"],
        )
        risk_report = critic_engine.calculate_renovation_risk_report(
            room_type=cfg["room_type"],
            scope=cfg["scope"],
            structural_changes=cfg["scope"] == "full",
            plumbing_changes=True,
            electrical_changes=True,
            budget_overrun=budget_opt.overrun_amount,
            square_footage=cfg["square_footage"],
        )
        quality_score = critic_engine.calculate_design_quality_score(
            critic_report=critic_report,
            risk_report=risk_report,
            budget_opt=budget_opt,
            room_type=cfg["room_type"],
            scope=cfg["scope"],
        )

        project = Project(
            project_id=pid,
            name=cfg["name"],
            room_type=cfg["room_type"],
            scope=cfg["scope"],
            square_footage=cfg["square_footage"],
            location=cfg["location"],
            currency=cfg["currency"],
            target_budget=cfg["target_budget"],
            style=cfg["style"],
            current_version=1,
            spatial_model=spatial_model,
            current_design=current_design,
            boq=boq,
            budget_optimization=budget_opt,
            timeline=timeline,
            permit_assessment=permit_assessment,
            critic_report=critic_report,
            risk_report=risk_report,
            quality_score=quality_score,
        )
        database.create_project(project)
        print(f"  [OK] Created showcase project: {cfg['name']} ({cfg['currency'].value})")

    print("[OK] Showcase seeding complete! You can now select these from the UI dropdown.")


if __name__ == "__main__":
    asyncio.run(seed_showcase_projects())
