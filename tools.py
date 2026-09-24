"""Tools for AI Home Renovation Planner.

Provides multimodal generation, rendering edits, version tracking,
artifact management, budget/cost calculations, and regulatory checks.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from google import genai
from google.genai import types
from google.adk.tools import ToolContext

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# API Client Helper
# ============================================================================

def get_genai_client() -> Optional[genai.Client]:
    """Retrieve an authenticated Google GenAI client.
    
    Checks GOOGLE_API_KEY and GEMINI_API_KEY environment variables.
    Returns None if neither key is configured.
    """
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


# ============================================================================
# Helper Functions for Asset Version & Artifact Management
# ============================================================================

def get_next_version_number(tool_context: ToolContext, asset_name: str) -> int:
    """Get the next version number for a given asset name."""
    asset_versions = tool_context.state.get("asset_versions", {})
    current_version = asset_versions.get(asset_name, 0)
    return current_version + 1


def update_asset_version(
    tool_context: ToolContext,
    asset_name: str,
    version: int,
    filename: str,
) -> None:
    """Update version tracking in the session state for an asset."""
    if "asset_versions" not in tool_context.state:
        tool_context.state["asset_versions"] = {}
    if "asset_filenames" not in tool_context.state:
        tool_context.state["asset_filenames"] = {}

    tool_context.state["asset_versions"][asset_name] = version
    tool_context.state["asset_filenames"][asset_name] = filename

    # Maintain chronological version history
    history_key = f"{asset_name}_history"
    if history_key not in tool_context.state:
        tool_context.state[history_key] = []
    tool_context.state[history_key].append({"version": version, "filename": filename})


def create_versioned_filename(asset_name: str, version: int, ext: str = "png") -> str:
    """Create a standardized versioned filename for an asset."""
    clean_name = asset_name.strip().replace(" ", "_").lower()
    return f"{clean_name}_v{version}.{ext}"


def get_asset_versions_info(tool_context: ToolContext) -> str:
    """Get human-readable summary of all generated renderings in session."""
    asset_versions = tool_context.state.get("asset_versions", {})
    if not asset_versions:
        return "No renovation renderings have been created in this session yet."

    lines = ["Session Renovation Renderings:"]
    for asset_name, current_ver in asset_versions.items():
        history = tool_context.state.get(f"{asset_name}_history", [])
        latest_file = tool_context.state.get("asset_filenames", {}).get(asset_name, "Unknown")
        lines.append(f"  - {asset_name}: {len(history)} version(s) (latest: v{current_ver}, filename: {latest_file})")

    return "\n".join(lines)


def get_reference_images_info(tool_context: ToolContext) -> str:
    """Get human-readable summary of all reference images uploaded in session."""
    reference_images = tool_context.state.get("reference_images", {})
    uploaded_images = tool_context.state.get("uploaded_images", {})
    all_refs = {**reference_images, **uploaded_images}

    if not all_refs:
        return "No reference images (room photos or inspiration) uploaded in this session yet."

    lines = ["Available Reference Images:"]
    for filename, info in all_refs.items():
        img_type = info.get("type", "reference") if isinstance(info, dict) else "reference"
        lines.append(f"  - {filename} ({img_type})")

    return "\n".join(lines)


async def load_reference_image(tool_context: ToolContext, filename: str):
    """Load a reference image artifact by filename."""
    try:
        loaded_part = await tool_context.load_artifact(filename)
        if loaded_part:
            logger.info(f"Successfully loaded reference artifact: {filename}")
            return loaded_part
        logger.warning(f"Reference artifact not found: {filename}")
        return None
    except Exception as e:
        logger.error(f"Error loading reference image {filename}: {e}")
        return None


def get_latest_reference_image_filename(tool_context: ToolContext) -> Optional[str]:
    """Get the filename of the most recently uploaded reference image."""
    return tool_context.state.get("latest_reference_image") or tool_context.state.get("current_room_artifact")


# ============================================================================
# Pydantic Input Schemas
# ============================================================================

class GenerateRenovationRenderingInput(BaseModel):
    prompt: str = Field(
        ...,
        description="A detailed description of the renovated space using the SLC (Subject, Lighting, Camera) formula.",
    )
    aspect_ratio: str = Field(
        default="16:9",
        description="The desired aspect ratio: '16:9', '4:3', or '1:1'. Default is '16:9'.",
    )
    asset_name: str = Field(
        default="renovation_rendering",
        description="Base name for the rendering artifact (e.g., 'kitchen_modern_farmhouse').",
    )
    current_room_photo: Optional[str] = Field(
        default=None,
        description="Optional artifact filename of current room photo to preserve layout.",
    )
    inspiration_image: Optional[str] = Field(
        default=None,
        description="Optional artifact filename of inspiration image, or 'latest'.",
    )


class EditRenovationRenderingInput(BaseModel):
    prompt: str = Field(
        ...,
        description="Specific refinement instruction (e.g., 'Change cabinets from white to sage green, keep layout identical').",
    )
    artifact_filename: Optional[str] = Field(
        default=None,
        description="Filename of the existing rendering artifact to edit. If omitted, uses the most recently generated rendering.",
    )
    asset_name: Optional[str] = Field(
        default=None,
        description="Optional asset name for the new version. If omitted, inherits previous asset name.",
    )
    reference_image_filename: Optional[str] = Field(
        default=None,
        description="Optional reference image artifact filename to guide the edit.",
    )


class CheckRenovationPermitsInput(BaseModel):
    room_type: str = Field(
        ...,
        description="Room being renovated: 'kitchen', 'bathroom', 'basement', 'bedroom', 'living_room', 'outdoor_patio'.",
    )
    scope: str = Field(
        default="moderate",
        description="Scope of renovation: 'cosmetic', 'moderate', 'full', 'luxury'.",
    )
    structural_changes: bool = Field(
        default=False,
        description="True if removing load-bearing walls, adding windows/doors, or expanding footprint.",
    )
    plumbing_changes: bool = Field(
        default=False,
        description="True if moving or adding water lines, drains, or sewer connections.",
    )
    electrical_changes: bool = Field(
        default=False,
        description="True if adding new circuits, heavy appliance lines (240V), or sub-panels.",
    )


class RecommendMaterialsInput(BaseModel):
    room_type: str = Field(
        ...,
        description="Room type: 'kitchen', 'bathroom', 'living_room', 'bedroom', 'basement'.",
    )
    style: str = Field(
        default="modern",
        description="Aesthetic style: 'modern', 'farmhouse', 'minimalist', 'industrial', 'traditional', 'scandinavian'.",
    )
    budget_tier: str = Field(
        default="moderate",
        description="Budget tier: 'budget_friendly', 'moderate', 'luxury'.",
    )


# ============================================================================
# Rendering & Editing Tools
# ============================================================================

async def generate_renovation_rendering(
    tool_context: ToolContext,
    inputs: GenerateRenovationRenderingInput,
) -> str:
    """Generates a photorealistic renovation rendering and saves it as an artifact."""
    if isinstance(inputs, dict):
        inputs = GenerateRenovationRenderingInput(**inputs)

    client = get_genai_client()
    if not client:
        return (
            "Image generation skipped: No valid GOOGLE_API_KEY or GEMINI_API_KEY found in environment or .env file.\n"
            "Please configure your Gemini API key in `.env` to enable AI photorealistic renderings."
        )

    try:
        # Load any reference images
        reference_images = []
        if inputs.current_room_photo:
            part = await load_reference_image(tool_context, inputs.current_room_photo)
            if part:
                reference_images.append(part)

        if inputs.inspiration_image:
            insp_filename = (
                get_latest_reference_image_filename(tool_context)
                if inputs.inspiration_image == "latest"
                else inputs.inspiration_image
            )
            if insp_filename:
                part = await load_reference_image(tool_context, insp_filename)
                if part:
                    reference_images.append(part)

        # Enhance prompt for photorealism using text model
        enhancement_prompt = (
            f"You are an expert architectural visualization prompt engineer.\n"
            f"Convert this interior renovation concept into a photorealistic generation prompt.\n"
            f"Requirements:\n"
            f"- Use SLC formula: Subject (exact textures, materials, colors), Lighting (natural diffused, warm LEDs), Camera (DSLR, wide-angle interior, 8K HDR, Architectural Digest quality).\n"
            f"- Emphasize exact preservation of room layout, window positions, and doors.\n"
            f"- Target aspect ratio: {inputs.aspect_ratio}\n\n"
            f"Original Concept: {inputs.prompt}"
        )

        try:
            prompt_res = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=enhancement_prompt,
            )
            refined_prompt = getattr(prompt_res, "text", None) or inputs.prompt
        except Exception:
            refined_prompt = inputs.prompt

        logger.info(f"Refined rendering prompt: {refined_prompt[:120]}...")

        # Determine output filename
        version = get_next_version_number(tool_context, inputs.asset_name)
        filename = create_versioned_filename(inputs.asset_name, version)

        # Build contents
        content_parts = [types.Part.from_text(text=refined_prompt)]
        content_parts.extend(reference_images)
        contents = [types.Content(role="user", parts=content_parts)]

        # Supported image-capable models with fallback
        image_models = ["gemini-3.1-flash-image", "gemini-2.5-flash-image", "gemini-3-pro-image-preview"]
        saved_success = False

        for model_candidate in image_models:
            try:
                logger.info(f"Attempting image generation with model: {model_candidate}")
                response = client.models.generate_content(
                    model=model_candidate,
                    contents=contents,
                )

                if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        inline_data = getattr(part, "inline_data", None)
                        if inline_data and getattr(inline_data, "data", None):
                            image_part = types.Part(inline_data=inline_data)
                            saved_ver = await tool_context.save_artifact(
                                filename=filename,
                                artifact=image_part,
                            )
                            update_asset_version(tool_context, inputs.asset_name, saved_ver, filename)
                            tool_context.state["last_generated_rendering"] = filename
                            tool_context.state["current_asset_name"] = inputs.asset_name
                            saved_success = True
                            return (
                                f"Renovation rendering successfully generated and saved!\n\n"
                                f"- Artifact Name: {filename}\n"
                                f"- Version: v{saved_ver}\n"
                                f"- Asset: {inputs.asset_name}\n"
                                f"- Aspect Ratio: {inputs.aspect_ratio}\n\n"
                                f"The photorealistic rendering has been stored in your session artifacts panel."
                            )
            except Exception as model_err:
                logger.warning(f"Model {model_candidate} generation attempt failed: {model_err}")
                continue

        if not saved_success:
            return (
                f"Rendering brief compiled successfully for '{inputs.asset_name}' (v{version}).\n"
                f"SLC Prompt: {refined_prompt}\n"
                f"(Note: Direct image synthesis requires active Gemini Multimodal Image API access on your API key)."
            )

    except Exception as e:
        logger.error(f"Error in generate_renovation_rendering: {e}")
        return f"Error generating rendering: {e}"


async def edit_renovation_rendering(
    tool_context: ToolContext,
    inputs: EditRenovationRenderingInput,
) -> str:
    """Edits an existing renovation rendering artifact based on refinement instructions."""
    if isinstance(inputs, dict):
        inputs = EditRenovationRenderingInput(**inputs)

    client = get_genai_client()
    if not client:
        return "Image editing skipped: No valid GOOGLE_API_KEY or GEMINI_API_KEY found in environment or .env file."

    try:
        # Resolve target filename
        filename = inputs.artifact_filename or tool_context.state.get("last_generated_rendering")
        if not filename:
            available = get_asset_versions_info(tool_context)
            return (
                f"No existing rendering artifact specified and none found in active session.\n\n"
                f"{available}\n\n"
                f"Please generate an initial rendering before applying edits."
            )

        # Load existing image artifact
        existing_image_part = await load_reference_image(tool_context, filename)
        if not existing_image_part:
            return f"Could not load artifact '{filename}'. Please verify the filename with list_renovation_renderings."

        # Determine asset name and next version
        asset_name = (
            inputs.asset_name
            or tool_context.state.get("current_asset_name")
            or filename.split("_v")[0].replace(".png", "")
        )
        new_version = get_next_version_number(tool_context, asset_name)
        new_filename = create_versioned_filename(asset_name, new_version)

        # Build edit request
        content_parts = [
            existing_image_part,
            types.Part.from_text(
                text=(
                    f"Perform this precise interior design refinement while preserving everything else:\n"
                    f"{inputs.prompt}\n"
                    f"Keep architectural layout, camera angle, and untouched elements strictly unchanged."
                )
            ),
        ]

        if inputs.reference_image_filename:
            ref_part = await load_reference_image(tool_context, inputs.reference_image_filename)
            if ref_part:
                content_parts.append(ref_part)

        contents = [types.Content(role="user", parts=content_parts)]
        image_models = ["gemini-3.1-flash-image", "gemini-2.5-flash-image", "gemini-3-pro-image-preview"]

        for model_candidate in image_models:
            try:
                logger.info(f"Attempting edit with model: {model_candidate}")
                response = client.models.generate_content(
                    model=model_candidate,
                    contents=contents,
                )

                if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        inline_data = getattr(part, "inline_data", None)
                        if inline_data and getattr(inline_data, "data", None):
                            image_part = types.Part(inline_data=inline_data)
                            saved_ver = await tool_context.save_artifact(
                                filename=new_filename,
                                artifact=image_part,
                            )
                            update_asset_version(tool_context, asset_name, saved_ver, new_filename)
                            tool_context.state["last_generated_rendering"] = new_filename
                            tool_context.state["current_asset_name"] = asset_name
                            return (
                                f"Rendering successfully updated!\n\n"
                                f"- Updated Artifact: {new_filename}\n"
                                f"- Version: v{saved_ver}\n"
                                f"- Based on: {filename}\n"
                                f"- Refinement: {inputs.prompt}\n\n"
                                f"Available in session artifacts panel."
                            )
            except Exception as model_err:
                logger.warning(f"Model {model_candidate} edit failed: {model_err}")
                continue

        return (
            f"Refinement instruction logged for '{filename}' -> '{new_filename}' (v{new_version}).\n"
            f"Changes specified: {inputs.prompt}"
        )

    except Exception as e:
        logger.error(f"Error in edit_renovation_rendering: {e}")
        return f"Error editing rendering: {e}"


# ============================================================================
# Session Inventory Tools
# ============================================================================

async def list_renovation_renderings(tool_context: ToolContext) -> str:
    """Lists all renovation renderings created in this session with their versions."""
    return get_asset_versions_info(tool_context)


async def list_reference_images(tool_context: ToolContext) -> str:
    """Lists all reference images (current room photos & inspiration) uploaded in this session."""
    return get_reference_images_info(tool_context)


async def save_uploaded_image_as_artifact(
    tool_context: ToolContext,
    image_data: str,
    artifact_name: str,
    image_type: str = "current_room",
) -> str:
    """Saves an uploaded image as a named session artifact for future reference."""
    try:
        clean_name = artifact_name.strip().replace(" ", "_")
        if not clean_name.endswith(".png") and not clean_name.endswith(".jpg"):
            clean_name = f"{clean_name}.png"

        await tool_context.save_artifact(
            filename=clean_name,
            artifact=image_data,
        )

        tool_context.state.setdefault("uploaded_images", {})
        tool_context.state["uploaded_images"][clean_name] = {
            "type": image_type,
            "filename": clean_name,
        }

        if image_type == "current_room":
            tool_context.state["current_room_artifact"] = clean_name
        elif image_type == "inspiration":
            tool_context.state["inspiration_artifact"] = clean_name

        logger.info(f"Saved uploaded image as artifact: {clean_name} ({image_type})")
        return f"Image saved as artifact: '{clean_name}' (type: {image_type}). Available for layout preservation and rendering."
    except Exception as e:
        logger.error(f"Error saving uploaded image: {e}")
        return f"Error saving uploaded image: {e}"


# ============================================================================
# Agentic Domain Tools (Permits, Codes & Material Recommendations)
# ============================================================================

def check_renovation_permits(
    room_type: str,
    scope: str = "moderate",
    structural_changes: bool = False,
    plumbing_changes: bool = False,
    electrical_changes: bool = False,
) -> str:
    """Checks permit and building code requirements for a renovation plan.
    
    Args:
        room_type: Room being renovated (kitchen, bathroom, basement, etc.)
        scope: Renovation scope (cosmetic, moderate, full, luxury)
        structural_changes: True if moving walls, doors, or windows
        plumbing_changes: True if relocating pipes, drains, or supply lines
        electrical_changes: True if adding circuits, sub-panels, or high-draw appliances
        
    Returns:
        Structured guidance on required building permits, inspection milestones, and safety codes.
    """
    room = room_type.lower().replace(" ", "_")
    scope_lvl = scope.lower()

    required_permits = []
    inspections = []
    codes = []

    # General scope check
    if scope_lvl in ["full", "luxury"] or structural_changes:
        required_permits.append("Building / Structural Permit: Mandatory for load-bearing modifications, header alterations, and room layout reconfigurations.")
        inspections.append("Framing & Structural Rough-in Inspection (before drywall)")

    if plumbing_changes or (room in ["kitchen", "bathroom", "laundry_room"] and scope_lvl in ["moderate", "full", "luxury"]):
        required_permits.append("Plumbing Permit: Required for rerouting waste stacks, supply lines, or moving sinks/showers/toilets.")
        inspections.append("Plumbing Rough-in & Pressure Test Inspection")
        codes.append("Anti-scald valves required on showers (ASSE 1016)")
        codes.append("Proper drain slope (min 1/4 inch per foot)")

    if electrical_changes or (room in ["kitchen", "bathroom"] and scope_lvl in ["moderate", "full", "luxury"]):
        required_permits.append("Electrical Permit: Required for dedicated 20A small-appliance circuits, GFCI/AFCI protection, and lighting relocations.")
        inspections.append("Electrical Rough-in Inspection (prior to insulation/drywall)")
        inspections.append("Final Electrical Inspection (receptacle testing)")
        codes.append("NEC 210.8: GFCI protection within 6 ft of all water sources")
        codes.append("AFCI (Arc-Fault) protection for all living areas and bedrooms")

    if room == "basement":
        codes.append("IRC R310: Emergency Egress window required for any habitable basement space")
        codes.append("Moisture & vapor barrier minimum class II on masonry exterior walls")

    if not required_permits:
        return (
            f"Permit Assessment for {scope.title()} {room_type.replace('_', ' ').title()}:\n"
            f"No Major Building Permits Typically Required: Cosmetic renovations (painting, cabinet refacing, surface flooring, tile backsplash, fixture swaps in place) "
            f"do not require municipal permits in most jurisdictions.\n"
            f"Tip: Check local HOA rules regarding work hours and disposal container placement."
        )

    output = [
        f"Permit & Building Code Assessment ({scope.title()} {room_type.replace('_', ' ').title()}):",
        "\nMandatory Permits Identified:",
    ]
    for p in required_permits:
        output.append(f"  - {p}")

    output.append("\nKey Building Codes Applicable:")
    for c in (codes or ["Standard local residential building code (IRC 2021/2024) applies."]):
        output.append(f"  - {c}")

    output.append("\nRequired Inspection Milestones:")
    for ins in (inspections + ["Final Building & Occupancy Inspection"]):
        output.append(f"  - {ins}")

    output.append("\nContractor Note: Ensure licensed and insured trades pull their respective trade permits.")
    return "\n".join(output)


def recommend_materials_and_finishes(
    room_type: str,
    style: str = "modern",
    budget_tier: str = "moderate",
) -> str:
    """Recommends durable materials, color schemes, and finishes for a room.
    
    Args:
        room_type: Room type (kitchen, bathroom, living_room, bedroom, basement)
        style: Aesthetic preference (modern, farmhouse, minimalist, industrial, scandinavian)
        budget_tier: Budget tier (budget_friendly, moderate, luxury)
        
    Returns:
        Curated material selections, maintenance notes, and price ranges.
    """
    room = room_type.lower().replace(" ", "_")
    tier = budget_tier.lower()

    catalog = {
        "kitchen": {
            "budget_friendly": {
                "countertops": "Butcher Block ($30-50/sq ft) or Wilsonart High-Definition Laminate ($25-40/sq ft)",
                "cabinetry": "Refinished existing cabinets with Sherwin-Williams Emerald Urethane Trim Enamel + matte black bar pulls",
                "flooring": "Waterproof Luxury Vinyl Plank (LVP, 20 mil wear layer, $3-5/sq ft)",
                "backsplash": "Classic White 3x6 Subway Tile with light grey grout ($4-8/sq ft installed)",
            },
            "moderate": {
                "countertops": "Engineered Quartz (e.g., Silestone or Cambria Calacatta Gold, $70-110/sq ft)",
                "cabinetry": "Semi-custom Painted Shaker Cabinets (Solid maple frames, soft-close hardware)",
                "flooring": "Engineered White Oak Hardwood or 12x24 Rectified Porcelain Tile ($8-14/sq ft installed)",
                "backsplash": "Zellige Handcrafted Ceramic Tile or Herringbone Marble ($15-25/sq ft installed)",
            },
            "luxury": {
                "countertops": "Honed Carrara Marble or Quartzite (Taj Mahal, bookmatched slabs, $130-220/sq ft)",
                "cabinetry": "Full Custom Inset Cabinets with walnut interior boxes and integrated LED channel lighting",
                "flooring": "Wide-Plank European White Oak (5/8\" thickness, UV oil finish, $18-28/sq ft)",
                "backsplash": "Continuous Full-Height Quartzite / Marble slab backsplash matching countertops",
            },
        },
        "bathroom": {
            "budget_friendly": {
                "vanity": "Pre-fabricated 36\" Vanity Combo with cultured marble top ($350-600)",
                "shower_tub": "Prefabricated Acrylic Tub Surround or Ceramic subway tile surround ($600-1,200)",
                "flooring": "Sheet Vinyl or Glazed Ceramic Hexagon Tile ($4-7/sq ft)",
                "fixtures": "Brushed Nickel Moen or Delta single-hole faucet and shower kit",
            },
            "moderate": {
                "vanity": "Floating or Furniture-style Wood Vanity with Quartz top and undermount sink ($800-1,600)",
                "shower_tub": "Walk-in Shower with frameless 3/8\" glass door, porcelain tile & niche ($2,500-5,000)",
                "flooring": "Heated 12x24 Matte Porcelain Tile with Ditra-Heat membrane ($12-18/sq ft)",
                "fixtures": "Kohler Purist or Delta Champagne Bronze thermostatic fixtures",
            },
            "luxury": {
                "vanity": "Custom Floating Double Vanity with Fluted Oak details and Calacatta Marble top ($3,000+)",
                "shower_tub": "Wet Room concept with freestanding resin soaking tub and ceiling rainfall head ($8,000+)",
                "flooring": "Radiant-heated Honed Natural Stone or Large Format Porcelain slabs ($22-35/sq ft)",
                "fixtures": "Waterworks or Brizo Luxury brass wall-mount fixtures with smart thermostatic valve",
            },
        },
    }

    # Fallback to living room / general living space
    general_catalog = {
        "budget_friendly": {
            "walls": "Sherwin-Williams SuperPaint in Alabaster (SW 7008) or Agreeable Gray (SW 7029)",
            "flooring": "Click-lock Luxury Vinyl Plank (rigid core, $3-5/sq ft)",
            "lighting": "Flush-mount LED disc lights with selectable 2700K-3000K warm white",
        },
        "moderate": {
            "walls": "Benjamin Moore Regal Select in Chantilly Lace (OC-65) or Swiss Coffee",
            "flooring": "Wire-brushed Engineered Oak Flooring ($9-15/sq ft installed)",
            "lighting": "Statement modern pendant fixture + 4-inch recessed warm dimming LED downlights",
        },
        "luxury": {
            "walls": "Roman Clay / Limewash finish or Venetian Plaster accent wall",
            "flooring": "Solid Rift & Quartered White Oak laid in herringbone pattern ($20-30/sq ft)",
            "lighting": "Architectural perimeter cove lighting + designer sculptural chandelier",
        },
    }

    selected_room = catalog.get(room, general_catalog)
    tier_data = selected_room.get(tier, selected_room.get("moderate", {}))

    lines = [
        f"Material & Finish Recommendations ({style.title()} Style - {budget_tier.replace('_', ' ').title()} Tier):",
        f"Target Room: {room_type.replace('_', ' ').title()}\n",
    ]
    for category, spec in tier_data.items():
        lines.append(f"- {category.replace('_', ' ').title()}: {spec}")

    lines.append(
        "\nDesign Cohesion Tip: Stick to the 60-30-10 rule (60% dominant wall/cabinet tone, "
        "30% secondary flooring/countertop tone, 10% bold hardware and accent color)."
    )
    return "\n".join(lines)


__all__ = [
    "generate_renovation_rendering",
    "edit_renovation_rendering",
    "list_renovation_renderings",
    "list_reference_images",
    "save_uploaded_image_as_artifact",
    "check_renovation_permits",
    "recommend_materials_and_finishes",
    "get_asset_versions_info",
    "get_reference_images_info",
    "get_next_version_number",
    "update_asset_version",
    "create_versioned_filename",
    "load_reference_image",
    "get_latest_reference_image_filename",
    "GenerateRenovationRenderingInput",
    "EditRenovationRenderingInput",
    "CheckRenovationPermitsInput",
    "RecommendMaterialsInput",
]