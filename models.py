"""Domain data models and strongly-typed schemas for AI Home Renovation Intelligence Platform.

Enforces strict separation of observed vs. inferred facts, structured design state,
multi-currency budgets, BOQ line items, dependency DAG schedules, regulatory citations,
and multi-agent critic reports.
"""

from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================

class FactSource(str, Enum):
    """Source classification for architectural and spatial facts."""
    OBSERVED = "observed"              # Directly visible and verified in uploaded image
    INFERRED = "inferred"              # Deduced by AI visual model with confidence < 1.0
    USER_PROVIDED = "user_provided"    # Explicitly entered by the homeowner
    REQUIRES_VERIFICATION = "requires_verification"  # Structural/code fact needing professional check


class Currency(str, Enum):
    """Supported currency formats."""
    INR = "INR"
    USD = "USD"


class RiskLevel(str, Enum):
    """Severity level for renovation risks."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Severity(str, Enum):
    """Critic finding severity."""
    BLOCKER = "BLOCKER"
    WARNING = "WARNING"
    SUGGESTION = "SUGGESTION"


# ============================================================================
# 1. Spatial Intelligence Models
# ============================================================================

class DimensionSpec(BaseModel):
    """Room dimension estimates with explicit sourcing."""
    length_ft: float = Field(..., description="Estimated room length in feet")
    width_ft: float = Field(..., description="Estimated room width in feet")
    height_ft: float = Field(default=9.0, description="Estimated ceiling height in feet")
    area_sqft: float = Field(..., description="Calculated floor area in square feet")
    source: FactSource = Field(default=FactSource.INFERRED)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Confidence rating between 0 and 1")


class Opening(BaseModel):
    """Doors, windows, and architectural openings that must be accounted for."""
    opening_type: str = Field(..., description="'window', 'door', 'cased_opening', 'patio_slider'")
    wall: str = Field(default="unknown", description="'north', 'south', 'east', 'west', 'interior', 'exterior'")
    position: str = Field(default="center", description="'center', 'left', 'right', 'corner'")
    dimensions_estimate: Optional[str] = Field(default=None, description="e.g. '36in x 80in door' or '48in x 48in window'")
    must_preserve: bool = Field(default=True, description="Strictly preserve this opening in renovations")
    notes: Optional[str] = None


class FixedElement(BaseModel):
    """Infrastructure utility elements (plumbing, gas, load-bearing walls, electrical)."""
    name: str = Field(..., description="'sink_drain', 'gas_stub', '240v_outlet', 'hvac_vent', 'waste_stack'")
    location_description: str = Field(..., description="e.g. 'Under center window on west wall'")
    source: FactSource = Field(default=FactSource.INFERRED)
    relocation_difficulty: str = Field(default="HIGH", description="'LOW', 'MEDIUM', 'HIGH', 'STRUCTURAL_PROHIBITIVE'")
    preserve_priority: str = Field(default="mandatory", description="'mandatory', 'preferred', 'flexible'")


class FurnitureItem(BaseModel):
    """Observed furniture items currently in space."""
    name: str
    approximate_location: str
    is_removable: bool = True


class SpatialModel(BaseModel):
    """Comprehensive spatial model extracted from room images or floor plans."""
    room_type: str = Field(..., description="e.g. 'kitchen', 'bathroom', 'living_room', 'bedroom'")
    dimensions: DimensionSpec
    openings: List[Opening] = Field(default_factory=list)
    fixed_elements: List[FixedElement] = Field(default_factory=list)
    furniture: List[FurnitureItem] = Field(default_factory=list)
    structural_constraints: List[str] = Field(default_factory=list)
    preserve_features: List[str] = Field(default_factory=list)
    observed_facts: List[str] = Field(default_factory=list, description="Strictly verified visual observations")
    inferred_facts: List[str] = Field(default_factory=list, description="Probabilistic assumptions needing field verification")
    confidence_score: float = Field(default=0.85, ge=0.0, le=1.0)
    analysis_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================================
# 2. Design State & Versioning Models
# ============================================================================

class DesignState(BaseModel):
    """Persistent, granular design configuration. Updated non-destructively."""
    style: str = Field(default="modern", description="'modern', 'minimalist', 'contemporary_indian', 'farmhouse', 'industrial', 'traditional'")
    color_palette: List[str] = Field(default_factory=lambda: ["#FFFFFF", "#2B3A4A", "#C5A880", "#E0E0E0"])
    wall_paint: str = Field(default="Warm Off-White (Sherwin-Williams Alabaster)", description="Primary wall paint")
    flooring_type: str = Field(default="Porcelain Tile", description="Flooring category")
    flooring_finish: str = Field(default="Matte 24x48 rectified marble-look", description="Flooring aesthetic finish")
    cabinet_style: str = Field(default="Slab Flat-Panel", description="Cabinet door profile")
    cabinet_color: str = Field(default="Natural White Oak & Charcoal", description="Cabinet finish/color")
    countertop_material: str = Field(default="Engineered Quartz", description="Countertop stone or surface")
    countertop_finish: str = Field(default="Calacatta Gold with subtle warm veining")
    backsplash: str = Field(default="Full-height quartz slab matching countertops")
    lighting_types: List[str] = Field(default_factory=lambda: ["2700K Recessed Ceiling LEDs", "Under-cabinet LED channel lights", "Matte Black Island Pendants"])
    fixtures_hardware: str = Field(default="Brushed Brass or Matte Black pulls and gooseneck faucet")
    target_budget: float = Field(default=800000.0, description="Target budget in project currency")
    currency: Currency = Field(default=Currency.INR)
    special_constraints: List[str] = Field(default_factory=list)
    user_notes: Optional[str] = None


class DesignVersion(BaseModel):
    """A timestamped, immutable snapshot of the design state."""
    version_id: int
    project_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    change_summary: str = Field(..., description="e.g. 'Updated cabinets to sage green and hardware to brass'")
    modified_fields: List[str] = Field(default_factory=list)
    design_state: DesignState
    rendering_artifact_filename: Optional[str] = None


# ============================================================================
# 3. Material Intelligence Models
# ============================================================================

class MaterialOption(BaseModel):
    """Individual material specification with cost, durability, and maintenance."""
    name: str
    category: str
    unit: str = "sq.ft"
    unit_price: float
    currency: Currency = Currency.INR
    durability_score: int = Field(default=4, ge=1, le=5)
    maintenance_level: str = "Low"  # 'Low', 'Medium', 'High'
    aesthetic_rating: int = Field(default=5, ge=1, le=5)
    eco_friendly: bool = True
    best_for_rooms: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class MaterialRecommendation(BaseModel):
    """Categorized recommendation comparing primary vs value-engineered alternative."""
    category: str
    primary_option: MaterialOption
    alternative_option: MaterialOption
    estimated_quantity: float
    unit: str
    total_primary_cost: float
    total_alternative_cost: float
    potential_savings: float


# ============================================================================
# 4. Bill of Quantities (BOQ) Models
# ============================================================================

class BOQItem(BaseModel):
    """Single line item in the automated Bill of Quantities."""
    item_id: str
    category: str = Field(..., description="'Civil & Demolition', 'Flooring', 'Carpentry & Cabinetry', 'Plumbing', 'Electrical', 'Painting', 'Hardware'")
    item_name: str
    description: str
    quantity: float
    unit: str = Field(..., description="'sq.ft', 'running.ft', 'units', 'lump_sum', 'liters'")
    material_unit_rate: float
    labor_unit_rate: float
    material_subtotal: float
    labor_subtotal: float
    total_amount: float
    currency: Currency = Currency.INR
    is_essential: bool = True
    assumption_notes: str = ""


class BOQSummary(BaseModel):
    """Consolidated Bill of Quantities report."""
    project_id: str
    currency: Currency = Currency.INR
    items: List[BOQItem] = Field(default_factory=list)
    subtotal_materials: float
    subtotal_labor: float
    permits_and_fees: float
    contingency_rate_pct: float = 10.0
    contingency_amount: float
    grand_total: float
    calculation_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================================
# 5. Budget Optimization Models
# ============================================================================

class BudgetTradeOff(BaseModel):
    """Actionable trade-off to reduce cost to meet target budget."""
    category: str
    original_item: str
    original_cost: float
    suggested_alternative: str
    alternative_cost: float
    savings: float
    compromise_description: str
    recommendation_level: str = "HIGH"  # 'HIGH', 'MEDIUM', 'LOW'


class BudgetOptimizationResult(BaseModel):
    """Structured output of the Budget Optimization Engine."""
    target_budget: float
    original_estimate: float
    is_over_budget: bool
    overrun_amount: float
    optimized_total: float
    total_savings: float
    currency: Currency = Currency.INR
    trade_offs: List[BudgetTradeOff] = Field(default_factory=list)
    preserved_features: List[str] = Field(default_factory=list)
    summary_advice: str


# ============================================================================
# 6. Construction Timeline Models
# ============================================================================

class TimelineTask(BaseModel):
    """Single construction task in the dependency DAG."""
    task_id: str
    phase_name: str
    title: str
    description: str
    duration_days: int
    depends_on: List[str] = Field(default_factory=list, description="IDs of tasks that must complete first")
    trade_required: str = Field(..., description="'Demolition', 'Plumbing', 'Electrical', 'Tiling', 'Carpentry', 'Painting', 'General'")
    is_critical_path: bool = False
    inspection_required: bool = False


class TimelineSchedule(BaseModel):
    """Phased schedule generated from scope, room type, and trade dependencies."""
    project_id: str
    total_working_days: int
    total_calendar_weeks: int
    phases: List[str] = Field(default_factory=list)
    tasks: List[TimelineTask] = Field(default_factory=list)
    critical_path: List[str] = Field(default_factory=list)
    potential_delays: List[str] = Field(default_factory=list)


# ============================================================================
# 7. Regulatory RAG & Building Codes Models
# ============================================================================

class RegulationCitation(BaseModel):
    """Groundable legal/code citation with source attribution."""
    jurisdiction: str = Field(..., description="'Austin, TX', 'India (National)', 'Universal Baseline'")
    code_standard: str = Field(..., description="'IRC 2021', 'NEC 2023', 'NBC 2016 Part 4', 'Local Municipal AHJ'")
    section_reference: str = Field(..., description="e.g. 'IRC R310.1', 'NEC 210.8(A)(6)', 'NBC 4.3'")
    title: str
    requirement_summary: str
    verification_needed_with_ahj: bool = True
    source_document: str
    retrieval_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))


class PermitCheckResult(BaseModel):
    """Grounded permit & building code assessment."""
    location: str
    jurisdiction_detected: str
    permits_required: List[str] = Field(default_factory=list)
    trade_permits: List[str] = Field(default_factory=list)
    citations: List[RegulationCitation] = Field(default_factory=list)
    mandatory_inspections: List[str] = Field(default_factory=list)
    local_ahj_guidance: str
    legal_disclaimer: str


# ============================================================================
# 8. Multi-Agent Critic & Risk Evaluation Models
# ============================================================================

class CriticFinding(BaseModel):
    """Issue identified by the Critic Agent."""
    severity: Severity
    category: str = Field(..., description="'layout', 'budget', 'safety', 'sequencing', 'user_intent'")
    title: str
    description: str
    suggested_fix: str


class CriticReport(BaseModel):
    """Consolidated review from the Multi-Agent Critic."""
    is_approved: bool
    quality_score: int = Field(default=85, ge=0, le=100)
    findings: List[CriticFinding] = Field(default_factory=list)
    iterations_performed: int = 1
    approval_stamp: str = "VALIDATED"


class RiskItem(BaseModel):
    """Categorized risk evaluation."""
    category: str = Field(..., description="'structural', 'electrical', 'plumbing', 'budget', 'timeline', 'materials'")
    level: RiskLevel
    reason: str
    evidence: str
    recommended_action: str


class RiskReport(BaseModel):
    """Overall renovation risk score and matrix."""
    overall_score: int = Field(..., ge=0, le=100, description="Risk index (0=Safe, 100=Extreme Risk)")
    overall_rating: RiskLevel
    category_ratings: Dict[str, RiskLevel] = Field(default_factory=dict)
    risks: List[RiskItem] = Field(default_factory=list)


class DesignQualityScore(BaseModel):
    """Deterministic 6-pillar score evaluating the renovation plan."""
    overall_score: int = Field(..., ge=0, le=100)
    layout_score: int = Field(..., ge=0, le=100)
    functionality_score: int = Field(..., ge=0, le=100)
    aesthetics_score: int = Field(..., ge=0, le=100)
    budget_adherence_score: int = Field(..., ge=0, le=100)
    safety_compliance_score: int = Field(..., ge=0, le=100)
    construction_feasibility_score: int = Field(..., ge=0, le=100)
    explanations: Dict[str, str] = Field(default_factory=dict)


# ============================================================================
# 9. Top-Level Project Container
# ============================================================================

class Project(BaseModel):
    """Root project entity."""
    project_id: str
    name: str
    room_type: str = "kitchen"
    scope: str = "moderate"
    square_footage: int = 180
    location: str = "General Baseline"
    currency: Currency = Currency.INR
    target_budget: float = 800000.0
    style: str = "modern"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    current_version: int = 1
    original_image_path: Optional[str] = None
    latest_rendering_path: Optional[str] = None
    
    # Nested domain models
    spatial_model: Optional[SpatialModel] = None
    current_design: Optional[DesignState] = None
    boq: Optional[BOQSummary] = None
    budget_optimization: Optional[BudgetOptimizationResult] = None
    timeline: Optional[TimelineSchedule] = None
    permit_assessment: Optional[PermitCheckResult] = None
    critic_report: Optional[CriticReport] = None
    risk_report: Optional[RiskReport] = None
    quality_score: Optional[DesignQualityScore] = None
