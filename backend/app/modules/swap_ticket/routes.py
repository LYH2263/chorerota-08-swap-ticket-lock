"""路由分文件：预演开票、列表、持票确认/作废。"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import connect
from .core import create_preview
from .confirm import confirm_ticket, void_ticket

router = APIRouter(prefix="/api", tags=["swap_ticket"])


class TicketBody(BaseModel):
    a_day: int; a_task: int; b_day: int; b_task: int; note: str = ""


@router.post("/weeks/{week_id}/swaps")
def preview_swap(week_id: int, body: TicketBody):
    """对调台发预演票：只校验+冻结票面，不改 assignments。"""
    c = connect()
    try:
        ticket = create_preview(
            c, week_id, a_day=body.a_day, a_task=body.a_task,
            b_day=body.b_day, b_task=body.b_task, note=body.note)
        c.commit()
    except LookupError as e:
        c.close(); raise HTTPException(404, str(e))
    except ValueError as e:
        c.close(); raise HTTPException(400, str(e))
    c.close()
    return ticket


@router.get("/swaps")
def list_swaps():
    c = connect()
    rows = [dict(r) for r in c.execute("""
        SELECT s.*, ma.name AS a_member_name, mb.name AS b_member_name
        FROM swap_requests s
        LEFT JOIN members ma ON ma.id = s.a_member
        LEFT JOIN members mb ON mb.id = s.b_member
        ORDER BY s.id DESC""")]
    c.close()
    return rows


@router.post("/swaps/{swap_id}/confirm")
def confirm_swap(swap_id: int):
    """持票确认：按票面成员交换两格；漂移/已确认/已作废则失败且格表不动。"""
    c = connect()
    try:
        result = confirm_ticket(c, swap_id)
        c.commit()
    except LookupError as e:
        c.close(); raise HTTPException(404, str(e))
    except ValueError as e:
        c.close(); raise HTTPException(400, str(e))
    c.close()
    return result


@router.post("/swaps/{swap_id}/void")
def void_swap(swap_id: int):
    c = connect()
    try:
        result = void_ticket(c, swap_id)
        c.commit()
    except LookupError as e:
        c.close(); raise HTTPException(404, str(e))
    except ValueError as e:
        c.close(); raise HTTPException(400, str(e))
    c.close()
    return result
