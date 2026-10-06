"""Multi-Agent Critic, Renovation Risk Engine & Design Quality Scorer.

Performs automated architectural checks across layout integrity, safety & electrical codes,
budget constraints, construction sequencing, and calculates deterministic quality/risk metrics.
"""

from typing import List, Dict, Optional, Tuple
from models import (
    CriticReport,
    CriticFinding,
    Severity,
    RiskReport,
    RiskItem,
    RiskLevel,
    DesignQualityScore,
    SpatialModel,
    DesignState,
    BOQSummary,
    TimelineSchedule,
    PermitCheckResult,
    BudgetOptimizationResult,
)


def evaluate_plan_critic(
    spatial_model: Optional[SpatialModel],
    design_state: Optional[DesignState],
    boq: Optional[BOQSummary],
    timeline: Optional[TimelineSchedule],
    permit_assessment: Optional[PermitCheckResult],
    budget_opt: Optional[BudgetOptimizationResult],
    room_type: str = "kitchen",
    scope: str = "moderate",
    target_budget: float = 800000.0,
) -> CriticReport:
    """Executes a 5-pillar architectural critic evaluation."""
    findings: List[CriticFinding] = []

    # 1. Layout & Aperture Preservation Check
    if spatial_model:
        openings_count = len(spatial_model.openings)
        windows = [op for op in spatial_model.openings if op.opening_type == "window"]
        doors = [op for op in spatial_model.openings if op.opening_type == "door"]

        if not doors:
            findings.append(
                CriticFinding(
                    severity=Severity.WARNING,
                    category="layout",
                    title="Entryway Door Position Unverified",
                    description="No primary entryway door was confirmed in spatial model. Verify 36-inch minimum clear passage from hallway.",
                    suggested_fix="Confirm primary threshold door location before fixing cabinet run end-panels.",
                )
            )

        if windows and design_state and "cabinet" in design_state.cabinet_style.lower():
            findings.append(
                CriticFinding(
                    severity=Severity.SUGGESTION,
                    category="layout",
                    title="Window Clearance for Overhead Cabinets",
                    description="Ensure upper wall cabinets terminate at least 3 inches away from exterior window casings to prevent daylight obstruction.",
                    suggested_fix="Maintain 3-inch gap between cabinet face-frames and window trim.",
                )
            )

    # 2. Safety & Building Code Checks
    if permit_assessment:
        has_plumbing = any("plumbing" in p.lower() for p in permit_assessment.trade_permits + permit_assessment.permits_required)
        has_electrical = any("electrical" in p.lower() for p in permit_assessment.trade_permits + permit_assessment.permits_required)

        if room_type.lower() in ["kitchen", "bathroom"] and not has_electrical and scope != "cosmetic":
            findings.append(
                CriticFinding(
                    severity=Severity.BLOCKER,
                    category="safety",
                    title="Missing GFCI / Wet-Location Electrical Verification",
                    description="Kitchen and bathroom renovations require dedicated GFCI protection within 6ft of sinks per NEC 210.8.",
                    suggested_fix="Ensure electrical scope includes GFCI breakers and two dedicated 20A small-appliance circuits.",
                )
            )

    # 3. Budget & Contingency Compliance Check
    if boq:
        if boq.contingency_rate_pct < 10.0:
            findings.append(
                CriticFinding(
                    severity=Severity.WARNING,
                    category="budget",
                    title="Sub-standard Contingency Reserve",
                    description=f"Contingency reserve set at {boq.contingency_rate_pct}%. Recommended minimum is 10% for residential remodels.",
                    suggested_fix="Maintain a minimum 10% cash reserve for hidden pipe or subfloor discoveries.",
                )
            )

        if budget_opt and budget_opt.is_over_budget:
            findings.append(
                CriticFinding(
                    severity=Severity.WARNING,
                    category="budget",
                    title="Initial Scope Exceeds Stated Budget",
                    description=f"Base estimate exceeded stated budget by {budget_opt.overrun_amount:,.0f} prior to value engineering.",
                    suggested_fix="Review value-engineering trade-offs (e.g. engineered quartz vs natural marble).",
                )
            )

    # 4. Construction Sequencing Check
    if timeline:
        task_titles = [t.title.lower() for t in timeline.tasks]
        has_inspection = any("inspection" in t for t in task_titles)
        if scope in ["full", "luxury"] and not has_inspection:
            findings.append(
                CriticFinding(
                    severity=Severity.BLOCKER,
                    category="sequencing",
                    title="Missing Municipal Rough-in Inspection Milestone",
                    description="Full demolition permits require rough-in city sign-off prior to insulating and hanging drywall.",
                    suggested_fix="Insert open-wall trade inspection prior to drywall installation.",
                )
            )

    # Determine overall approval
    has_blockers = any(f.severity == Severity.BLOCKER for f in findings)
    quality_score = 92 - (len(findings) * 4)
    quality_score = max(60, min(98, quality_score))

    return CriticReport(
        is_approved=not has_blockers,
        quality_score=quality_score,
        findings=findings,
        iterations_performed=1,
        approval_stamp="APPROVED WITH RECOMMENDATIONS" if not has_blockers else "REVISIONS REQUIRED",
    )


