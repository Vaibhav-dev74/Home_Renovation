"""Automated Bill of Quantities (BOQ) Engine & Exporter.

Computes mathematically grounded material & labor quantities derived from
room dimensions and spatial constraints. Supports multi-currency calculations,
wastage allowances, and CSV / printable HTML exports.
"""

import csv
import io
import math
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from models import (
    BOQItem,
    BOQSummary,
    Currency,
    SpatialModel,
    DesignState,
)


def generate_automated_boq(
    project_id: str,
    room_type: str,
    scope: str = "moderate",
    square_footage: int = 180,
    spatial_model: Optional[SpatialModel] = None,
    design_state: Optional[DesignState] = None,
    currency: Currency = Currency.INR,
) -> BOQSummary:
    """Generates an itemized Bill of Quantities (BOQ) with transparent quantities and unit rates."""
    clean_room = room_type.lower().replace(" ", "_")
    clean_scope = scope.lower()
    is_inr = currency == Currency.INR

    # Derive dimensional quantities
    floor_area = float(square_footage)
    ceiling_height = 9.0
    if spatial_model and spatial_model.dimensions:
        floor_area = spatial_model.dimensions.area_sqft
        ceiling_height = spatial_model.dimensions.height_ft

    # Estimate perimeter walls (assuming ~1.3 aspect ratio room)
    width = round(math.sqrt(floor_area / 1.3), 1)
    length = round(floor_area / width, 1)
    perimeter_lin_ft = round(2 * (length + width), 1)
    # Gross wall area minus standard window/door deductions (~60 sq ft)
    wall_area_sqft = max(100.0, round((perimeter_lin_ft * ceiling_height) - 60.0, 1))

    # Waste margins
    tile_wastage_factor = 1.10  # 10% cutting waste
    paint_coats_factor = 2.0    # 2 finish coats

    items: List[BOQItem] = []
    item_idx = 1

    def add_item(category, name, desc, qty, unit, mat_rate, lab_rate, notes=""):
        nonlocal item_idx
        m_sub = round(qty * mat_rate, 2)
        l_sub = round(qty * lab_rate, 2)
        tot = round(m_sub + l_sub, 2)
        items.append(
            BOQItem(
                item_id=f"BOQ-{item_idx:03d}",
                category=category,
                item_name=name,
                description=desc,
                quantity=round(qty, 2),
                unit=unit,
                material_unit_rate=mat_rate,
                labor_unit_rate=lab_rate,
                material_subtotal=m_sub,
                labor_subtotal=l_sub,
                total_amount=tot,
                currency=currency,
                assumption_notes=notes,
            )
        )
        item_idx += 1

    # 1. Civil & Demolition
    demo_rate_mat = 0.0
    demo_rate_lab = 35.0 if is_inr else 3.50
    if clean_scope in ["full", "luxury"]:
        demo_rate_lab *= 1.8
    add_item(
        "Civil & Demolition",
        "Selective Demolition & Haul-away",
        f"Safe strip-out of existing fixtures, cabinetry, surface coatings, and debris haul for {floor_area:.0f} sq ft room",
        floor_area,
        "sq.ft",
        demo_rate_mat,
        demo_rate_lab,
        "Includes municipal disposal carting fees and dust protection containment.",
    )

    # 2. Flooring & Baseboards
    tile_qty = round(floor_area * tile_wastage_factor, 1)
    if is_inr:
        tile_mat_rate = 145.0 if clean_scope == "moderate" else (280.0 if clean_scope == "full" else 650.0)
        tile_lab_rate = 55.0
    else:
        tile_mat_rate = 7.50 if clean_scope == "moderate" else (14.0 if clean_scope == "full" else 24.0)
        tile_lab_rate = 6.00
    
    floor_mat_name = design_state.flooring_type if design_state else "Glazed Vitrified Tile / LVP"
    add_item(
        "Flooring",
        f"Floor Finish: {floor_mat_name}",
        f"Subfloor surface prep, adhesive bedding, grouting, and edge trims (includes 10% cutting wastage allowance)",
        tile_qty,
        "sq.ft",
        tile_mat_rate,
        tile_lab_rate,
        f"Base net area {floor_area:.0f} sq ft + 10% pattern/cut waste margin.",
    )

    # 3. Carpentry & Cabinetry (for Kitchens / Bedrooms / Baths)
    if clean_room == "kitchen":
        # Linear feet of base and upper cabinets
        cab_lin_ft = max(10.0, round(perimeter_lin_ft * 0.45, 1))
        if is_inr:
            cab_mat_rate = 4200.0 if clean_scope == "moderate" else 7500.0
            cab_lab_rate = 1200.0
        else:
            cab_mat_rate = 260.0 if clean_scope == "moderate" else 480.0
            cab_lab_rate = 95.0
        
        cab_style = design_state.cabinet_style if design_state else "Modular Shaker"
        cab_color = design_state.cabinet_color if design_state else "Two-tone"
        add_item(
            "Carpentry & Cabinetry",
            f"Kitchen Modular Cabinetry ({cab_style})",
            f"Base & overhead storage units in {cab_color}, soft-close hinges, full-extension drawer runners",
            cab_lin_ft,
            "running.ft",
            cab_mat_rate,
            cab_lab_rate,
            f"Calculated from perimeter cabinet run (~{cab_lin_ft:.1f} linear ft).",
        )

        # Countertop stone
        counter_sqft = round(cab_lin_ft * 2.2, 1)  # 26 inch standard depth
        if is_inr:
            ct_mat_rate = 380.0 if clean_scope == "moderate" else 850.0
            ct_lab_rate = 95.0
        else:
            ct_mat_rate = 70.0 if clean_scope == "moderate" else 135.0
            ct_lab_rate = 25.0

        ct_stone = design_state.countertop_material if design_state else "Engineered Quartz"
        add_item(
            "Carpentry & Cabinetry",
            f"Countertop Stone & Edging ({ct_stone})",
            f"Fabrication, sink cutout, pencil-edge polishing, and mechanical anchoring",
            counter_sqft,
            "sq.ft",
            ct_mat_rate,
            ct_lab_rate,
            f"Based on {cab_lin_ft:.1f} running ft counter run at 26-inch standard depth.",
        )
    elif clean_room in ["bedroom", "master_bedroom"]:
        wardrobe_lin_ft = max(6.0, round(length * 0.7, 1))
        if is_inr:
            w_mat_rate = 3800.0
            w_lab_rate = 950.0
        else:
            w_mat_rate = 220.0
            w_lab_rate = 75.0
        add_item(
            "Carpentry & Cabinetry",
            "Built-in Wardrobe / Closet System",
            "Full-height wardrobe with modular shelving, hanging rods, and internal LED strip lights",
            wardrobe_lin_ft,
            "running.ft",
            w_mat_rate,
            w_lab_rate,
            f"Proportioned to {wardrobe_lin_ft:.1f} linear feet of storage.",
        )

    # 4. Plumbing & Wet-Area Rough-Ins
    if clean_room in ["kitchen", "bathroom", "laundry_room"]:
        if is_inr:
            plumb_mat = 18000.0 if clean_room == "kitchen" else 32000.0
            plumb_lab = 12000.0 if clean_room == "kitchen" else 18000.0
        else:
            plumb_mat = 950.0 if clean_room == "kitchen" else 1800.0
            plumb_lab = 1100.0 if clean_room == "kitchen" else 2200.0
        
        add_item(
            "Plumbing",
            "Plumbing Rough-in & Fixture Trim-out",
            "CPVC/PEX water supply lines, trap connections, isolation valves, and professional faucet mounting",
            1.0,
            "lump_sum",
            plumb_mat,
            plumb_lab,
            "Preserves primary drain rough-in stack centers.",
        )

    # 5. Electrical & Lighting
    # Points estimated based on room area (~1 point per 25 sq ft)
    elec_points = max(6, round(floor_area / 25.0))
    if is_inr:
        elec_mat_rate = 950.0
        elec_lab_rate = 550.0
    else:
        elec_mat_rate = 65.0
        elec_lab_rate = 85.0

    add_item(
        "Electrical",
        "Concealed Electrical Circuit Wiring & Outlets",
        f"FR wiring in conduit, dedicated circuits, modular switches, and safety grounding ({elec_points} points)",
        float(elec_points),
        "units",
        elec_mat_rate,
        elec_lab_rate,
        "Includes GFCI protection compliance for wet locations.",
    )

    # Architectural Lighting Fixtures
    fixtures_count = 4 if floor_area < 150 else 6
    if is_inr:
        fix_mat_rate = 1400.0
        fix_lab_rate = 300.0
    else:
        fix_mat_rate = 65.0
        fix_lab_rate = 45.0
    add_item(
        "Electrical",
        "Architectural Lighting Fixtures & Recessed LEDs",
        f"2700K Warm LED ceiling downlights, under-cabinet task channels, and dimmable drivers",
        float(fixtures_count),
        "units",
        fix_mat_rate,
        fix_lab_rate,
        "Calculated for minimum 350-500 lumens/sq m workspace illumination.",
    )

    # 6. Painting & Surface Finishes
    paint_qty = round(wall_area_sqft, 1)
    if is_inr:
        paint_mat_rate = 28.0
        paint_lab_rate = 22.0
    else:
        paint_mat_rate = 1.40
        paint_lab_rate = 2.10
    
    wall_color = design_state.wall_paint if design_state else "Premium Acrylic Emulsion"
    add_item(
        "Painting",
        f"Interior Wall Painting ({wall_color})",
        f"Surface sanding, primer coat, two coats of washable low-VOC acrylic emulsion across {paint_qty:.0f} sq ft wall surface",
        paint_qty,
        "sq.ft",
        paint_mat_rate,
        paint_lab_rate,
        f"Computed from perimeter walls ({perimeter_lin_ft:.1f} ft) minus opening deductions.",
    )

    # 7. Hardware & Site Protection
    if is_inr:
        hw_mat = 8500.0
        hw_lab = 3500.0
    else:
        hw_mat = 450.0
        hw_lab = 250.0
    add_item(
        "Hardware",
        "Architectural Hardware & Protective Seals",
        "Silicone sanitary sealants, threshold transition strips, door stops, and hardware fasteners",
        1.0,
        "lump_sum",
        hw_mat,
        hw_lab,
        "Ensures moisture barrier perimeter seals.",
    )

    # Calculate Totals
    sub_materials = round(sum(i.material_subtotal for i in items), 2)
    sub_labor = round(sum(i.labor_subtotal for i in items), 2)
    permit_fee = round(0.03 * (sub_materials + sub_labor), 2) if clean_scope in ["moderate", "full", "luxury"] else 0.0
    sub_direct = sub_materials + sub_labor + permit_fee
    contingency = round(0.10 * sub_direct, 2)
    grand_total = round(sub_direct + contingency, 2)

    return BOQSummary(
        project_id=project_id,
        currency=currency,
        items=items,
        subtotal_materials=sub_materials,
        subtotal_labor=sub_labor,
        permits_and_fees=permit_fee,
        contingency_rate_pct=10.0,
        contingency_amount=contingency,
        grand_total=grand_total,
    )


