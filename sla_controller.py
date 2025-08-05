# Utility: Match ticket priority to SLA policy (shared logic)
async def match_ticket_to_sla_policy(db, ticket_priority):
    from sla_models import SLAPolicy
    from sqlalchemy import select
    policy_result = await db.execute(select(SLAPolicy))
    all_policies = policy_result.scalars().all()
    sla_policies = {str(p.name).strip().lower(): p for p in all_policies}
    ticket_priority_normalized = (ticket_priority or '').strip().lower()
    matched_sla_name = None
    sla_policy = None
    if ticket_priority_normalized in sla_policies:
        sla_policy = sla_policies[ticket_priority_normalized]
        matched_sla_name = sla_policy.name
    else:
        for env_key, env_value in PRIORITY_LEVELS.items():
            if ticket_priority_normalized == env_value:
                if env_key in sla_policies:
                    sla_policy = sla_policies[env_key]
                    matched_sla_name = sla_policy.name
                    break
        if not sla_policy:
            for key, policy in sla_policies.items():
                if key in ticket_priority_normalized or ticket_priority_normalized in key:
                    sla_policy = policy
                    matched_sla_name = policy.name
                    break
        if not sla_policy and sla_policies:
            sla_policy = sla_policies.get("default sla") or list(sla_policies.values())[0]
            matched_sla_name = sla_policy.name if hasattr(sla_policy, "name") else sla_policy.get("name")
    return sla_policy, matched_sla_name

from models import Ticket
from datetime import datetime, timedelta
from fastapi import HTTPException
import os, math
from sqlalchemy import select
from sla_models import SLAPolicy


def to_dict(obj):
    if obj is None:return None
    if isinstance(obj,list):return [to_dict(i) for i in obj]
    if hasattr(obj,'__table__'):return{c.name:getattr(obj,c.name)for c in obj.__table__.columns}
    if isinstance(obj,dict):return{k:to_dict(v)for k,v in obj.items()}
    return obj


# Get priority levels from environment variables
PRIORITY_LEVELS = {
    "critical": os.getenv("PRIORITY_LEVEL_0", "critical").lower(),
    "high": os.getenv("PRIORITY_LEVEL_1", "high").lower(),
    "medium": os.getenv("PRIORITY_LEVEL_2", "medium").lower(),
    "low": os.getenv("PRIORITY_LEVEL_3", "low").lower(),
}

# SLA Controllers


async def update_all_tickets_sla_alignment(db):
    """Update all existing tickets to align with proper SLA assignment logic"""
    tickets_result = await db.execute(select(Ticket))
    tickets = tickets_result.scalars().all()

    policy_result = await db.execute(select(SLAPolicy))
    all_policies = policy_result.scalars().all()
    # Create case-insensitive mapping
    sla_policies = {}
    for p in all_policies:
        policy_name = str(p.name).strip().lower()
        sla_policies[policy_name] = p

    if not sla_policies:
        return {"error": "No SLA policies found"}

    updated_count = 0
    alignment_report = []

    for ticket in tickets:
        ticket_priority = (ticket.priority or "").strip().lower()
        old_sla_target = ticket.current_sla_target

        # Apply same logic as get_ticket_sla_status_controller
        matched_sla_name = None
        sla_policy = None

        # First try exact match with ticket priority
        if ticket_priority in sla_policies:
            sla_policy = sla_policies[ticket_priority]
            matched_sla_name = sla_policy.name
        else:
            # Try mapping from env variables and check if SLA policy exists
            for env_key, env_value in PRIORITY_LEVELS.items():
                if ticket_priority == env_value:
                    # Look for SLA policy with this name (case insensitive)
                    if env_key in sla_policies:
                        sla_policy = sla_policies[env_key]
                        matched_sla_name = sla_policy.name
                        break

            # If still no match, try partial matching on policy names
            if not sla_policy:
                for key, policy in sla_policies.items():
                    if key in ticket_priority or ticket_priority in key:
                        sla_policy = policy
                        matched_sla_name = policy.name
                        break

            # Final fallback to default
            if not sla_policy:
                sla_policy = sla_policies.get(
                    "default sla") or list(sla_policies.values())[0]
                matched_sla_name = sla_policy.name if hasattr(
                    sla_policy, "name") else sla_policy.get("name")

        # Calculate new SLA target time
        if ticket.createdat and sla_policy:
            new_sla_target = ticket.createdat + \
                timedelta(minutes=sla_policy.resolution_time_minutes)
            ticket.current_sla_target = new_sla_target
            updated_count += 1

            alignment_report.append({
                "ticket_id": ticket.ticketid,
                "subject": ticket.subject,
                "priority": ticket.priority,
                "matched_sla": matched_sla_name,
                "sla_minutes": sla_policy.resolution_time_minutes,
                "old_sla_target": str(old_sla_target) if old_sla_target else None,
                "new_sla_target": str(new_sla_target)
            })

    await db.commit()

    return {
        "message": f"Successfully updated SLA alignment for {updated_count} tickets",
        "updated_count": updated_count,
        "total_tickets": len(tickets),
        "alignment_report": alignment_report
    }


