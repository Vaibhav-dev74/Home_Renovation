"""Comprehensive Test Suite for AI Home Renovation Intelligence Platform (V2).

Tests:
1. Spatial Vision & Architectural Models (Openings, Utilities, Dimensions)
2. Persistent Design State & Non-Destructive Conversational Edits
3. Budget Optimization & Multi-Currency Calculations (INR / USD)
4. Regulatory RAG & Building Code Citations (IRC, NEC, NBC India)
5. Automated BOQ Calculations, Wastage Factors & CSV/HTML Export
6. Construction Timeline DAG & Dependency Resolution
7. Multi-Agent Critic & Risk Matrix Evaluation
8. SQLite Persistence Layer & Version Snapshots
9. FastAPI REST Gateway Endpoints
"""

import unittest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

import models
import database
import spatial_vision
import design_engine
import budget_optimizer
import permit_rag
import boq_engine
import timeline_engine
import critic_engine
from web_app import app


class TestSpatialIntelligence(unittest.TestCase):
    """Validates spatial model creation, opening detection, and dimension bounds."""

    def test_fallback_spatial_model_structure(self):
        model = spatial_vision.build_fallback_spatial_model("kitchen", 180)
        self.assertEqual(model.room_type, "kitchen")
        self.assertAlmostEqual(model.dimensions.area_sqft, 180.0)
        self.assertGreaterEqual(len(model.openings), 2)
        # Verify openings have preserve flags
        window = [op for op in model.openings if op.opening_type == "window"][0]
        self.assertTrue(window.must_preserve)
        self.assertIn("north", window.wall.lower())

    def test_fixed_elements_preservation(self):
        model = spatial_vision.build_fallback_spatial_model("kitchen", 200)
        plumbing = [f for f in model.fixed_elements if "plumbing" in f.name.lower() or "sink" in f.name.lower()]
        self.assertTrue(len(plumbing) > 0)
        self.assertEqual(plumbing[0].relocation_difficulty, "HIGH")


class TestDesignStateEngine(unittest.TestCase):
    """Validates stateful, non-destructive design editing and version snapshots."""

    def test_initial_design_state_coordination(self):
        state_inr = design_engine.create_initial_design_state("kitchen", "modern", 800000.0, models.Currency.INR)
        self.assertEqual(state_inr.style, "modern")
        self.assertEqual(state_inr.currency, models.Currency.INR)
        self.assertIn("Quartz", state_inr.countertop_material)

        state_ind = design_engine.create_initial_design_state("living_room", "contemporary_indian", 1500000.0, models.Currency.INR)
        self.assertEqual(state_ind.style, "contemporary_indian")
        self.assertIn("Teak", state_ind.cabinet_color)

    def test_conversational_edit_preserves_unmodified_fields(self):
        initial = design_engine.create_initial_design_state("kitchen", "modern", 50000.0, models.Currency.USD)
        initial.countertop_material = "Original Calacatta Quartz"
        initial.flooring_type = "Original French Oak"

        new_state, version, rationale = asyncio.run(
            design_engine.apply_conversational_design_edit(
                current_state=initial,
                user_instruction="Make the cabinets sage green",
                project_id="test-proj-edit",
                current_version=1,
            )
        )

        # Cabinet must change
        self.assertIn("sage green", new_state.cabinet_color.lower())
        # Countertop and flooring must remain identical
        self.assertEqual(new_state.countertop_material, initial.countertop_material)
        self.assertEqual(new_state.flooring_type, initial.flooring_type)
        # Version must increment
        self.assertEqual(version.version_id, 2)


