
from fastapi import APIRouter, Depends, HTTPException
from db import get_db
from models import User
from router import get_current_user
from sla_controller import get_sla_policies_controller, create_sla_policy_controller, update_sla_policy_controller, get_ticket_sla_status_controller, get_sla_violations_controller, get_sla_report_controller, update_all_tickets_sla_alignment, to_dict
from schemas import SLAPolicyCreate, SLAPolicyUpdate, SLAPolicyOut, SLAStatusOut, SLAViolationOut, SLAReportOut

sla_router = APIRouter(prefix="/api/sla", tags=["SLA"])


@sla_router.get("/policies", response_model=list[SLAPolicyOut])
async def get_sla_policies(db=Depends(get_db), current_user=Depends(get_current_user)):
    if not current_user.role or current_user.role.name.lower() != "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmin can access this endpoint.")
    return await get_sla_policies_controller(db)


@sla_router.post("/policies", response_model=SLAPolicyOut)
async def create_sla_policy(sla: SLAPolicyCreate, db=Depends(get_db), current_user=Depends(get_current_user)):
    if not current_user.role or current_user.role.name.lower() != "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmin can access this endpoint.")
    return await create_sla_policy_controller(sla, db)


@sla_router.put("/policies/{sla_id}", response_model=SLAPolicyOut)
async def update_sla_policy(sla_id: int, sla: SLAPolicyUpdate, db=Depends(get_db), current_user=Depends(get_current_user)):
    if not current_user.role or current_user.role.name.lower() != "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmin can access this endpoint.")
    return await update_sla_policy_controller(sla_id, sla, db)


@sla_router.get("/violations", response_model=list[SLAViolationOut])
async def get_sla_violations(db=Depends(get_db), current_user=Depends(get_current_user)):
    if not current_user.role or current_user.role.name.lower() != "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmin can access this endpoint.")
    return await get_sla_violations_controller(db)


@sla_router.get("/report", response_model=SLAReportOut)
async def get_sla_report(db=Depends(get_db), current_user=Depends(get_current_user)):
    if not current_user.role or current_user.role.name.lower() != "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmin can access this endpoint.")
    return await get_sla_report_controller(db)


@sla_router.post("/align-tickets")
async def align_all_tickets_sla(db=Depends(get_db), current_user=Depends(get_current_user)):
    if not current_user.role or current_user.role.name.lower() != "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmin can access this endpoint.")
    from fastapi.responses import JSONResponse
    result = await update_all_tickets_sla_alignment(db)
    return JSONResponse(content=to_dict(result))


@sla_router.get("/ticket/{ticket_id}/status")
async def get_ticket_sla_status(ticket_id: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    # Only allow users to access their own ticket, or admins/superadmins
    from models import Ticket
    ticket = await db.execute(__import__('sqlalchemy').select(Ticket).where(Ticket.ticketid == ticket_id))
    ticket_obj = ticket.scalar_one_or_none()
    if not ticket_obj:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not getattr(current_user, 'isadmin', False) and not getattr(current_user, 'is_superadmin', False):
        if ticket_obj.userid != current_user.userid:
            raise HTTPException(status_code=403, detail="Not authorized to view this ticket's SLA status")
    from fastapi.responses import JSONResponse
    result = await get_ticket_sla_status_controller(ticket_id, db)
    return JSONResponse(content=to_dict(result))
