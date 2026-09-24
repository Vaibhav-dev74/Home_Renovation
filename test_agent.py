"""Unit tests for AI Home Renovation Planner Multi-Agent System."""

import unittest
from pathlib import Path
from google.adk.tools import ToolContext
from google.adk.cli.cli import AgentLoader

import tools
import agent


class DummyToolContext(ToolContext):
    """Mock ToolContext for local testing of state and helper methods."""
    def __init__(self):
        self._state = {}

    @property
    def state(self):
        return self._state


class TestRenovationTools(unittest.TestCase):

    def test_tools_exported(self):
        """Verify all critical tools and helper utilities are exported."""
        expected_exports = [
            "generate_renovation_rendering",
            "edit_renovation_rendering",
            "list_renovation_renderings",
            "list_reference_images",
            "save_uploaded_image_as_artifact",
            "check_renovation_permits",
            "recommend_materials_and_finishes",
            "get_asset_versions_info",
            "get_reference_images_info",
        ]
        for exp in expected_exports:
            self.assertTrue(hasattr(tools, exp), f"Missing export in tools: {exp}")

    def test_estimate_renovation_cost(self):
        """Verify cost estimation breakdown and calculations across rooms and scopes."""
        rooms = ["kitchen", "bathroom", "master_bedroom", "basement", "living_room"]
        for room in rooms:
            for scope in ["cosmetic", "moderate", "full", "luxury"]:
                result = agent.estimate_renovation_cost(room, scope, 200)
                self.assertIn("Estimated Budget Breakdown", result)
                self.assertIn("Materials & Finishes", result)
                self.assertIn("Professional Labor & Trades", result)
                self.assertIn("Estimated Resale ROI Potential", result)
                self.assertIn("$", result)

    def test_calculate_timeline(self):
        """Verify timeline phase generation across scopes."""
        for scope in ["cosmetic", "moderate", "full", "luxury"]:
            result = agent.calculate_timeline(scope, "kitchen")
            self.assertIn("Estimated Project Timeline", result)
            self.assertIn("Phase 1", result)
            self.assertIn("kitchen", result.lower())

    def test_check_renovation_permits(self):
        """Verify permit advisory logic for cosmetic vs structural renovations."""
        # Cosmetic should not require permits
        cosmetic_res = tools.check_renovation_permits("kitchen", "cosmetic", False, False, False)
        self.assertIn("No Major Building Permits Typically Required", cosmetic_res)

        # Full renovation with plumbing and electrical should require permits
        major_res = tools.check_renovation_permits(
            room_type="kitchen",
            scope="full",
            structural_changes=True,
            plumbing_changes=True,
            electrical_changes=True,
        )
        self.assertIn("Building / Structural Permit", major_res)
        self.assertIn("Plumbing Permit", major_res)
        self.assertIn("Electrical Permit", major_res)
        self.assertIn("Required Inspection Milestones", major_res)

    def test_recommend_materials_and_finishes(self):
        """Verify material recommendations by room and budget tier."""
        tiers = ["budget_friendly", "moderate", "luxury"]
        for tier in tiers:
            res = tools.recommend_materials_and_finishes("kitchen", "modern", tier)
            self.assertIn("Material & Finish Recommendations", res)
            self.assertIn("Countertops", res)
            self.assertIn("Cabinetry", res)

    def test_version_management_helpers(self):
        """Verify artifact versioning and filename formatting."""
        ctx = DummyToolContext()
        v1 = tools.get_next_version_number(ctx, "kitchen_render")
        self.assertEqual(v1, 1)

        filename1 = tools.create_versioned_filename("kitchen render", v1)
        self.assertEqual(filename1, "kitchen_render_v1.png")

        tools.update_asset_version(ctx, "kitchen_render", v1, filename1)
        v2 = tools.get_next_version_number(ctx, "kitchen_render")
        self.assertEqual(v2, 2)

        info = tools.get_asset_versions_info(ctx)
        self.assertIn("kitchen_render", info)
        self.assertIn("v1", info)


class TestAgentArchitecture(unittest.TestCase):

    def test_root_agent_hierarchy(self):
        """Verify root coordinator agent and subagent composition."""
        root = agent.root_agent
        self.assertEqual(root.name, "HomeRenovationPlanner")
        subagent_names = [s.name for s in root.sub_agents]
        self.assertIn("InfoAgent", subagent_names)
        self.assertIn("RenderingEditor", subagent_names)
        self.assertIn("PlanningPipeline", subagent_names)

    def test_planning_pipeline_specialists(self):
        """Verify sequential pipeline specialists and tools."""
        pipeline = agent.planning_pipeline
        self.assertEqual(pipeline.name, "PlanningPipeline")
        specialists = [s.name for s in pipeline.sub_agents]
        self.assertEqual(specialists, ["VisualAssessor", "DesignPlanner", "ProjectCoordinator"])

        def get_tool_name(t):
            return getattr(t, "name", getattr(t, "__name__", str(t)))

        # Check VisualAssessor tools
        va = pipeline.sub_agents[0]
        va_tool_names = [get_tool_name(t) for t in va.tools]
        self.assertIn("estimate_renovation_cost", va_tool_names)
        self.assertIn("list_reference_images", va_tool_names)

        # Check DesignPlanner tools
        dp = pipeline.sub_agents[1]
        dp_tool_names = [get_tool_name(t) for t in dp.tools]
        self.assertIn("recommend_materials_and_finishes", dp_tool_names)
        self.assertIn("calculate_timeline", dp_tool_names)

        # Check ProjectCoordinator tools
        pc = pipeline.sub_agents[2]
        pc_tool_names = [get_tool_name(t) for t in pc.tools]
        self.assertIn("check_renovation_permits", pc_tool_names)
        self.assertIn("generate_renovation_rendering", pc_tool_names)
        self.assertIn("edit_renovation_rendering", pc_tool_names)
        self.assertIn("list_renovation_renderings", pc_tool_names)

    def test_adk_agent_loader_discovery(self):
        """Verify Google ADK AgentLoader can discover and load the root agent."""
        parent_dir = Path(__file__).resolve().parent.parent
        loader = AgentLoader(str(parent_dir))
        agents = loader.list_agents()
        self.assertIn("ai_home_renovation_agent", agents)

        loaded_agent = loader.load_agent("ai_home_renovation_agent")
        self.assertIsNotNone(loaded_agent)
        self.assertEqual(loaded_agent.name, "HomeRenovationPlanner")


if __name__ == "__main__":
    unittest.main()
