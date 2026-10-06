"""Regulatory RAG & Building Code Advisory Engine.

Provides grounded legal and municipal permit advice based on an indexed corpus
of verified building regulations: International Residential Code (IRC),
National Electrical Code (NEC), National Building Code of India (NBC 2016),
and municipal Authority Having Jurisdiction (AHJ) guidelines.
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from models import PermitCheckResult, RegulationCitation

# Structured Knowledge Base of Verified Building Codes & Standards
REGULATORY_CORPUS: List[Dict[str, Any]] = [
    # ------------------------------------------------------------------------
    # 1. International Residential Code (IRC 2021/2024)
    # ------------------------------------------------------------------------
    {
        "id": "IRC-R310.1",
        "jurisdiction": "United States (General Baseline / Adopted by 49 States)",
        "code_standard": "IRC 2021/2024",
        "section_reference": "IRC R310.1",
        "title": "Emergency Escape and Rescue Openings (Egress)",
        "room_types": ["basement", "bedroom", "master_bedroom"],
        "trigger_conditions": ["basement_remodel", "adding_bedroom", "structural"],
        "requirement_summary": (
            "Basements, habitable attics, and every sleeping room must have at least one operable emergency escape opening. "
            "Minimum net clear opening of 5.7 sq ft (5.0 sq ft at grade floor), minimum clear height 24 inches, minimum clear width 20 inches, "
            "sill height not exceeding 44 inches above floor."
        ),
        "source_document": "International Code Council (ICC) Residential Code, Chapter 3",
    },
    {
        "id": "IRC-R307.1",
        "jurisdiction": "United States (General Baseline)",
        "code_standard": "IRC 2021/2024",
        "section_reference": "IRC R307.1",
        "title": "Toilet, Bath and Shower Clearances & Anti-Scald Protection",
        "room_types": ["bathroom", "master_bedroom"],
        "trigger_conditions": ["plumbing", "full", "luxury", "moderate"],
        "requirement_summary": (
            "A minimum 21-inch clearance is required in front of toilets, lavatories, and bidets to any wall or obstruction. "
            "Water closets must have a minimum 15 inches from the center of the bowl to any side wall or partition (30 inches total clearance). "
            "Showers and tub-shower valves must feature ASSE 1016 pressure-balance or thermostatic anti-scald mixing valves capped at 120°F (49°C)."
        ),
        "source_document": "International Code Council (ICC) Residential Code, Plumbing Chapter 27",
    },
    {
        "id": "IRC-P3005.4",
        "jurisdiction": "United States (General Baseline)",
        "code_standard": "IRC 2021/2024",
        "section_reference": "IRC P3005.4",
        "title": "Drainage Pipe Slope & Cleanout Access",
        "room_types": ["kitchen", "bathroom", "laundry_room"],
        "trigger_conditions": ["plumbing", "full", "structural"],
        "requirement_summary": (
            "Horizontal drainage piping of 2 inches or smaller must maintain a minimum slope of 1/4 inch per foot (2% fall). "
            "Cleanouts are required at the base of each waste stack and for changes of direction exceeding 45 degrees."
        ),
        "source_document": "International Code Council (ICC) Residential Plumbing Provisions",
    },

    # ------------------------------------------------------------------------
    # 2. National Electrical Code (NEC NFPA 70 2023)
    # ------------------------------------------------------------------------
    {
        "id": "NEC-210.8A",
        "jurisdiction": "United States & Model Code Jurisdictions",
        "code_standard": "NEC 2023 (NFPA 70)",
        "section_reference": "NEC 210.8(A)(6)",
        "title": "Ground-Fault Circuit-Interrupter (GFCI) Protection for Kitchens & Bathrooms",
        "room_types": ["kitchen", "bathroom", "outdoor_patio", "laundry_room", "basement"],
        "trigger_conditions": ["electrical", "moderate", "full", "luxury"],
        "requirement_summary": (
            "All 125-volt through 250-volt receptacles installed in kitchens, bathrooms, within 6 feet of the top inside edge of a sink basin, "
            "and in laundry areas must be equipped with GFCI Class A protection."
        ),
        "source_document": "National Fire Protection Association (NFPA) 70, Article 210",
    },
    {
        "id": "NEC-210.52B",
        "jurisdiction": "United States & Model Code Jurisdictions",
        "code_standard": "NEC 2023 (NFPA 70)",
        "section_reference": "NEC 210.52(B)(1)",
        "title": "Kitchen Small Appliance Dedicated Branch Circuits",
        "room_types": ["kitchen"],
        "trigger_conditions": ["electrical", "moderate", "full", "luxury"],
        "requirement_summary": (
            "Kitchen countertop areas must be supplied by a minimum of two 20-ampere small-appliance branch circuits. "
            "These circuits may not feed general illumination fixtures or outlets in other rooms."
        ),
        "source_document": "National Fire Protection Association (NFPA) 70, Article 210",
    },

    # ------------------------------------------------------------------------
    # 3. National Building Code of India (NBC 2016)
    # ------------------------------------------------------------------------
    {
        "id": "NBC-PART4-SEC3",
        "jurisdiction": "India (National & Municipal Corporation Baseline)",
        "code_standard": "NBC 2016 Part 4",
        "section_reference": "NBC 2016 Clause 3.4.1",
        "title": "Fire & Life Safety - Residential Escape Routes & Kitchen Ventilation",
        "room_types": ["kitchen", "living_room", "bedroom"],
        "trigger_conditions": ["structural", "full", "luxury"],
        "requirement_summary": (
            "Residential kitchens must possess dedicated natural or mechanical exhaust ventilation independent of living zones. "
            "Corridors and internal passage clearances must provide an unobstructed minimum width of 1.0 meter (3.3 ft). "
            "Balcony safety railings or parapets must maintain a minimum height of 1.2 meters from the finished floor level."
        ),
        "source_document": "Bureau of Indian Standards (BIS) SP 7: National Building Code of India 2016, Part 4",
    },
    {
        "id": "NBC-PART9-SEC1",
        "jurisdiction": "India (National & Municipal Corporation Baseline)",
        "code_standard": "NBC 2016 Part 9",
        "section_reference": "NBC 2016 Clause 5.2.3",
        "title": "Internal Drainage, Waste Separation & Soil Pipe Ventilation",
        "room_types": ["bathroom", "kitchen", "laundry_room"],
        "trigger_conditions": ["plumbing", "moderate", "full", "luxury"],
        "requirement_summary": (
            "Waste water (grey water from sinks/baths) and soil waste (black water from WCs) must run via two-pipe or ventilated single-stack systems. "
            "All water closets require an anti-siphonage P-trap or S-trap with a minimum 50mm water seal. Horizontal soil runs must maintain a minimum 1:50 gradient."
        ),
        "source_document": "Bureau of Indian Standards (BIS) SP 7: National Building Code of India 2016, Part 9",
    },
    {
        "id": "NBC-PART8-SEC1",
        "jurisdiction": "India (National & Municipal Corporation Baseline)",
        "code_standard": "NBC 2016 Part 8",
        "section_reference": "NBC 2016 Sec 1 Clause 4.1",
        "title": "Natural Lighting and Ventilation Minimum Aggregate Window Area",
        "room_types": ["bedroom", "master_bedroom", "living_room", "kitchen"],
        "trigger_conditions": ["structural", "full"],
        "requirement_summary": (
            "Every habitable room must have opening areas (windows/doors opening directly into external air or open verandah) "
            "of not less than 1/10th (10%) of the floor area for lighting and 1/20th (5%) for aggregate ventilation."
        ),
        "source_document": "Bureau of Indian Standards (BIS) SP 7: National Building Code of India 2016, Part 8",
    },
]


def detect_jurisdiction(location: str) -> Tuple[str, str]:
    """Infers jurisdictional regime (US/IRC/NEC vs India/NBC vs Universal) from user location."""
    loc = location.lower().strip()
    
    india_keywords = [
        "india", "mumbai", "delhi", "bangalore", "bengaluru", "hyderabad",
        "pune", "chennai", "kolkata", "gurugram", "gurgaon", "noida", "ahmedabad",
    ]
    for kw in india_keywords:
        if kw in loc:
            return "India (National / Municipal Authority)", "NBC 2016"

    us_state_codes = [
        "tx", "texas", "austin", "california", "ca", "ny", "new york",
        "florida", "fl", "washington", "wa", "illinois", "il", "colorado", "co",
    ]
    for kw in us_state_codes:
        if kw in loc:
            return f"United States ({location})", "IRC 2021/2024 & NEC 2023"

    if loc and loc != "general baseline":
        return f"Regional Jurisdiction: {location}", "Local Municipal Residential Code"

    return "General Residential Model Standards", "Model Building & Safety Codes"


def query_regulatory_rag(
    room_type: str,
    scope: str = "moderate",
    structural_changes: bool = False,
    plumbing_changes: bool = False,
    electrical_changes: bool = False,
    location: str = "General Baseline",
) -> PermitCheckResult:
    """Retrieves grounded citations and evaluates permit obligations for a project."""
    jurisdiction_label, primary_standard = detect_jurisdiction(location)
    is_india = "india" in jurisdiction_label.lower()
    clean_room = room_type.lower().replace(" ", "_")
    clean_scope = scope.lower()

    # Determine triggers
    triggers = [clean_scope]
    if structural_changes or clean_scope in ["full", "luxury"]:
        triggers.append("structural")
    if plumbing_changes or clean_room in ["kitchen", "bathroom", "laundry_room"]:
        triggers.append("plumbing")
    if electrical_changes or clean_room in ["kitchen", "bathroom"]:
        triggers.append("electrical")
    if clean_room == "basement":
        triggers.append("basement_remodel")

    # Document retrieval pass
    matched_citations: List[RegulationCitation] = []
    for doc in REGULATORY_CORPUS:
        # Jurisdiction filter
        doc_is_india = "india" in doc["jurisdiction"].lower()
        if is_india and not doc_is_india:
            continue
        if not is_india and doc_is_india and location.strip().lower() != "general baseline":
            continue

        # Room match
        room_match = clean_room in doc["room_types"]
        # Trigger match
        trigger_match = any(t in doc["trigger_conditions"] for t in triggers)

        if room_match and trigger_match:
            matched_citations.append(
                RegulationCitation(
                    jurisdiction=jurisdiction_label,
                    code_standard=doc["code_standard"],
                    section_reference=doc["section_reference"],
                    title=doc["title"],
                    requirement_summary=doc["requirement_summary"],
                    verification_needed_with_ahj=True,
                    source_document=doc["source_document"],
                )
            )

    # Formulate permits list
    permits_required: List[str] = []
    trade_permits: List[str] = []
    inspections: List[str] = []

    if structural_changes or clean_scope in ["full", "luxury"]:
        permits_required.append("Building / Structural Alteration Permit")
        inspections.append("Framing & Structural Rough-in Inspection (prior to insulation/drywall)")

    if plumbing_changes or (clean_room in ["kitchen", "bathroom"] and clean_scope in ["moderate", "full", "luxury"]):
        trade_permits.append("Trade Plumbing Permit (water supply line relocation & waste stack ties)")
        inspections.append("Plumbing Rough-in Pressure & Hydrostatic Test Inspection")

    if electrical_changes or (clean_room in ["kitchen", "bathroom"] and clean_scope in ["moderate", "full", "luxury"]):
        trade_permits.append("Trade Electrical Permit (sub-panel expansion & small-appliance 20A branch circuits)")
        inspections.append("Electrical Rough-in Open-Wall Inspection")
        inspections.append("Final Electrical Receptacle & AFCI/GFCI Trip Testing")

    if not permits_required and not trade_permits and clean_scope == "cosmetic":
        guidance = (
            f"Cosmetic renovations in {location} (surface tiling, cabinet refacing, wall painting, like-for-like plumbing fixture swaps) "
            f"do not require municipal building permits in most residential districts. "
            f"Verify HOA or building management rules regarding dumpster placement and contractor working hours."
        )
    else:
        guidance = (
            f"Permits must be pulled through the local {location} Building Department (AHJ) prior to commencing demolition. "
            f"Licensed and insured master trades (plumber and electrician) must pull their respective trade permits. "
            f"All rough-in inspections must pass before hanging gypsum drywall or tiling over pipe cavities."
        )

    disclaimer = (
        "LEGAL DISCLAIMER: Regulatory requirements vary across municipal jurisdictions and local amendments. "
        "This assessment provides grounded model code citations for planning purposes only and does not substitute for "
        "a formal plan review by a licensed architect, structural engineer, or your local municipal building official."
    )

    return PermitCheckResult(
        location=location,
        jurisdiction_detected=jurisdiction_label,
        permits_required=permits_required,
        trade_permits=trade_permits,
        citations=matched_citations,
        mandatory_inspections=inspections + (["Final Building & Occupancy Sign-off"] if permits_required or trade_permits else []),
        local_ahj_guidance=guidance,
        legal_disclaimer=disclaimer,
    )
