"""AI Home Renovation Planner - Coordinator/Dispatcher Pattern with Multimodal Vision.

This demonstrates ADK's Coordinator/Dispatcher Pattern with Gemini's multimodal
capabilities where a routing agent analyzes requests and delegates to specialists:

- General questions → InfoAgent (Quick info & project scoping)
- Renovation planning → PlanningPipeline (VisualAssessor → DesignPlanner → ProjectCoordinator)
- Iterative rendering edits → RenderingEditor (Refines existing renderings)

Pattern Reference: https://google.github.io/adk-docs/agents/multi-agents/#coordinator-dispatcher-pattern
"""

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool

# Robust import supporting both package and standalone execution
try:
    from .tools import (
        generate_renovation_rendering,
        edit_renovation_rendering,
        list_renovation_renderings,
        list_reference_images,
        check_renovation_permits,
        recommend_materials_and_finishes,
    )
except (ImportError, ValueError):
    from tools import (
        generate_renovation_rendering,
        edit_renovation_rendering,
        list_renovation_renderings,
        list_reference_images,
        check_renovation_permits,
        recommend_materials_and_finishes,
    )


# ============================================================================
# Helper Tool Agent (wraps google_search)
# ============================================================================

search_agent = LlmAgent(
    name="SearchAgent",
    model="gemini-3.6-flash",
    description="Searches online for current renovation costs, local contractors, materials, and design trends",
    instruction="""You are a home renovation search specialist.
When asked to research current material prices, local labor rates, contractor requirements, or interior design trends,
use your search capability to find accurate, up-to-date information.
Be concise, practical, and cite sources or retail references when available.""",
    tools=[google_search],
)


# ============================================================================
# Utility Domain Functions (Cost & Timeline Estimators)
# ============================================================================

def estimate_renovation_cost(
    room_type: str,
    scope: str = "moderate",
    square_footage: int = 150,
) -> str:
    """Estimates detailed renovation costs with itemized breakdown and estimated ROI.
    
    Args:
        room_type: Type of room (kitchen, bathroom, master_bedroom, bedroom, living_room, dining_room, home_office, basement, laundry_room, outdoor_patio)
        scope: Renovation scope (cosmetic, moderate, full, luxury)
        square_footage: Room size in square feet (default: 150)
    
    Returns:
        Structured budget breakdown including materials, labor, permits, contingency, and ROI.
    """
    rates = {
        "kitchen": {"cosmetic": (50, 100), "moderate": (150, 250), "full": (300, 500), "luxury": (600, 1200)},
        "bathroom": {"cosmetic": (75, 125), "moderate": (200, 350), "full": (400, 600), "luxury": (800, 1500)},
        "master_bedroom": {"cosmetic": (35, 70), "moderate": (90, 180), "full": (180, 350), "luxury": (450, 900)},
        "bedroom": {"cosmetic": (30, 60), "moderate": (75, 150), "full": (150, 300), "luxury": (400, 800)},
        "living_room": {"cosmetic": (40, 80), "moderate": (100, 200), "full": (200, 400), "luxury": (500, 1000)},
        "dining_room": {"cosmetic": (35, 70), "moderate": (85, 175), "full": (175, 350), "luxury": (450, 900)},
        "home_office": {"cosmetic": (30, 60), "moderate": (75, 160), "full": (160, 320), "luxury": (400, 850)},
        "basement": {"cosmetic": (40, 75), "moderate": (90, 180), "full": (180, 350), "luxury": (400, 800)},
        "laundry_room": {"cosmetic": (50, 90), "moderate": (120, 220), "full": (220, 400), "luxury": (500, 900)},
        "outdoor_patio": {"cosmetic": (30, 55), "moderate": (65, 130), "full": (130, 260), "luxury": (300, 600)},
    }

    roi_estimates = {
        "kitchen": "70% - 85% (highest value add)",
        "bathroom": "65% - 78% (strong buyer appeal)",
        "master_bedroom": "55% - 70%",
        "bedroom": "50% - 65%",
        "living_room": "55% - 68%",
        "dining_room": "50% - 60%",
        "home_office": "55% - 70%",
        "basement": "65% - 75% (valuable additional square footage)",
        "laundry_room": "60% - 72%",
        "outdoor_patio": "55% - 70%",
    }

    clean_room = room_type.lower().replace(" ", "_")
    scope_lvl = scope.lower()

    if clean_room not in rates:
        clean_room = "living_room"
    if scope_lvl not in rates[clean_room]:
        scope_lvl = "moderate"

    sqft = max(square_footage, 25)
    low_rate, high_rate = rates[clean_room][scope_lvl]

    total_low = low_rate * sqft
    total_high = high_rate * sqft
    midpoint = (total_low + total_high) // 2

    materials_est = int(midpoint * 0.42)
    labor_est = int(midpoint * 0.45)
    permits_est = int(midpoint * 0.03) if scope_lvl in ["moderate", "full", "luxury"] else 0
    contingency_est = int(midpoint * 0.10)
    expected_roi = roi_estimates.get(clean_room, "55% - 70%")

    return (
        f"💰 **Estimated Budget Breakdown ({scope_lvl.title()} {clean_room.replace('_', ' ').title()}, ~{sqft} sq ft)**:\n"
        f"• **Estimated Cost Range**: ${total_low:,} - ${total_high:,} (Typical Midpoint: ~${midpoint:,})\n"
        f"  - 📦 Materials & Finishes (42%): ~${materials_est:,}\n"
        f"  - 👷 Professional Labor & Trades (45%): ~${labor_est:,}\n"
        f"  - 📄 Permits & Inspections (3%): ~${permits_est:,}\n"
        f"  - 🛡️ Recommended Contingency Fund (10%): ~${contingency_est:,}\n"
        f"• **Estimated Resale ROI Potential**: {expected_roi}"
    )


