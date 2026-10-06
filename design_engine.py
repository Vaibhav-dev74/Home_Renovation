"""Design Engine & Conversational State Editor.

Maintains persistent, structured DesignState, applies non-destructive delta edits,
tracks version history, and compiles grounded SLC (Subject, Lighting, Camera) rendering briefs.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple

import tools
from models import DesignState, DesignVersion, SpatialModel, Currency

logger = logging.getLogger(__name__)


def extract_json_block(text: str) -> str:
    """Extracts JSON substring from text, handling markdown fences."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def create_initial_design_state(
    room_type: str,
    style: str = "modern",
    target_budget: float = 800000.0,
    currency: Currency = Currency.INR,
    user_notes: Optional[str] = None,
) -> DesignState:
    """Creates a sensible, aesthetically coordinated initial DesignState."""
    clean_style = style.lower()
    
    style_profiles = {
        "modern": {
            "wall_paint": "Warm Off-White (Sherwin-Williams Alabaster)",
            "flooring_type": "Porcelain Tile",
            "flooring_finish": "Large format 24x48 matte neutral grey porcelain",
            "cabinet_style": "Flat-Panel Slab",
            "cabinet_color": "Two-tone: Matte Charcoal base with Natural White Oak uppers",
            "countertop_material": "Engineered Quartz",
            "countertop_finish": "Calacatta Gold with subtle warm gold/grey veining",
            "backsplash": "Matching full-height quartz slab",
            "fixtures_hardware": "Brushed brass bar pulls and minimal gooseneck pull-down faucet",
            "palette": ["#2D3142", "#FFFFFF", "#C5A880", "#E0E0E0"],
        },
        "contemporary_indian": {
            "wall_paint": "Warm Creamy Ivory with a textured lime-wash accent wall",
            "flooring_type": "Honed Kota Stone / Polished Italian Marble",
            "flooring_finish": "Seamless large-format honed greyish-green stone with brass inlays",
            "cabinet_style": "Fluted Teak Wood and Matte Lacquer",
            "cabinet_color": "Rich Natural Teak wood grain with sage green accents",
            "countertop_material": "Granite / Quartzite",
            "countertop_finish": "Leathered Black Pearl or Taj Mahal Quartzite",
            "backsplash": "Handcrafted terracotta or zellige tiles with geometric brass trim",
            "fixtures_hardware": "Antique brass / warm copper fixtures",
            "palette": ["#B3541E", "#3A506B", "#F5EBE0", "#DDBEA9"],
        },
        "minimalist": {
            "wall_paint": "Pure Warm White (Benjamin Moore Chantilly Lace)",
            "flooring_type": "Microcement / Seamless Engineered Light Ash",
            "flooring_finish": "Seamless low-sheen monolithic light grey microcement",
            "cabinet_style": "Handleless Push-to-Open J-Pull",
            "cabinet_color": "Monochromatic warm chalk white with integrated finger channels",
            "countertop_material": "Sintered Stone (Dekton / Neolith)",
            "countertop_finish": "Ultra-compact matte concrete grey 12mm profile",
            "backsplash": "Monolithic continuation of sintered stone countertop",
            "fixtures_hardware": "Concealed hardware with matte black architectural tapware",
            "palette": ["#FFFFFF", "#F0F0F0", "#C8C8C8", "#222222"],
        },
        "farmhouse": {
            "wall_paint": "Soft Linen White (Sherwin-Williams Dover White)",
            "flooring_type": "Wide-Plank White Oak",
            "flooring_finish": "Wire-brushed 7.5-inch European White Oak with matte polyurethane",
            "cabinet_style": "Classic Shaker (5-piece)",
            "cabinet_color": "Crisp White with a deep Navy or Sage Green island",
            "countertop_material": "Honed Carrara Marble or Soapstone",
            "countertop_finish": "Honed matte soft grey marble with eased edge",
            "backsplash": "Handcrafted glazed white subway tile with subtle wavy glaze",
            "fixtures_hardware": "Oil-rubbed bronze cup pulls and bridge faucet with apron sink",
            "palette": ["#1D3557", "#457B9D", "#F1FAEE", "#E63946"],
        },
    }

    profile = style_profiles.get(clean_style, style_profiles["modern"])

    return DesignState(
        style=style,
        color_palette=profile["palette"],
        wall_paint=profile["wall_paint"],
        flooring_type=profile["flooring_type"],
        flooring_finish=profile["flooring_finish"],
        cabinet_style=profile["cabinet_style"],
        cabinet_color=profile["cabinet_color"],
        countertop_material=profile["countertop_material"],
        countertop_finish=profile["countertop_finish"],
        backsplash=profile["backsplash"],
        fixtures_hardware=profile["fixtures_hardware"],
        target_budget=target_budget,
        currency=currency,
        user_notes=user_notes,
    )


