"""Budget Optimization & Material Intelligence Engine.

Computes realistic renovation estimates in INR and USD, itemizes cost drivers,
and executes value-engineering trade-offs to automatically align projects with stated budgets.
"""

import math
from typing import Dict, List, Tuple, Optional
from models import (
    Currency,
    BudgetOptimizationResult,
    BudgetTradeOff,
    MaterialOption,
    MaterialRecommendation,
    DesignState,
)

# Benchmark rate tables per square foot
# INR Base rates (₹/sq ft)
RATES_INR = {
    "kitchen": {"cosmetic": (1200, 2200), "moderate": (3500, 5500), "full": (6500, 11000), "luxury": (12000, 25000)},
    "bathroom": {"cosmetic": (1500, 2800), "moderate": (4000, 7000), "full": (8000, 14000), "luxury": (16000, 30000)},
    "master_bedroom": {"cosmetic": (800, 1600), "moderate": (2000, 3800), "full": (4000, 7500), "luxury": (9000, 18000)},
    "bedroom": {"cosmetic": (700, 1400), "moderate": (1800, 3200), "full": (3500, 6500), "luxury": (8000, 15000)},
    "living_room": {"cosmetic": (900, 1800), "moderate": (2200, 4200), "full": (4500, 8500), "luxury": (10000, 20000)},
    "dining_room": {"cosmetic": (800, 1500), "moderate": (1900, 3600), "full": (3800, 7200), "luxury": (9000, 17000)},
    "home_office": {"cosmetic": (700, 1400), "moderate": (1800, 3400), "full": (3600, 6800), "luxury": (8500, 16000)},
    "basement": {"cosmetic": (900, 1700), "moderate": (2000, 4000), "full": (4000, 7800), "luxury": (9000, 18000)},
    "laundry_room": {"cosmetic": (1000, 2000), "moderate": (2500, 4800), "full": (5000, 9000), "luxury": (11000, 20000)},
    "outdoor_patio": {"cosmetic": (700, 1300), "moderate": (1500, 3000), "full": (3000, 6000), "luxury": (7000, 14000)},
}