def calculate_timeline(
    scope: str = "moderate",
    room_type: str = "kitchen",
) -> str:
    """Estimates renovation timeline broken down into sequential project phases.
    
    Args:
        scope: Renovation scope (cosmetic, moderate, full, luxury)
        room_type: Type of room being renovated
    
    Returns:
        Estimated phase-by-phase project schedule.
    """
    timelines = {
        "cosmetic": {
            "total": "1 - 2 weeks",
            "phases": [
                ("Phase 1 (Days 1-2)", "Material procurement & room clearing"),
                ("Phase 2 (Days 3-7)", "Surface prep, cabinet painting / refacing, trim repairs"),
                ("Phase 3 (Days 8-12)", "Hardware updates, light fixture swaps, flooring touches"),
                ("Phase 4 (Days 13-14)", "Deep clean, styling, and final punch list"),
            ],
        },
        "moderate": {
            "total": "3 - 6 weeks",
            "phases": [
                ("Phase 1 (Week 1)", "Demolition, layout prep & permit approvals"),
                ("Phase 2 (Weeks 2-3)", "Plumbing/electrical adjustments & rough-in inspections"),
                ("Phase 3 (Weeks 3-4)", "Tile installation, new countertops & cabinet installation"),
                ("Phase 4 (Weeks 4-5)", "Flooring installation, painting & trim work"),
                ("Phase 5 (Week 6)", "Appliance install, fixture trims & final inspection"),
            ],
        },
        "full": {
            "total": "2 - 4 months",
            "phases": [
                ("Phase 1 (Weeks 1-2)", "Architectural drawings, permits & materials ordering"),
                ("Phase 2 (Weeks 3-4)", "Full demolition down to studs/subfloor"),
                ("Phase 3 (Weeks 5-8)", "Framing, plumbing/HVAC/electrical rough-in & city inspections"),
                ("Phase 4 (Weeks 9-11)", "Insulation, drywall, painting, custom cabinetry & countertops"),
                ("Phase 5 (Weeks 12-14)", "Tile, premium flooring, plumbing trims & final sign-offs"),
            ],
        },
        "luxury": {
            "total": "4 - 6 months",
            "phases": [
                ("Phase 1 (Month 1)", "Engineering, bespoke design plans, permits & custom material fabrication"),
                ("Phase 2 (Month 2)", "Structural modifications, precision rough-ins & architectural inspections"),
                ("Phase 3 (Month 3-4)", "Custom cabinetry installation, bookmatched stone fabrication & specialized tiling"),
                ("Phase 4 (Month 5)", "Hardwood laying, bespoke lighting, smart home automation integration"),
                ("Phase 5 (Month 6)", "Fine trim finishing, specialty coatings, final testing & sign-off"),
            ],
        },
    }

    scope_lvl = scope.lower()
    data = timelines.get(scope_lvl, timelines["moderate"])

    lines = [
        f"⏱️ **Estimated Project Timeline ({scope_lvl.title()} Renovation - Total: {data['total']})**:",
        f"Room: **{room_type.replace('_', ' ').title()}**\n",
    ]
    for phase_name, desc in data["phases"]:
        lines.append(f"• **{phase_name}**: {desc}")

    return "\n".join(lines)