async def apply_conversational_design_edit(
    current_state: DesignState,
    user_instruction: str,
    project_id: str,
    current_version: int = 1,
) -> Tuple[DesignState, DesignVersion, str]:
    """Applies a non-destructive edit to the design state using Gemini reasoning.
    
    Parses the user's conversational intent, modifies ONLY the specified attributes,
    and returns the new state, the version record, and an explanatory reply.
    """
    client = tools.get_genai_client()
    
    # Define state fields that can be updated
    editable_fields = [
        "style", "wall_paint", "flooring_type", "flooring_finish",
        "cabinet_style", "cabinet_color", "countertop_material",
        "countertop_finish", "backsplash", "fixtures_hardware",
        "target_budget"
    ]

    current_dict = current_state.model_dump()

    prompt = f"""You are the Principal AI Interior Design Architect.
A homeowner has requested an edit to their current renovation design state.

CURRENT DESIGN STATE:
{json.dumps(current_dict, indent=2)}

USER EDIT REQUEST:
"{user_instruction}"

YOUR TASK:
1. Detect which specific design attributes the user wants to change.
2. Update ONLY the attributes mentioned or directly implied. PRESERVE every other decision intact!
   - Example: If the user says "Make the cabinets sage green", update "cabinet_color" to "Sage Green" or "Matte Sage Green Shaker/Slab", but keep countertop, flooring, and wall paint completely unchanged.
   - Example: If the user says "Change countertop to Taj Mahal Quartzite", change only "countertop_material" and "countertop_finish".
   - Example: If the user says "Switch style to Minimalist Japandi", update "style", "wall_paint", and "color_palette" while preserving room layout.
3. Formulate a concise change summary (1 sentence).
4. List the exact field names that were modified.
5. Provide a helpful, professional explanation (2-3 sentences) detailing why this refined selection coordinates harmoniously with the preserved elements.

RETURN STRICT JSON matching this format:
{{
  "updated_fields": {{
    "cabinet_color": "Matte Sage Green with brass bar pulls"
  }},
  "modified_field_names": ["cabinet_color"],
  "change_summary": "Updated cabinetry finish to Matte Sage Green while preserving Calacatta quartz counters and white oak floors.",
  "designer_rationale": "Sage green introduces an organic, calming tone that pairs gracefully with the warm veining of your existing Calacatta quartz countertops and brushed brass hardware."
}}
"""

    updated_fields = {}
    modified_names = []
    change_summary = f"Refined design: {user_instruction[:80]}"
    rationale = f"Updated design specifications per your request: '{user_instruction}'."

    if client:
        for model_candidate in ["gemini-3.6-flash", "gemini-3.8-flash"]:
            try:
                response = client.models.generate_content(
                    model=model_candidate,
                    contents=prompt,
                )
                raw_json = extract_json_block(response.text or "{}")
                parsed = json.loads(raw_json)
                updated_fields = parsed.get("updated_fields", {})
                modified_names = parsed.get("modified_field_names", list(updated_fields.keys()))
                change_summary = parsed.get("change_summary", change_summary)
                rationale = parsed.get("designer_rationale", rationale)
                break
            except Exception as e:
                logger.warning("Gemini conversational edit attempt failed on %s: %s", model_candidate, e)

    # Heuristic fallback if LLM is unavailable or failed
    if not updated_fields:
        lower_req = user_instruction.lower()
        if "cabinet" in lower_req:
            updated_fields["cabinet_color"] = user_instruction
            modified_names.append("cabinet_color")
        elif "counter" in lower_req:
            updated_fields["countertop_material"] = user_instruction
            modified_names.append("countertop_material")
        elif "floor" in lower_req:
            updated_fields["flooring_type"] = user_instruction
            modified_names.append("flooring_type")
        elif "paint" in lower_req or "wall" in lower_req:
            updated_fields["wall_paint"] = user_instruction
            modified_names.append("wall_paint")
        elif "budget" in lower_req:
            # Try to extract numbers
            nums = re.findall(r"\d+", user_instruction.replace(",", ""))
            if nums:
                updated_fields["target_budget"] = float(nums[0])
                modified_names.append("target_budget")
        else:
            updated_fields["user_notes"] = user_instruction
            modified_names.append("user_notes")

    # Construct new state copy non-destructively
    new_state_dict = current_state.model_dump()
    for k, v in updated_fields.items():
        if k in new_state_dict:
            new_state_dict[k] = v

    new_state = DesignState(**new_state_dict)
    new_version_id = current_version + 1

    new_version = DesignVersion(
        version_id=new_version_id,
        project_id=project_id,
        change_summary=change_summary,
        modified_fields=modified_names,
        design_state=new_state,
        rendering_artifact_filename=f"{project_id}_v{new_version_id}.png",
    )

    return new_state, new_version, rationale