async def get_sla_policies_controller(db):
    result = await db.execute(select(SLAPolicy))
    return result.scalars().all()


async def create_sla_policy_controller(sla, db):
    new_policy = SLAPolicy(**sla.dict())
    db.add(new_policy)
    await db.commit()
    await db.refresh(new_policy)
    return new_policy


async def update_sla_policy_controller(sla_id, sla, db):
    result = await db.execute(select(SLAPolicy).where(SLAPolicy.sla_id == sla_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="SLA policy not found")

    for key, value in sla.dict(exclude_unset=True).items():
        setattr(policy, key, value)
    await db.commit()
    await db.refresh(policy)

    return policy


async def get_ticket_sla_status_controller(ticket_id, db):
    result = await db.execute(select(Ticket).where(Ticket.ticketid == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    policy_result = await db.execute(select(SLAPolicy))
    all_policies = policy_result.scalars().all()
    # Create case-insensitive mapping
    sla_policies = {}
    for p in all_policies:
        policy_name = str(p.name).strip().lower()
        sla_policies[policy_name] = p

    if not sla_policies:
        raise HTTPException(status_code=404, detail="No SLA policies found")
    created = ticket.createdat
    ticket_priority = (ticket.priority or "").strip().lower()

    # Map ticket priority to SLA policy using environment variables
    matched_sla_name = None
    sla_policy = None
    debug_priorities = list(sla_policies.keys())

    # First try exact match with ticket priority
    if ticket_priority in sla_policies:
        sla_policy = sla_policies[ticket_priority]
        matched_sla_name = sla_policy.name
    else:
        # Try mapping from env variables and check if SLA policy exists
        for env_key, env_value in PRIORITY_LEVELS.items():
            if ticket_priority == env_value:
                # Look for SLA policy with this name (case insensitive)
                if env_key in sla_policies:
                    sla_policy = sla_policies[env_key]
                    matched_sla_name = sla_policy.name
                    break

        # If still no match, try partial matching on policy names
        if not sla_policy:
            for key, policy in sla_policies.items():
                if key in ticket_priority or ticket_priority in key:
                    sla_policy = policy
                    matched_sla_name = policy.name
                    break

        # Final fallback to default
        if not sla_policy:
            sla_policy = sla_policies.get(
                "default sla") or list(sla_policies.values())[0]
            matched_sla_name = sla_policy.name if hasattr(
                sla_policy, "name") else sla_policy.get("name")

    status = "on track"
    time_left = sla_policy.resolution_time_minutes if hasattr(
        sla_policy, "resolution_time_minutes") else sla_policy.get("resolution_time_minutes")
    sla_policy_dict = to_dict(sla_policy)
    return {
        "ticket_id": ticket.ticketid,
        "sla_policy": sla_policy_dict,
        "status": status,
        "time_left_minutes": time_left,
        "debug": {
            "createdat": str(created),
            "ticket_priority": ticket.priority,
            "normalized_priority": ticket_priority,
            "available_sla_priorities": debug_priorities,
            "env_priority_levels": PRIORITY_LEVELS,
            "matched_sla_name": matched_sla_name
        }
    }


async def get_sla_violations_controller(db):
    from sla_models import SLAPolicy
    from datetime import datetime, timedelta
    from models import Ticket
    ticket_result = await db.execute(select(Ticket))
    tickets = ticket_result.scalars().all()
    sla_policy_result = await db.execute(select(SLAPolicy))
    all_policies = sla_policy_result.scalars().all()
    # Create case-insensitive mapping
    sla_policies = {}
    for p in all_policies:
        policy_name = str(p.name).strip().lower()
        sla_policies[policy_name] = p
    violations = []
    for ticket in tickets:
        if not ticket.userid:
            continue
        created = ticket.createdat
        resolved = getattr(ticket, "end_date", None) or getattr(
            ticket, "updatedat", None)
        ticket_priority = (ticket.priority or "").strip().lower()
        matched_sla_name = None
        sla_policy = None
        # First try exact match with ticket priority
        if ticket_priority in sla_policies:
            sla_policy = sla_policies[ticket_priority]
            matched_sla_name = sla_policy.name
        else:
            for env_key, env_value in PRIORITY_LEVELS.items():
                if ticket_priority == env_value:
                    if env_key in sla_policies:
                        sla_policy = sla_policies[env_key]
                        matched_sla_name = sla_policy.name
                        break
            if not sla_policy:
                for key, policy in sla_policies.items():
                    if key in ticket_priority or ticket_priority in key:
                        sla_policy = policy
                        matched_sla_name = policy.name
                        break
            if not sla_policy:
                sla_policy = sla_policies.get(
                    "default sla") or list(sla_policies.values())[0]
                matched_sla_name = sla_policy.name if hasattr(
                    sla_policy, "name") else sla_policy.get("name")
        sla_minutes = sla_policy.resolution_time_minutes if hasattr(
            sla_policy, "resolution_time_minutes") else sla_policy.get("resolution_time_minutes")
        if not created or not resolved or not sla_policy:
            continue
        time_to_resolve = (resolved - created).total_seconds() / 60
        within_sla = time_to_resolve <= sla_minutes if sla_minutes else False
        if not within_sla:
            violations.append({
                "ticket_id": ticket.ticketid,
                "user_id": ticket.userid,
                "breached_at": str(resolved),
                "sla_policy": {
                    "sla_id": sla_policy.sla_id,
                    "name": sla_policy.name,
                    "description": sla_policy.description,
                    "response_time_minutes": sla_policy.response_time_minutes,
                    "resolution_time_minutes": sla_policy.resolution_time_minutes
                }
            })
    return violations


async def get_sla_report_controller(db):
    tickets_result = await db.execute(select(Ticket))
    tickets = tickets_result.scalars().all()
    sla_policy_result = await db.execute(select(SLAPolicy))
    all_policies = sla_policy_result.scalars().all()
    # Create case-insensitive mapping
    sla_policies = {}
    for p in all_policies:
        policy_name = str(p.name).strip().lower()
        sla_policies[policy_name] = p
    if not sla_policies:
        return {
            "error": "No SLA policies found. Please create SLA policies for each priority.",
            "total_tickets": 0,
            "tickets_within_sla": 0,
            "tickets_breached": 0,
            "compliance_percentage": 0.0,
            "details": []
        }
    tickets_within_sla = 0
    tickets_breached = 0
    details = []
    now = datetime.utcnow()
    for ticket in tickets:
        created = ticket.createdat
        resolved = getattr(ticket, "end_date", None) or getattr(
            ticket, "updatedat", None)
        ticket_priority = (ticket.priority or "").strip().lower()

        # Map ticket priority to SLA policy using environment variables
        matched_sla_name = None
        sla_policy = None

        # First try exact match with ticket priority
        if ticket_priority in sla_policies:
            sla_policy = sla_policies[ticket_priority]
            matched_sla_name = sla_policy.name
        else:
            # Try mapping from env variables and check if SLA policy exists
            for env_key, env_value in PRIORITY_LEVELS.items():
                if ticket_priority == env_value:
                    # Look for SLA policy with this name (case insensitive)
                    if env_key in sla_policies:
                        sla_policy = sla_policies[env_key]
                        matched_sla_name = sla_policy.name
                        break

            # If still no match, try partial matching on policy names
            if not sla_policy:
                for key, policy in sla_policies.items():
                    if key in ticket_priority or ticket_priority in key:
                        sla_policy = policy
                        matched_sla_name = policy.name
                        break

            # Final fallback to default
            if not sla_policy:
                sla_policy = sla_policies.get(
                    "default sla") or list(sla_policies.values())[0]
                matched_sla_name = sla_policy.name if hasattr(
                    sla_policy, "name") else sla_policy.get("name")

        sla_minutes = sla_policy.resolution_time_minutes if hasattr(
            sla_policy, "resolution_time_minutes") else sla_policy.get("resolution_time_minutes")
        if not created or not resolved or not sla_policy:
            details.append({
                "ticketid": ticket.ticketid,
                "subject": ticket.subject,
                "status": ticket.status,
                "priority": ticket.priority,
                "createdat": str(created),
                "resolvedat": str(resolved) if resolved else None,
                "time_to_resolve_minutes": None,
                "sla_minutes": sla_minutes,
                "within_sla": False,
                "debug": {
                    "ticket_priority": ticket.priority,
                    "normalized_priority": ticket_priority,
                    "available_sla_priorities": list(sla_policies.keys()),
                    "env_priority_levels": PRIORITY_LEVELS,
                    "matched_sla_name": matched_sla_name
                }
            })
            tickets_breached += 1
            continue
        time_to_resolve = (resolved - created).total_seconds() / 60
        within_sla = time_to_resolve <= sla_minutes if sla_minutes else False
        if within_sla:
            tickets_within_sla += 1
        else:
            tickets_breached += 1
        details.append({
            "ticketid": ticket.ticketid,
            "subject": ticket.subject,
            "status": ticket.status,
            "priority": ticket.priority,
            "createdat": str(created),
            "resolvedat": str(resolved),
            "time_to_resolve_minutes": math.ceil(time_to_resolve),
            "sla_minutes": sla_minutes,
            "within_sla": within_sla,
            "debug": {
                "ticket_priority": ticket.priority,
                "normalized_priority": ticket_priority,
                "available_sla_priorities": list(sla_policies.keys()),
                "env_priority_levels": PRIORITY_LEVELS,
                "matched_sla_name": matched_sla_name
            }
        })
    total_tickets = len(tickets)
    compliance_percentage = (tickets_within_sla /
                             total_tickets * 100) if total_tickets > 0 else 0.0

    result = {
        "total_tickets": total_tickets,
        "tickets_within_sla": tickets_within_sla,
        "tickets_breached": tickets_breached,
        "compliance_percentage": round(compliance_percentage, 2),
        "details": details
    }

    return result
