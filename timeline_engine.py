"""Construction Timeline & Task Dependency DAG Engine.

Generates realistic, graph-based construction schedules with trade dependencies,
inspection milestones, and critical path analysis.
"""

from typing import List, Dict, Set, Optional
from models import TimelineSchedule, TimelineTask


def build_construction_schedule(
    project_id: str,
    room_type: str,
    scope: str = "moderate",
    structural_changes: bool = False,
    plumbing_changes: bool = False,
    electrical_changes: bool = False,
) -> TimelineSchedule:
    """Builds a dependency DAG construction timeline based on room type and renovation scope."""
    clean_room = room_type.lower().replace(" ", "_")
    clean_scope = scope.lower()

    tasks: List[TimelineTask] = []

    # ------------------------------------------------------------------------
    # 1. Phase 1: Planning, Permitting & Mobilization
    # ------------------------------------------------------------------------
    prep_days = 2 if clean_scope == "cosmetic" else (5 if clean_scope == "moderate" else 12)
    tasks.append(
        TimelineTask(
            task_id="TSK-01",
            phase_name="Phase 1: Planning & Pre-Construction",
            title="Material Procurement & Permit Filings",
            description="Finalize trade contracts, submit municipal permit applications (AHJ), order long lead-time cabinetry and stone slabs.",
            duration_days=prep_days,
            depends_on=[],
            trade_required="General",
            is_critical_path=True,
            inspection_required=False,
        )
    )

    tasks.append(
        TimelineTask(
            task_id="TSK-02",
            phase_name="Phase 1: Planning & Pre-Construction",
            title="Site Protection & Containment",
            description="Install zip-wall dust containment, floor protection runners from entryway, and cap off existing branch lines.",
            duration_days=1,
            depends_on=["TSK-01"],
            trade_required="General",
            is_critical_path=True,
            inspection_required=False,
        )
    )

    # ------------------------------------------------------------------------
    # 2. Phase 2: Demolition & Structural Rough-In
    # ------------------------------------------------------------------------
    demo_days = 1 if clean_scope == "cosmetic" else (3 if clean_scope == "moderate" else 6)
    tasks.append(
        TimelineTask(
            task_id="TSK-03",
            phase_name="Phase 2: Demolition",
            title="Selective Strip-out & Debris Carting",
            description="Carefully remove existing cabinets, fixtures, trim, and designated wall coverings down to studs/subfloor.",
            duration_days=demo_days,
            depends_on=["TSK-02"],
            trade_required="Demolition",
            is_critical_path=True,
            inspection_required=False,
        )
    )

    if structural_changes or clean_scope in ["full", "luxury"]:
        tasks.append(
            TimelineTask(
                task_id="TSK-04",
                phase_name="Phase 3: Structural & Rough Trades",
                title="Framing Alterations & Structural Headers",
                description="Erect new partition walls, install reinforced headers over openings, and square up subfloor framing.",
                duration_days=4,
                depends_on=["TSK-03"],
                trade_required="Carpentry",
                is_critical_path=True,
                inspection_required=True,
            )
        )
        last_trade_dep = "TSK-04"
    else:
        last_trade_dep = "TSK-03"

    # ------------------------------------------------------------------------
    # 3. Phase 3: Mechanical, Electrical & Plumbing (MEP) Rough-Ins
    # ------------------------------------------------------------------------
    if plumbing_changes or clean_room in ["kitchen", "bathroom", "laundry_room"] or clean_scope in ["moderate", "full", "luxury"]:
        tasks.append(
            TimelineTask(
                task_id="TSK-05",
                phase_name="Phase 3: MEP Rough-Ins",
                title="Plumbing Supply & Drain Rough-in",
                description="Relocate water supply lines, set shower/tub valve assemblies, tie into waste stack, and run pressure test.",
                duration_days=3 if clean_scope == "moderate" else 5,
                depends_on=[last_trade_dep],
                trade_required="Plumbing",
                is_critical_path=True,
                inspection_required=True,
            )
        )
        plumb_dep = "TSK-05"
    else:
        plumb_dep = last_trade_dep

    if electrical_changes or clean_scope in ["moderate", "full", "luxury"]:
        tasks.append(
            TimelineTask(
                task_id="TSK-06",
                phase_name="Phase 3: MEP Rough-Ins",
                title="Electrical Conduit, Circuit Runs & Lighting Boxes",
                description="Pull 20A appliance lines, install recessed light housings, wire under-cabinet runs, and prep GFCI device boxes.",
                duration_days=2 if clean_scope == "moderate" else 4,
                depends_on=[last_trade_dep],
                trade_required="Electrical",
                is_critical_path=False,  # Can run concurrently with plumbing
                inspection_required=True,
            )
        )
        elec_dep = "TSK-06"
    else:
        elec_dep = last_trade_dep

    # City In-Wall Rough-In Inspection
    if clean_scope in ["moderate", "full", "luxury"]:
        tasks.append(
            TimelineTask(
                task_id="TSK-07",
                phase_name="Phase 3: MEP Rough-Ins",
                title="Municipal Trade Rough-In Inspections",
                description="Building inspector reviews open-wall structural framing, plumbing pressure test, and electrical rough-in.",
                duration_days=2,
                depends_on=list(set([plumb_dep, elec_dep])),
                trade_required="General",
                is_critical_path=True,
                inspection_required=True,
            )
        )
        wall_close_dep = "TSK-07"
    else:
        wall_close_dep = last_trade_dep

    # ------------------------------------------------------------------------
    # 4. Phase 4: Wall Closure, Drywall & Surface Prep
    # ------------------------------------------------------------------------
    if clean_scope in ["moderate", "full", "luxury"]:
        tasks.append(
            TimelineTask(
                task_id="TSK-08",
                phase_name="Phase 4: Wall & Surface Enclosures",
                title="Insulation & Drywall Hanging / Taping",
                description="Install acoustic/thermal batts, hang 1/2-inch or 5/8-inch drywall, apply 3 coats of joint compound, Level-4 finish.",
                duration_days=4 if clean_scope == "moderate" else 7,
                depends_on=[wall_close_dep],
                trade_required="General",
                is_critical_path=True,
                inspection_required=False,
            )
        )
        finish_dep = "TSK-08"
    else:
        finish_dep = "TSK-03"

    # ------------------------------------------------------------------------
    # 5. Phase 5: Flooring & Cabinetry Installation
    # ------------------------------------------------------------------------
    tasks.append(
        TimelineTask(
            task_id="TSK-09",
            phase_name="Phase 5: Finishes & Built-ins",
            title="Flooring Surface Prep & Tile/Hardwood Laying",
            description="Level subfloor substrate, lay porcelain tiles or hardwood flooring, allow cure time, apply grout and sealers.",
            duration_days=3 if clean_scope == "moderate" else 5,
            depends_on=[finish_dep],
            trade_required="Tiling",
            is_critical_path=True,
            inspection_required=False,
        )
    )

    if clean_room in ["kitchen", "bathroom", "master_bedroom"]:
        tasks.append(
            TimelineTask(
                task_id="TSK-10",
                phase_name="Phase 5: Finishes & Built-ins",
                title="Modular Cabinetry Installation & Leveling",
                description="Hang upper cabinets on stud blocks, anchor base cabinets, align drawer slides, install filler panels and toe-kicks.",
                duration_days=3 if clean_scope == "moderate" else 5,
                depends_on=["TSK-09"],
                trade_required="Carpentry",
                is_critical_path=True,
                inspection_required=False,
            )
        )

        tasks.append(
            TimelineTask(
                task_id="TSK-11",
                phase_name="Phase 5: Finishes & Built-ins",
                title="Countertop Laser Templating & Installation",
                description="Laser template cabinet surfaces, fabricate stone cutouts offsite, deliver and mechanically anchor countertop slabs.",
                duration_days=5 if clean_scope == "moderate" else 8,
                depends_on=["TSK-10"],
                trade_required="General",
                is_critical_path=True,
                inspection_required=False,
            )
        )
        cabinet_dep = "TSK-11"
    else:
        cabinet_dep = "TSK-09"

    # ------------------------------------------------------------------------
    # 6. Phase 6: Trim, Painting & Fixture Trim-Out
    # ------------------------------------------------------------------------
    tasks.append(
        TimelineTask(
            task_id="TSK-12",
            phase_name="Phase 6: Fixture Trim-out & Paint",
            title="Tile Backsplash & Final Interior Painting",
            description="Install wall backsplash tile, apply two topcoats of washable wall paint, and spray trim/casing enamel.",
            duration_days=3,
            depends_on=[cabinet_dep],
            trade_required="Painting",
            is_critical_path=True,
            inspection_required=False,
        )
    )

    tasks.append(
        TimelineTask(
            task_id="TSK-13",
            phase_name="Phase 6: Fixture Trim-out & Paint",
            title="Final Trade Trim-Out (Plumbing & Electrical)",
            description="Mount sink, connect faucet and disposer, set trim plates, install decorative light pendants, and test GFCI breakers.",
            duration_days=2,
            depends_on=["TSK-12"],
            trade_required="Plumbing",
            is_critical_path=True,
            inspection_required=False,
        )
    )

    # ------------------------------------------------------------------------
    # 7. Phase 7: Punch List & Final Sign-Off
    # ------------------------------------------------------------------------
    tasks.append(
        TimelineTask(
            task_id="TSK-14",
            phase_name="Phase 7: Final Completion",
            title="Final Municipal Inspection & Deep Clean",
            description="Pass final building/occupancy inspection, execute contractor punch list items, and complete post-construction deep clean.",
            duration_days=2,
            depends_on=["TSK-13"],
            trade_required="General",
            is_critical_path=True,
            inspection_required=True,
        )
    )

    # Calculate Critical Path Duration (longest path through DAG)
    duration_map: Dict[str, int] = {t.task_id: t.duration_days for t in tasks}
    depends_map: Dict[str, List[str]] = {t.task_id: t.depends_on for t in tasks}

    # Memoized longest path calculation
    earliest_finish: Dict[str, int] = {}

    def get_finish_time(task_id: str) -> int:
        if task_id in earliest_finish:
            return earliest_finish[task_id]
        deps = depends_map.get(task_id, [])
        if not deps:
            earliest_finish[task_id] = duration_map[task_id]
        else:
            earliest_finish[task_id] = max(get_finish_time(d) for d in deps) + duration_map[task_id]
        return earliest_finish[task_id]

    for t in tasks:
        get_finish_time(t.task_id)

    total_working_days = max(earliest_finish.values()) if earliest_finish else 15
    total_calendar_weeks = max(1, round(total_working_days / 5.0 + 0.5))

    # Identify critical path tasks
    critical_path = [t.task_id for t in tasks if t.is_critical_path]
    phases = list(dict.fromkeys(t.phase_name for t in tasks))

    potential_delays = [
        "Municipal permit review backlog with local building department (adds 1-2 weeks).",
        "Stone countertop slab offsite fabrication backlog (typically 5-7 business days between template and install).",
        "Custom cabinet shop fabrication lead times (confirm 4-6 weeks in advance).",
        "Unforeseen concealed pipe corrosion or wiring junction anomalies discovered during wall demolition.",
    ]

    return TimelineSchedule(
        project_id=project_id,
        total_working_days=total_working_days,
        total_calendar_weeks=total_calendar_weeks,
        phases=phases,
        tasks=tasks,
        critical_path=critical_path,
        potential_delays=potential_delays,
    )