def build_grounded_rendering_prompt(
    design_state: DesignState,
    spatial_model: Optional[SpatialModel] = None,
    room_type: str = "kitchen",
) -> str:
    """Constructs a deterministic, physically grounded SLC architectural rendering brief."""
    # Camera & Lens
    camera_spec = (
        "Professional architectural interior photography, shot on Hasselblad H6D-100c with 24mm tilt-shift lens, "
        "eye-level horizontal perspective, tack-sharp edge-to-edge focus, realistic depth of field, 8K ultra-detailed."
    )

    # Lighting
    lighting_spec = (
        "Architectural natural daylighting streaming through preserved windows, soft directional fill, "
        "warm 2700K ambient recessed ceiling illumination, continuous LED under-cabinet task lighting casting subtle reflections."
    )

    # Layout Constraints & Subject
    layout_notes = []
    if spatial_model:
        if spatial_model.openings:
            for op in spatial_model.openings:
                layout_notes.append(f"Preserved {op.opening_type} on {op.wall} ({op.position})")
        if spatial_model.fixed_elements:
            for fx in spatial_model.fixed_elements:
                layout_notes.append(f"Fixed {fx.name} at {fx.location_description}")

    layout_str = "; ".join(layout_notes) if layout_notes else "Exact original window and doorway apertures strictly preserved."

    subject_spec = (
        f"A newly renovated {design_state.style.title()} {room_type.replace('_', ' ').title()}. "
        f"Cabinetry: {design_state.cabinet_style} in {design_state.cabinet_color}. "
        f"Countertops: {design_state.countertop_material} ({design_state.countertop_finish}). "
        f"Backsplash: {design_state.backsplash}. "
        f"Flooring: {design_state.flooring_type} ({design_state.flooring_finish}). "
        f"Walls: Finished in {design_state.wall_paint}. "
        f"Fixtures & Hardware: {design_state.fixtures_hardware}. "
        f"Layout Preservation Mandate: {layout_str}. "
        f"Clean, uncluttered, photorealistic, lived-in luxury, interior design magazine editorial quality."
    )

    return f"SUBJECT: {subject_spec}\nLIGHTING: {lighting_spec}\nCAMERA: {camera_spec}"