# ============================================================================
# Specialist Agent 1: Info Agent (General inquiries & scoping)
# ============================================================================

info_agent = LlmAgent(
    name="InfoAgent",
    model="gemini-3.6-flash",
    description="Handles general renovation questions, system capabilities, and user onboarding",
    instruction="""
You are the Info Agent for the AI Home Renovation Planner.

ROLE: The coordinator routes general questions, casual greetings, and system inquiries to you.

YOUR RESPONSE GUIDELINES:
- Keep it friendly, clear, and helpful (2-4 sentences).
- Explain how our multi-agent AI system helps homeowners plan their renovations:
  1. Multimodal visual inspection of current room photos and inspiration pictures
  2. Budget estimation and materials recommendation
  3. Building permit and code compliance review
  4. Photorealistic rendering generation with layout preservation
  5. Step-by-step project timeline and contractor guidance
- Prompt the user to tell you which room they want to renovate and invite them to share room photos or their desired aesthetic.
""",
)


# ============================================================================
# Specialist Agent 2: Rendering Editor (Iterative refinements)
# ============================================================================

rendering_editor = LlmAgent(
    name="RenderingEditor",
    model="gemini-3.6-flash",
    description="Refines and edits existing renovation renderings based on user feedback",
    instruction="""
You are the Rendering Editor specialist for the AI Home Renovation Planner.

TASK: When the user wants to refine or alter an existing rendering (e.g., "make cabinets navy blue", "switch to brass hardware", "add pendant lights"),
you coordinate the edit using `edit_renovation_rendering`.

WORKFLOW:
1. Identify the target rendering artifact filename from conversation history or use `list_renovation_renderings` to check available renderings.
2. Formulate a precise, descriptive prompt for `edit_renovation_rendering`. Specify clearly what to change (e.g. colors, textures, lighting) while keeping untouched elements identical.
3. Call `edit_renovation_rendering`.
4. Confirm the updated version to the user concisely.

IMPORTANT: Do not output broken markdown image syntax like `![image](file.png)`. The artifacts panel handles rendering visualization.
""",
    tools=[edit_renovation_rendering, list_renovation_renderings],
)


# ============================================================================
# Specialist Agents 3-5: Planning Pipeline (Sequential Execution)
# ============================================================================

visual_assessor = LlmAgent(
    name="VisualAssessor",
    model="gemini-3.6-flash",
    description="Analyzes room photos and inspiration images using multimodal visual AI",
    instruction="""
You are the Visual Assessor specialist. Analyze ANY uploaded images and user descriptions.

CAPABILITIES:
1. Detect whether an image shows a CURRENT ROOM (existing space) or INSPIRATION/STYLE reference.
2. For Current Room photos:
   - Identify room type, estimated dimensions, current condition, and structural constraints.
   - CRITICAL: Document exact layout elements to PRESERVE: window positions, door locations, cabinet footprint, appliance hookups, sink placement, and camera perspective.
3. For Inspiration photos:
   - Extract design style, color palettes, materials (wood types, countertop stone, metal finishes), and lighting themes.
4. If budget or size is mentioned, use `estimate_renovation_cost` to calculate an initial cost range.
5. If reference images are uploaded, you can view existing uploads using `list_reference_images`.

OUTPUT STRUCTURE:
Provide a crisp, structured assessment summary:
- **Room Type & Detected Condition**
- **Existing Layout To Preserve** (windows, doors, cabinet line, appliances)
- **Desired Aesthetic & Color Palette**
- **Preliminary Cost Range** (via `estimate_renovation_cost`)
""",
    tools=[AgentTool(search_agent), estimate_renovation_cost, list_reference_images],
)