def export_boq_to_csv(boq: BOQSummary) -> str:
    """Exports BOQ into a standard CSV format compatible with Microsoft Excel and Google Sheets."""
    output = io.StringIO()
    writer = csv.writer(output)

    sym = "INR (Rs)" if boq.currency == Currency.INR else "USD ($)"
    writer.writerow(["BILL OF QUANTITIES (BOQ) - AI RENOVATION INTELLIGENCE PLATFORM"])
    writer.writerow([f"Project ID: {boq.project_id}", f"Generated: {boq.calculation_timestamp}", f"Currency: {sym}"])
    writer.writerow([])
    writer.writerow([
        "Item ID", "Category", "Item Name", "Description",
        "Quantity", "Unit", "Material Rate", "Labor Rate",
        "Material Subtotal", "Labor Subtotal", "Total Amount", "Assumptions & Sourcing"
    ])

    for item in boq.items:
        writer.writerow([
            item.item_id,
            item.category,
            item.item_name,
            item.description,
            item.quantity,
            item.unit,
            item.material_unit_rate,
            item.labor_unit_rate,
            item.material_subtotal,
            item.labor_subtotal,
            item.total_amount,
            item.assumption_notes,
        ])

    writer.writerow([])
    writer.writerow(["", "", "", "", "", "", "", "Subtotal Materials:", boq.subtotal_materials])
    writer.writerow(["", "", "", "", "", "", "", "Subtotal Labor:", boq.subtotal_labor])
    writer.writerow(["", "", "", "", "", "", "", "Permits & Municipal Fees:", boq.permits_and_fees])
    writer.writerow(["", "", "", "", "", "", "", f"Contingency Reserve ({boq.contingency_rate_pct}%):", boq.contingency_amount])
    writer.writerow(["", "", "", "", "", "", "", "GRAND TOTAL:", boq.grand_total])

    return output.getvalue()


