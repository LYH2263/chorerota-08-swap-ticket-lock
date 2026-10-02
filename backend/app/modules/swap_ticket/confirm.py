"""持票确认写库：严格按票面成员交换两格。

确认时绝不按确认瞬间的现场格位重算，只认票面冻结的四元组与双方成员：
- 票面成员与现场不一致（现场漂移）→ member_drift，格表不动
- 票已确认 → already_confirmed，格表不动
- 票已作废 → ticket_void，格表不动
- 任一票面格位现场缺失 → slot_missing，格表不动
"""
from .core import PREVIEW

CONFIRMED = "confirmed"
VOID = "void"


def _slot(assigns, day, task):
    for a in assigns:
        if a["day"] == day and a["task_id"] == task:
            return a
    return None


def confirm_ticket(c, swap_id: int) -> dict:
    sw = c.execute("SELECT * FROM swap_requests WHERE id=?", (swap_id,)).fetchone()
    if not sw:
        raise LookupError("swap_not_found")
    sw = dict(sw)

    if sw["status"] == CONFIRMED:
        raise ValueError("already_confirmed")
    if sw["status"] == VOID:
        raise ValueError("ticket_void")
    if sw["status"] != PREVIEW:
        raise ValueError("not_preview")

    assigns = [dict(r) for r in c.execute(
        "SELECT id,day,task_id,member_id FROM assignments WHERE week_id=?",
        (sw["week_id"],))]

    sa = _slot(assigns, sw["a_day"], sw["a_task"])
    sb = _slot(assigns, sw["b_day"], sw["b_task"])
    if sa is None or sb is None:
        raise ValueError("slot_missing")

    # 票面成员与现场逐一比对：漂移即拒，且先于任何 UPDATE，保证格表不动。
    if sa["member_id"] != sw["a_member"] or sb["member_id"] != sw["b_member"]:
        raise ValueError("member_drift")

    # 按票面成员钉两格（用票面值，而非现场重算）。
    c.execute("UPDATE assignments SET member_id=? WHERE id=?",
              (sw["b_member"], sa["id"]))
    c.execute("UPDATE assignments SET member_id=? WHERE id=?",
              (sw["a_member"], sb["id"]))
    c.execute("UPDATE swap_requests SET status=? WHERE id=?", (CONFIRMED, swap_id))
    return {"ok": True, "swap_id": swap_id, "status": CONFIRMED}


def void_ticket(c, swap_id: int) -> dict:
    sw = c.execute("SELECT id,status FROM swap_requests WHERE id=?", (swap_id,)).fetchone()
    if not sw:
        raise LookupError("swap_not_found")
    if sw["status"] == CONFIRMED:
        raise ValueError("already_confirmed")
    if sw["status"] == VOID:
        raise ValueError("already_void")
    c.execute("UPDATE swap_requests SET status=? WHERE id=?", (VOID, swap_id))
    return {"ok": True, "swap_id": swap_id, "status": VOID}