design_planner = LlmAgent(
    name="DesignPlanner",
    model="gemini-3.6-flash",
    description="Creates detailed design specifications, material selections, and schedule milestones",
    instruction="""
You are the Design Planner specialist. Build upon the Visual Assessor's analysis to create a cohesive renovation design.

RULES:
1. **Preserve Layout**: Unless the user specifically asks for walls to be moved, focus changes strictly on surface finishes, cabinetry, lighting, and fixtures.
2. **Material Recommendations**: Use `recommend_materials_and_finishes` to select durable, stylish materials suitable for the room and budget.
3. **Timeline Calculation**: Use `calculate_timeline` with the determined room type and renovation scope.

OUTPUT STRUCTURE:
- **Design Concept & Color Palette** (specific paint codes and undertones)
- **Surfaces & Finishes** (cabinets, countertops, backsplash, flooring)
- **Lighting & Fixtures** (task, ambient, accent lighting)
- **Recommended Materials** (with durability and cost tier)
- **Project Timeline** (from `calculate_timeline`)
""",
    tools=[recommend_materials_and_finishes, calculate_timeline],
)


project_coordinator = LlmAgent(
    name="ProjectCoordinator",
    model="gemini-3.6-flash",
    description="Coordinates budget, permits, contractor trades, and triggers photorealistic rendering",
    instruction="""
You are the Project Coordinator specialist. Finalize the renovation plan and produce visual renderings.

WORKFLOW:
1. Review the Visual Assessor's layout notes and Design Planner's specifications.
2. Check permit and building code requirements using `check_renovation_permits`.
3. Provide a consolidated budget summary (Materials, Labor, Permits, 10% Contingency).
4. Create a photorealistic visual rendering using `generate_renovation_rendering`:
   - Construct an ultra-detailed SLC (Subject, Lighting, Camera) prompt:
     - **Camera**: Professional architectural DSLR photography, wide-angle interior lens, 8K HDR, tack-sharp focus.
     - **Subject**: Renovated space incorporating the exact design materials, maintaining original window/door/cabinet layout.
     - **Lighting**: Diffused daylight streaming through windows, warm 2700K ambient recessed lighting, under-cabinet illumination.
   - Pass `asset_name="[room]_[style]_renovation"` and `aspect_ratio="16:9"`.
5. Present the final executive summary to the user with actionable next steps for hiring contractors.

IMPORTANT: Do not output markdown image syntax like `![image](url)`. Renderings are saved as artifacts in the session panel.
""",
    tools=[
        check_renovation_permits,
        generate_renovation_rendering,
        edit_renovation_rendering,
        list_renovation_renderings,
        list_reference_images,
    ],
)


# Sequential Agent: Planning Pipeline
planning_pipeline = SequentialAgent(
    name="PlanningPipeline",
    description="Complete 3-stage renovation pipeline: Visual Assessment → Design Planning → Project Coordination & Rendering",
    sub_agents=[
        visual_assessor,
        design_planner,
        project_coordinator,
    ],
)


# ============================================================================
# Coordinator / Dispatcher (Root Agent)
# ============================================================================

root_agent = LlmAgent(
    name="HomeRenovationPlanner",
    model="gemini-3.6-flash",
    description="Intelligent coordinator that routes home renovation inquiries to specialists or the full planning pipeline.",
    instruction="""
You are the Master Coordinator for the AI Home Renovation Planner.

YOUR ROLE: Analyze the user's intent and route to the appropriate specialist using `transfer_to_agent`.

ROUTING LOGIC:
1. **General Inquiries & Casual Greetings**:
   → `transfer_to_agent` to "InfoAgent"
   → Examples: "Hi", "What can this app do?", "How much does a remodel typically cost?"

2. **Editing an Existing Rendering**:
   → `transfer_to_agent` to "RenderingEditor"
   → Examples: "Make the cabinets sage green", "Change the floor to dark oak", "Add brass pendants"
   → Use this when the user is refining a design already created in this conversation.

3. **New Renovation Project or Image Uploaded**:
   → `transfer_to_agent` to "PlanningPipeline"
   → Examples: "Here is a photo of my kitchen, help me renovate it", "Plan a master bathroom remodel for $15,000", "I want a modern farmhouse living room"
   → ALWAYS route here when a new space is being planned or when room/inspiration images are shared.

CRITICAL: Always delegate via `transfer_to_agent` to ensure the dedicated specialist handles the domain tasks.
""",
    sub_agents=[
        info_agent,
        rendering_editor,
        planning_pipeline,
    ],
)


__all__ = ["root_agent"]