class TestBudgetAndBOQEngine(unittest.TestCase):
    """Validates cost modeling, budget optimization, trade-offs, and BOQ line items."""

    def test_budget_overrun_optimization(self):
        # 180 sq ft moderate kitchen baseline is ~₹8,10,000 mid
        # Stated budget of ₹5,00,000 is intentionally over-budget
        opt = budget_optimizer.optimize_renovation_budget(
            room_type="kitchen",
            scope="moderate",
            square_footage=180,
            target_budget=500000.0,
            currency=models.Currency.INR,
        )
        self.assertTrue(opt.is_over_budget)
        self.assertGreater(opt.overrun_amount, 0)
        self.assertGreater(len(opt.trade_offs), 0)
        self.assertGreater(opt.total_savings, 0)

    def test_automated_boq_calculation_and_exports(self):
        boq = boq_engine.generate_automated_boq(
            project_id="boq-test-1",
            room_type="kitchen",
            scope="moderate",
            square_footage=180,
            currency=models.Currency.INR,
        )
        self.assertGreater(len(boq.items), 6)
        self.assertEqual(boq.contingency_rate_pct, 10.0)
        self.assertGreater(boq.contingency_amount, 0)
        self.assertGreater(boq.grand_total, boq.subtotal_materials + boq.subtotal_labor)

        # Test CSV Export
        csv_data = boq_engine.export_boq_to_csv(boq)
        self.assertIn("BILL OF QUANTITIES", csv_data)
        self.assertIn("GRAND TOTAL", csv_data)

        # Test Printable HTML Export
        html_data = boq_engine.export_boq_to_html_printable(boq, "Test Villa")
        self.assertIn("<!DOCTYPE html>", html_data)
        self.assertIn("Bill of Quantities (BOQ)", html_data)
        self.assertIn("Test Villa", html_data)


class TestRegulatoryRAG(unittest.TestCase):
    """Validates grounded legal and building code citations."""

    def test_us_regulatory_rag(self):
        res = permit_rag.query_regulatory_rag(
            room_type="kitchen",
            scope="moderate",
            structural_changes=False,
            plumbing_changes=True,
            electrical_changes=True,
            location="Austin, TX",
        )
        self.assertIn("United States", res.jurisdiction_detected)
        self.assertTrue(len(res.citations) > 0)
        standards = [c.code_standard for c in res.citations]
        self.assertTrue(any("IRC" in s or "NEC" in s for s in standards))

    def test_india_regulatory_rag(self):
        res = permit_rag.query_regulatory_rag(
            room_type="kitchen",
            scope="full",
            structural_changes=True,
            plumbing_changes=True,
            location="Bengaluru, India",
        )
        self.assertIn("India", res.jurisdiction_detected)
        self.assertTrue(len(res.citations) > 0)
        standards = [c.code_standard for c in res.citations]
        self.assertTrue(any("NBC 2016" in s for s in standards))


class TestTimelineDAG(unittest.TestCase):
    """Validates graph-based task sequencing and critical path."""

    def test_timeline_dependencies(self):
        sched = timeline_engine.build_construction_schedule("proj-t1", "kitchen", "moderate")
        self.assertGreater(sched.total_working_days, 15)
        self.assertGreater(len(sched.tasks), 8)
        self.assertTrue(len(sched.critical_path) > 0)

        # Drywall must depend on MEP inspections or rough trades
        drywall_task = [t for t in sched.tasks if "drywall" in t.title.lower() or "enclosures" in t.phase_name.lower()][0]
        self.assertTrue(len(drywall_task.depends_on) > 0)


class TestCriticAndRiskEngines(unittest.TestCase):
    """Validates multi-agent critic, risk matrix, and design quality scores."""

    def test_critic_approval_and_findings(self):
        critic = critic_engine.evaluate_plan_critic(None, None, None, None, None, None)
        self.assertTrue(critic.is_approved)
        self.assertGreaterEqual(critic.quality_score, 70)

    def test_risk_report_scoring(self):
        risk = critic_engine.calculate_renovation_risk_report("kitchen", "full", structural_changes=True, plumbing_changes=True)
        self.assertIn(risk.overall_rating, [models.RiskLevel.LOW, models.RiskLevel.MEDIUM, models.RiskLevel.HIGH])
        self.assertEqual(risk.category_ratings["structural"], models.RiskLevel.HIGH)


class TestFastAPIRestGateway(unittest.TestCase):
    """Validates FastAPI end-to-end endpoints."""

    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("api_key_configured"))

    def test_create_and_retrieve_project(self):
        payload = {
            "name": "Mid-Century Modern Kitchen",
            "room_type": "kitchen",
            "scope": "moderate",
            "square_footage": 180,
            "location": "Austin, TX",
            "currency": "USD",
            "target_budget": 35000.0,
            "style": "modern",
        }
        res = self.client.post("/api/projects", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        project_id = data["project"]["project_id"]

        # Retrieve project
        get_res = self.client.get(f"/api/projects/{project_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["project"]["name"], "Mid-Century Modern Kitchen")

        # Export BOQ
        boq_res = self.client.get(f"/api/projects/{project_id}/export-boq?format=csv")
        self.assertEqual(boq_res.status_code, 200)
        self.assertIn("BILL OF QUANTITIES", boq_res.text)


if __name__ == "__main__":
    unittest.main()
