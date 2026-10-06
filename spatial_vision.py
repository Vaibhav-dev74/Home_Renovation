"""Spatial Vision & Architectural Assessment Engine.

Upgrades visual inspection from free-form text descriptions into strongly-typed
spatial models with openings (windows/doors), utility points, structural constraints,
and explicit labeling of observed vs. inferred vs. user-provided facts.
"""

import json
import logging
import re
from typing import Optional, Dict, Any, Tuple
from pydantic import ValidationError

import tools
from models import (
    SpatialModel,
    DimensionSpec,
    Opening,
    FixedElement,
    FurnitureItem,
    FactSource,
)

logger = logging.getLogger(__name__)


def extract_json_block(text: str) -> str:
    """Extracts JSON substring from text, handling markdown code fences."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Try finding the first '{' and last '}'
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def build_fallback_spatial_model(
    room_type: str,
    square_footage: int = 180,
    dimensions_hint: Optional[str] = None,
) -> SpatialModel:
    """Constructs a deterministic, structurally sound spatial model when no image is provided or vision is offline."""
    import math

    clean_room = room_type.lower().replace(" ", "_")
    area = max(40, square_footage)
    aspect_ratio = 1.3
    width = round(math.sqrt(area / aspect_ratio), 1)
    length = round(area / width, 1)

    openings = [
        Opening(
            opening_type="window",
            wall="exterior_north",
            position="center",
            dimensions_estimate="48in W x 48in H double-hung",
            must_preserve=True,
            notes="Natural light source to preserve in layout",
        ),
        Opening(
            opening_type="door",
            wall="interior_south",
            position="right",
            dimensions_estimate="32in W x 80in H interior passageway",
            must_preserve=True,
            notes="Primary room entrance/hallway threshold",
        ),
    ]

    fixed_elements = []
    if clean_room in ["kitchen", "bathroom", "laundry_room"]:
        fixed_elements.append(
            FixedElement(
                name="sink_plumbing_rough_in",
                location_description="Under north window on exterior wall",
                source=FactSource.INFERRED,
                relocation_difficulty="HIGH",
                preserve_priority="mandatory",
            )
        )
    if clean_room == "kitchen":
        fixed_elements.append(
            FixedElement(
                name="appliance_circuits_and_gas",
                location_description="East interior wall perimeter line",
                source=FactSource.INFERRED,
                relocation_difficulty="MEDIUM",
                preserve_priority="preferred",
            )
        )

    return SpatialModel(
        room_type=room_type,
        dimensions=DimensionSpec(
            length_ft=length,
            width_ft=width,
            height_ft=9.0,
            area_sqft=float(area),
            source=FactSource.USER_PROVIDED if square_footage else FactSource.INFERRED,
            confidence=0.80 if square_footage else 0.65,
        ),
        openings=openings,
        fixed_elements=fixed_elements,
        furniture=[],
        structural_constraints=[
            "Exterior wall on North side contains critical window opening.",
            "Plumbing waste stack location dictates wet-wall fixture cluster.",
        ],
        preserve_features=[
            "Existing door frame threshold and entryway clearances.",
            "Exterior window aperture location and daylighting path.",
        ],
        observed_facts=[
            f"Room classified as {room_type.replace('_', ' ').title()}.",
            f"Baseline target footprint estimated at ~{area} sq ft.",
        ],
        inferred_facts=[
            "Ceiling height standard residential assumed at 9.0 ft.",
            "Plumbing and electrical lines follow standard residential framing bays.",
        ],
        confidence_score=0.75,
    )


async def analyze_room_spatial_image(
    image_base64: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    room_type: str = "kitchen",
    square_footage_hint: int = 180,
    user_notes: Optional[str] = None,
) -> SpatialModel:
    """Performs multimodal spatial vision analysis on a room photo or floor plan.
    
    Extracts structured openings, utility points, dimension bounds, and separates
    observed from inferred facts.
    """
    client = tools.get_genai_client()
    if not client or (not image_base64 and not image_bytes):
        logger.info("Using baseline spatial model (no client or no image provided).")
        return build_fallback_spatial_model(room_type, square_footage_hint)

    import base64
    from google.genai import types

    # Prepare image part
    try:
        raw_bytes = image_bytes
        if not raw_bytes and image_base64:
            # Strip data:image/...;base64, prefix if present
            if "," in image_base64:
                image_base64 = image_base64.split(",", 1)[1]
            raw_bytes = base64.b64decode(image_base64)

        image_part = types.Part.from_bytes(
            data=raw_bytes,
            mime_type="image/jpeg",
        )
    except Exception as e:
        logger.warning("Failed to decode uploaded image for spatial analysis: %s", e)
        return build_fallback_spatial_model(room_type, square_footage_hint)

    prompt = f"""You are a Principal Architectural Vision Specialist and Spatial Intelligence AI.