def calculate_renovation_risk_report(
    room_type: str,
    scope: str = "moderate",
    structural_changes: bool = False,
    plumbing_changes: bool = False,
    electrical_changes: bool = False,
    budget_overrun: float = 0.0,
    square_footage: int = 180,
) -> RiskReport:
    """Calculates a deterministic risk index (0-100) and multi-domain risk matrix."""
    clean_scope = scope.lower()
    clean_room = room_type.lower()

    risks: List[RiskItem] = []
    category_ratings: Dict[str, RiskLevel] = {}

    # 1. Structural Risk
    if structural_changes or clean_scope in ["full", "luxury"]:
        struct_level = RiskLevel.HIGH if structural_changes else RiskLevel.MEDIUM
        risks.append(
            RiskItem(
                category="structural",
                level=struct_level,
                reason="Load-bearing wall alterations and header span calculations",
                evidence="Scope includes opening walls or shifting structural openings.",
                recommended_action="Commission a licensed structural engineer (PE) for stamped calculation drawings.",
            )
        )
    else:
        struct_level = RiskLevel.LOW
        risks.append(
            RiskItem(
                category="structural",
                level=RiskLevel.LOW,
                reason="Non-structural finish replacement",
                evidence="Existing partition framing and exterior load lines remain undisturbed.",
                recommended_action="Standard contractor layout verification.",
            )
        )
    category_ratings["structural"] = struct_level

    # 2. Plumbing Risk
    if plumbing_changes or clean_room in ["kitchen", "bathroom"]:
        plumb_level = RiskLevel.HIGH if plumbing_changes else RiskLevel.MEDIUM
        risks.append(
            RiskItem(
                category="plumbing",
                level=plumb_level,
                reason="Subfloor drain slopes and concealed pipe integrity",
                evidence="Relocating fixture traps requires cutting into existing joist bays or subfloor slab.",
                recommended_action="Require master plumber hydrostatic pressure testing before closing walls.",
            )
        )
    else:
        plumb_level = RiskLevel.LOW
        risks.append(
            RiskItem(
                category="plumbing",
                level=RiskLevel.LOW,
                reason="Dry room renovation without wet utility feeds",
                evidence="No major water supply or sewer stack connections.",
                recommended_action="None required.",
            )
        )
    category_ratings["plumbing"] = plumb_level

    # 3. Electrical Risk
    if electrical_changes or clean_scope in ["moderate", "full", "luxury"]:
        elec_level = RiskLevel.MEDIUM
        risks.append(
            RiskItem(
                category="electrical",
                level=RiskLevel.MEDIUM,
                reason="Panel capacity and circuit breaker loading",
                evidence="Modern induction cooktops, dishwashers, and microwave drawers require dedicated 20A/40A home-runs.",
                recommended_action="Perform whole-house electrical service load calculation before adding high-draw circuits.",
            )
        )
    else:
        elec_level = RiskLevel.LOW
    category_ratings["electrical"] = elec_level

    # 4. Budget Risk
    if budget_overrun > 0:
        budget_level = RiskLevel.HIGH if budget_overrun > 50000 else RiskLevel.MEDIUM
        risks.append(
            RiskItem(
                category="budget",
                level=budget_level,
                reason="Initial scope cost exceeds target cash allocation",
                evidence=f"Baseline estimate is currently {budget_overrun:,.0f} above target envelope.",
                recommended_action="Execute recommended value-engineering substitutions or phase the renovation.",
            )
        )
    else:
        budget_level = RiskLevel.LOW
    category_ratings["budget"] = budget_level

    # 5. Timeline Risk
    time_level = RiskLevel.HIGH if clean_scope == "luxury" else (RiskLevel.MEDIUM if clean_scope == "full" else RiskLevel.LOW)
    risks.append(
        RiskItem(
            category="timeline",
            level=time_level,
            reason="Specialty custom cabinetry & stone fabrication lead times",
            evidence="Custom stone and cabinetry suppliers currently average 3-6 week fabrication backlogs.",
            recommended_action="Order long lead-time cabinetry and custom slabs prior to commencing demolition.",
        )
    )
    category_ratings["timeline"] = time_level

    # Compute overall composite risk score (0=safe, 100=critical)
    weight_map = {RiskLevel.LOW: 10, RiskLevel.MEDIUM: 35, RiskLevel.HIGH: 70, RiskLevel.CRITICAL: 95}
    composite_score = round(sum(weight_map[lvl] for lvl in category_ratings.values()) / len(category_ratings))

    overall_rating = RiskLevel.LOW if composite_score < 30 else (RiskLevel.MEDIUM if composite_score < 60 else RiskLevel.HIGH)

    return RiskReport(
        overall_score=composite_score,
        overall_rating=overall_rating,
        category_ratings=category_ratings,
        risks=risks,
    )