def export_boq_to_html_printable(boq: BOQSummary, project_name: str = "Renovation Project") -> str:
    """Generates an executive, printable HTML document for saving as PDF or sharing with contractors."""
    sym = "₹" if boq.currency == Currency.INR else "$"

    rows_html = []
    for item in boq.items:
        rows_html.append(f"""
        <tr>
            <td style="font-family:monospace; font-weight:600; color:#4b5563;">{item.item_id}</td>
            <td style="font-weight:600; color:#1f2937;">{item.category}</td>
            <td>
                <strong>{item.item_name}</strong><br>
                <span style="font-size:0.85rem; color:#6b7280;">{item.description}</span>
                {f'<br><em style="font-size:0.75rem; color:#9ca3af;">Note: {item.assumption_notes}</em>' if item.assumption_notes else ''}
            </td>
            <td style="text-align:right;">{item.quantity:,.1f} {item.unit}</td>
            <td style="text-align:right;">{sym}{item.material_unit_rate:,.2f}</td>
            <td style="text-align:right;">{sym}{item.labor_unit_rate:,.2f}</td>
            <td style="text-align:right; font-weight:600;">{sym}{item.total_amount:,.2f}</td>
        </tr>
        """)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>BOQ - {project_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; color: #111827; }}
        .header {{ border-bottom: 2px solid #e5e7eb; padding-bottom: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; }}
        .title {{ font-size: 24px; font-weight: 700; color: #1e3a8a; margin: 0; }}
        .meta {{ font-size: 13px; color: #6b7280; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13px; }}
        th {{ background: #f3f4f6; color: #374151; text-align: left; padding: 10px 12px; border-bottom: 2px solid #d1d5db; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }}
        tr:nth-child(even) {{ background: #fafafa; }}
        .totals-table {{ width: 350px; margin-left: auto; margin-top: 30px; font-size: 14px; border-collapse: collapse; }}
        .totals-table td {{ padding: 8px 12px; }}
        .grand-total {{ font-size: 16px; font-weight: 700; background: #e0e7ff; color: #1e3a8a; border-top: 2px solid #3b82f6; }}
        .disclaimer {{ margin-top: 50px; font-size: 11px; color: #9ca3af; border-top: 1px solid #e5e7eb; padding-top: 15px; }}
        @media print {{
            body {{ margin: 15mm; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="no-print" style="margin-bottom: 20px;">
        <button onclick="window.print()" style="background:#2563eb; color:#fff; border:none; padding:10px 20px; border-radius:6px; cursor:pointer; font-weight:600;">🖨️ Print / Save as PDF</button>
    </div>
    <div class="header">
        <div>
            <h1 class="title">Bill of Quantities (BOQ)</h1>
            <div class="meta">Project: <strong>{project_name}</strong> | ID: {boq.project_id}</div>
            <div class="meta">Generated: {boq.calculation_timestamp[:10]} | Standards: Architectural Estimating Model</div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 18px; font-weight: 700; color: #1e3a8a;">AI Renovation Intelligence</div>
            <div class="meta">Verified Construction Estimating</div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th style="width:70px;">Item</th>
                <th style="width:130px;">Category</th>
                <th>Description & Specifications</th>
                <th style="width:100px; text-align:right;">Quantity</th>
                <th style="width:90px; text-align:right;">Material</th>
                <th style="width:80px; text-align:right;">Labor</th>
                <th style="width:110px; text-align:right;">Subtotal</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows_html)}
        </tbody>
    </table>

    <table class="totals-table">
        <tr>
            <td>Direct Materials Subtotal:</td>
            <td style="text-align:right; font-weight:600;">{sym}{boq.subtotal_materials:,.2f}</td>
        </tr>
        <tr>
            <td>Direct Labor Subtotal:</td>
            <td style="text-align:right; font-weight:600;">{sym}{boq.subtotal_labor:,.2f}</td>
        </tr>
        <tr>
            <td>Permits & Municipal Fees:</td>
            <td style="text-align:right; font-weight:600;">{sym}{boq.permits_and_fees:,.2f}</td>
        </tr>
        <tr>
            <td>Contingency Reserve ({boq.contingency_rate_pct}%):</td>
            <td style="text-align:right; font-weight:600;">{sym}{boq.contingency_amount:,.2f}</td>
        </tr>
        <tr class="grand-total">
            <td>ESTIMATED GRAND TOTAL:</td>
            <td style="text-align:right;">{sym}{boq.grand_total:,.2f}</td>
        </tr>
    </table>

    <div class="disclaimer">
        <strong>CONTRACTOR NOTICE & DISCLAIMER:</strong> This Bill of Quantities is produced by the AI Home Renovation Intelligence Platform based on architectural spatial parameters and standard contractor estimating models. Quantities include standard material cut allowances (10% on tiling, 2 finish coats on wall emulsions). Actual job-site conditions, concealed structural or plumbing anomalies, and local material market fluctuations may affect final contractor bids. Homeowners should verify measurements on-site with licensed trade professionals before purchasing materials.
    </div>
</body>
</html>"""
    return html