# USD Base rates ($/sq ft)
RATES_USD = {
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


def calculate_baseline_cost(
    room_type: str,
    scope: str = "moderate",
    square_footage: int = 180,
    currency: Currency = Currency.INR,
) -> Tuple[float, float, float]:
    """Calculates min, max, and mid-point baseline renovation cost."""
    clean_room = room_type.lower().replace(" ", "_")
    clean_scope = scope.lower()
    
    rate_table = RATES_INR if currency == Currency.INR else RATES_USD
    room_rates = rate_table.get(clean_room, rate_table["kitchen"])
    scope_rates = room_rates.get(clean_scope, room_rates["moderate"])

    sqft = max(30, min(5000, square_footage))
    low = round(scope_rates[0] * sqft, 2)
    high = round(scope_rates[1] * sqft, 2)
    mid = round((low + high) / 2.0, 2)
    return low, high, mid


def optimize_renovation_budget(
    room_type: str,
    scope: str = "moderate",
    square_footage: int = 180,
    target_budget: float = 800000.0,
    currency: Currency = Currency.INR,
    current_design: Optional[DesignState] = None,
) -> BudgetOptimizationResult:
    """Evaluates budget vs baseline estimate and generates value-engineering alternatives."""
    _, _, estimated_mid = calculate_baseline_cost(room_type, scope, square_footage, currency)

    is_over = estimated_mid > target_budget
    overrun = max(0.0, round(estimated_mid - target_budget, 2))

    trade_offs: List[BudgetTradeOff] = []
    symbol = "₹" if currency == Currency.INR else "$"

    if is_over:
        # Determine value-engineering substitutions based on room type
        if currency == Currency.INR:
            substitutions = [
                (
                    "Countertops & Slab",
                    "Imported Italian Marble / Quartzite Slabs",
                    round(0.18 * estimated_mid, 2),
                    "Engineered Quartz (Calacatta pattern) or High-Grade Granite",
                    round(0.10 * estimated_mid, 2),
                    round(0.08 * estimated_mid, 2),
                    "Quartz offers 0% porosity and superior stain resistance with identical marble visual veining.",
                    "HIGH",
                ),
                (
                    "Cabinetry & Joinery",
                    "Custom PU-Coated Marine Plywood with Blum Soft-Close Servo",
                    round(0.32 * estimated_mid, 2),
                    "Modular BWR Plywood with High-Gloss Acrylic / Matte Laminate",
                    round(0.24 * estimated_mid, 2),
                    round(0.08 * estimated_mid, 2),
                    "Maintains boiling-water resistant substrate while replacing expensive PU paint with durable acrylic laminate.",
                    "HIGH",
                ),
                (
                    "Flooring",
                    "Imported 3x3 Greek Thassos / Botticino Marble",
                    round(0.14 * estimated_mid, 2),
                    "Large-Format 24x48 Rectified Glazed Vitrified Tiles (GVT)",
                    round(0.08 * estimated_mid, 2),
                    round(0.06 * estimated_mid, 2),
                    "Vitrified tiles eliminate ongoing sealing and polishing costs while delivering a sleek modern finish.",
                    "MEDIUM",
                ),
                (
                    "Wall Finishes & Ceilings",
                    "Multi-layer Lime-wash / Venetian Stucco & Gypsum Bulkheads",
                    round(0.08 * estimated_mid, 2),
                    "Smooth Level-5 Skim Coat with Royal Acrylic Emulsion",
                    round(0.05 * estimated_mid, 2),
                    round(0.03 * estimated_mid, 2),
                    "Clean, scrubbable matte finish without specialized artisan labor markups.",
                    "LOW",
                ),
            ]
        else:
            substitutions = [
                (
                    "Countertops",
                    "Full-Slab Natural Calacatta Marble ($140/sq ft installed)",
                    round(0.18 * estimated_mid, 2),
                    "Engineered Quartz (Silestone / Cambria, $80/sq ft installed)",
                    round(0.10 * estimated_mid, 2),
                    round(0.08 * estimated_mid, 2),
                    "Non-porous quartz requires zero annual sealing and withstands lemon juice and red wine.",
                    "HIGH",
                ),
                (
                    "Cabinetry",
                    "Full Custom Inset White Oak Cabinets ($600/lin ft)",
                    round(0.34 * estimated_mid, 2),
                    "Semi-Custom Pre-Finished Maple Shaker Cabinets ($380/lin ft)",
                    round(0.25 * estimated_mid, 2),
                    round(0.09 * estimated_mid, 2),
                    "Factory-finished baked enamel ensures 15-year chip resistance at a 30% discount.",
                    "HIGH",
                ),
                (
                    "Flooring",
                    "Site-Finished 7-inch Engineered White Oak Hardwood ($18/sq ft)",
                    round(0.12 * estimated_mid, 2),
                    "Commercial-Grade Rigid Core Luxury Vinyl Plank (LVP, $7/sq ft)",
                    round(0.05 * estimated_mid, 2),
                    round(0.07 * estimated_mid, 2),
                    "100% waterproof construction with integrated acoustic cork underlayment.",
                    "MEDIUM",
                ),
            ]

        accumulated_savings = 0.0
        for cat, orig, o_cost, alt, a_cost, sav, comp, rec in substitutions:
            if accumulated_savings < overrun or len(trade_offs) < 2:
                trade_offs.append(
                    BudgetTradeOff(
                        category=cat,
                        original_item=orig,
                        original_cost=o_cost,
                        suggested_alternative=alt,
                        alternative_cost=a_cost,
                        savings=sav,
                        compromise_description=comp,
                        recommendation_level=rec,
                    )
                )
                accumulated_savings += sav

        total_savings = round(accumulated_savings, 2)
        optimized_total = max(target_budget, round(estimated_mid - total_savings, 2))
        summary_advice = (
            f"Your stated budget of {symbol}{target_budget:,.0f} was initially exceeded by {symbol}{overrun:,.0f}. "
            f"Our value-engineering engine identified {len(trade_offs)} strategic material and fabrication adjustments "
            f"that recover {symbol}{total_savings:,.0f} in savings without altering your core room layout or spatial flow."
        )
    else:
        optimized_total = estimated_mid
        total_savings = 0.0
        summary_advice = (
            f"Your project budget of {symbol}{target_budget:,.0f} comfortably accommodates the estimated baseline of "
            f"{symbol}{estimated_mid:,.0f}. Your scope has an estimated buffer of {symbol}{(target_budget - estimated_mid):,.0f} "
            f"which can be allocated to luxury appliance upgrades or custom architectural lighting."
        )

    preserved_features = [
        "Preserved architectural footprint and window/door openings.",
        "Undisturbed plumbing stack and primary drainage rough-in centers.",
        "Full 10% contingency reserve maintained for unforeseen site discoveries.",
        "Licensed trade labor standards (master plumber & licensed electrician).",
    ]

    return BudgetOptimizationResult(
        target_budget=target_budget,
        original_estimate=estimated_mid,
        is_over_budget=is_over,
        overrun_amount=overrun,
        optimized_total=optimized_total,
        total_savings=total_savings,
        currency=currency,
        trade_offs=trade_offs,
        preserved_features=preserved_features,
        summary_advice=summary_advice,
    )


def get_material_catalog_recommendations(
    room_type: str,
    currency: Currency = Currency.INR,
) -> List[MaterialRecommendation]:
    """Returns curated material recommendations with primary vs value-engineered alternatives."""
    is_inr = currency == Currency.INR
    sym = "₹" if is_inr else "$"

    if is_inr:
        countertop_prim = MaterialOption(
            name="Imported Italian Statuario Marble",
            category="Countertops",
            unit_price=1200.0,
            currency=currency,
            durability_score=3,
            maintenance_level="High",
            aesthetic_rating=5,
            notes="Requires annual impregnating sealants against turmeric and lemon acids.",
        )
        countertop_alt = MaterialOption(
            name="Engineered Calacatta Quartz (18mm)",
            category="Countertops",
            unit_price=450.0,
            currency=currency,
            durability_score=5,
            maintenance_level="Low",
            aesthetic_rating=5,
            notes="Non-porous, stain-proof, heat resistant up to 150°C.",
        )

        flooring_prim = MaterialOption(
            name="Bookmatched Botticino Marble Slabs",
            category="Flooring",
            unit_price=650.0,
            currency=currency,
            durability_score=4,
            maintenance_level="Medium",
            aesthetic_rating=5,
        )
        flooring_alt = MaterialOption(
            name="24x48 Rectified Glazed Vitrified Tiles (GVT)",
            category="Flooring",
            unit_price=135.0,
            currency=currency,
            durability_score=5,
            maintenance_level="Low",
            aesthetic_rating=4,
        )
    else:
        countertop_prim = MaterialOption(
            name="Honed Carrara Marble",
            category="Countertops",
            unit_price=120.0,
            currency=currency,
            durability_score=3,
            maintenance_level="High",
            aesthetic_rating=5,
        )
        countertop_alt = MaterialOption(
            name="Silestone Calacatta Gold Quartz",
            category="Countertops",
            unit_price=75.0,
            currency=currency,
            durability_score=5,
            maintenance_level="Low",
            aesthetic_rating=5,
        )

        flooring_prim = MaterialOption(
            name="Select White Oak Engineered Hardwood",
            category="Flooring",
            unit_price=14.0,
            currency=currency,
            durability_score=4,
            maintenance_level="Medium",
            aesthetic_rating=5,
        )
        flooring_alt = MaterialOption(
            name="Luxury Rigid-Core Vinyl Plank (20mil wear)",
            category="Flooring",
            unit_price=5.50,
            currency=currency,
            durability_score=5,
            maintenance_level="Low",
            aesthetic_rating=4,
        )

    # 45 sq ft of countertops (typical 15 linear ft kitchen)
    ct_qty = 45.0
    ct_p_tot = round(ct_qty * countertop_prim.unit_price, 2)
    ct_a_tot = round(ct_qty * countertop_alt.unit_price, 2)

    # 180 sq ft of flooring
    fl_qty = 180.0
    fl_p_tot = round(fl_qty * flooring_prim.unit_price, 2)
    fl_a_tot = round(fl_qty * flooring_alt.unit_price, 2)

    return [
        MaterialRecommendation(
            category="Countertops",
            primary_option=countertop_prim,
            alternative_option=countertop_alt,
            estimated_quantity=ct_qty,
            unit="sq.ft",
            total_primary_cost=ct_p_tot,
            total_alternative_cost=ct_a_tot,
            potential_savings=round(ct_p_tot - ct_a_tot, 2),
        ),
        MaterialRecommendation(
            category="Flooring",
            primary_option=flooring_prim,
            alternative_option=flooring_alt,
            estimated_quantity=fl_qty,
            unit="sq.ft",
            total_primary_cost=fl_p_tot,
            total_alternative_cost=fl_a_tot,
            potential_savings=round(fl_p_tot - fl_a_tot, 2),
        ),
    ]