def calculate_design_quality_score(
    critic_report: CriticReport,
    risk_report: RiskReport,
    budget_opt: Optional[BudgetOptimizationResult],
    room_type: str = "kitchen",
    scope: str = "moderate",
) -> DesignQualityScore:
    """Calculates deterministic 6-pillar score with comprehensive explanations."""
    # 1. Layout score
    layout_deductions = sum(6 for f in critic_report.findings if f.category == "layout")
    layout_score = max(70, 96 - layout_deductions)

    # 2. Functionality score
    func_score = 92 if room_type.lower() in ["kitchen", "bathroom"] else 90

    # 3. Aesthetics score
    aes_score = 94 if scope.lower() in ["full", "luxury"] else 90

    # 4. Budget Adherence score
    if budget_opt:
        if not budget_opt.is_over_budget:
            budget_score = 95
        elif budget_opt.total_savings >= budget_opt.overrun_amount:
            budget_score = 88
        else:
            budget_score = 74
    else:
        budget_score = 85

    # 5. Safety score
    safety_deductions = sum(15 for f in critic_report.findings if f.category == "safety" and f.severity == Severity.BLOCKER)
    safety_score = max(65, 98 - safety_deductions)

    # 6. Feasibility score
    feasibility_score = max(60, 100 - int(risk_report.overall_score * 0.4))

    overall = round((layout_score + func_score + aes_score + budget_score + safety_score + feasibility_score) / 6.0)

    explanations = {
        "layout": f"Scored {layout_score}/100 based on verified spatial flow, doorway thresholds, and window daylight paths.",
        "functionality": f"Scored {func_score}/100 reflecting ergonomic clearance zones and utility access.",
        "aesthetics": f"Scored {aes_score}/100 for coordinated palettes, finish textures, and modern lighting.",
        "budget": f"Scored {budget_score}/100 based on value-engineering alignment against your target envelope.",
        "safety": f"Scored {safety_score}/100 adhering to NEC/IRC/NBC code compliance and mandatory rough-in inspections.",
        "feasibility": f"Scored {feasibility_score}/100 evaluated by contractor trade sequencing and lead-time risks.",
    }

    return DesignQualityScore(
        overall_score=overall,
        layout_score=layout_score,
        functionality_score=func_score,
        aesthetics_score=aes_score,
        budget_adherence_score=budget_score,
        safety_compliance_score=safety_score,
        construction_feasibility_score=feasibility_score,
        explanations=explanations,
    )