Analyze this room photograph or floor plan with architectural precision.

Target Room Type: {room_type}
Expected Square Footage Reference: {square_footage_hint} sq ft
User Notes: {user_notes or 'None'}

CRITICAL INSTRUCTIONS:
1. Identify all OPENINGS (windows, doorways, passageways) with wall orientations and positions.
2. Identify all FIXED UTILITY ELEMENTS (sink locations, drains, 240V outlets, gas lines, HVAC vents, load-bearing indicators).
3. Estimate room dimensions in feet (length, width, ceiling height, total area).
4. Strictly categorize:
   - "observed_facts": facts directly visible in the image (e.g. "Double window centered on back wall", "Single-basin stainless sink").
   - "inferred_facts": reasonable probabilistic deductions that require contractor verification (e.g. "Ceiling height approximately 9ft", "Plumbing stack likely inside west wall bay").
5. Do NOT hallucinate certainty. Flag any questionable dimension or structural wall as inferred.

Return a STRICT, RAW JSON object conforming to this schema (no extra prose outside JSON):
{{
  "room_type": "{room_type}",
  "dimensions": {{
    "length_ft": 14.5,
    "width_ft": 12.0,
    "height_ft": 9.0,
    "area_sqft": 174.0,
    "source": "inferred",
    "confidence": 0.85
  }},
  "openings": [
    {{
      "opening_type": "window",
      "wall": "exterior_north",
      "position": "center",
      "dimensions_estimate": "36in W x 48in H",
      "must_preserve": true,
      "notes": "Preserve natural light and view"
    }}
  ],
  "fixed_elements": [
    {{
      "name": "sink_rough_in",
      "location_description": "Under north window",
      "source": "observed",
      "relocation_difficulty": "HIGH",
      "preserve_priority": "mandatory"
    }}
  ],
  "furniture": [],
  "structural_constraints": [
    "Load-bearing exterior wall on north side cannot be relocated without engineer"
  ],
  "preserve_features": [
    "Existing window aperture and plumbing drain center"
  ],
  "observed_facts": [
    "Tile flooring in distressed condition",
    "L-shaped cabinet configuration"
  ],
  "inferred_facts": [
    "Supply water lines run under the perimeter floorboards",
    "Ceiling height appears standard 9ft"
  ],
  "confidence_score": 0.88
}}
"""

    models_to_try = ["gemini-3.6-flash", "gemini-3.8-flash"]
    for model_name in models_to_try:
        try:
            logger.info("Executing spatial vision analysis with model %s...", model_name)
            response = client.models.generate_content(
                model=model_name,
                contents=[image_part, prompt],
            )
            raw_text = response.text or ""
            json_str = extract_json_block(raw_text)
            data = json.loads(json_str)
            parsed_model = SpatialModel.model_validate(data)
            logger.info("Spatial model successfully generated and validated.")
            return parsed_model
        except (json.JSONDecodeError, ValidationError) as parse_err:
            logger.warning("Spatial model JSON parse failed with model %s: %s", model_name, parse_err)
            continue
        except Exception as api_err:
            logger.warning("Spatial vision call failed with model %s: %s", model_name, api_err)
            continue

    logger.warning("Falling back to deterministic spatial model due to vision pipeline error.")
    return build_fallback_spatial_model(room_type, square_footage_hint)
