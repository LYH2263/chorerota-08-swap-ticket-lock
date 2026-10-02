"""Swap ticket persistence (确认写库).

Owns every DB touch of the swap-desk flow: issuing preview rows, the
confirm transaction that writes the pinned members into assignments, and
voiding. Routes stay thin; the ticket math lives in engines/swap_ticket.
"""
from app.db import connect
from app.engines import swap_ticket as core


def _live_slots(c, week_id: int) -> list[dict]:
    rows = c.execute(
        "SELECT day,task_id,member_id FROM assignments WHERE week_id=?", (week_id,))
    return [dict(r) for r in rows]


def create_ticket(week_id: int, a_day: int, a_task: int, b_day: int, b_task: int,
                  note: str = "") -> dict:
    """Issue a preview ticket: validate + freeze the face. Assignments untouched."""
    c = connect()
    try:
        prev = core.issue_preview(_live_slots(c, week_id), a_day, a_task, b_day, b_task)
        if not prev["ok"]:
            return {"ok": False, "reason": prev["reason"]}
        t = prev["ticket"]
        cur = c.execute(
            "INSERT INTO swap_requests(week_id,a_day,a_task,b_day,b_task,a_member,b_member,status,note)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (week_id, t["a_day"], t["a_task"], t["b_day"], t["b_task"],
             t["a_member"], t["b_member"], core.PREVIEW, note))
        c.commit()
        return {"ok": True, "id": cur.lastrowid, "status": core.PREVIEW, **t}
    finally:
        c.close()


def confirm_ticket(swap_id: int) -> dict:
    """Confirm a held ticket: write the ticket-face members into the two cells.

    Refuses (grid untouched) when the ticket is not a live preview or the
    live grid has drifted from the frozen face.
    """
    c = connect()
    try:
        sw = c.execute("SELECT * FROM swap_requests WHERE id=?", (swap_id,)).fetchone()
        if not sw:
            return {"ok": False, "reason": "not_found"}
        ticket = dict(sw)
        guard = core.confirm_guard(ticket, _live_slots(c, sw["week_id"]))
        if not guard["ok"]:
            return {"ok": False, "reason": guard["reason"]}
        for (day, task), member in core.confirm_writes(ticket).items():
            c.execute(
                "UPDATE assignments SET member_id=? WHERE week_id=? AND day=? AND task_id=?",
                (member, sw["week_id"], day, task))
        c.execute("UPDATE swap_requests SET status=? WHERE id=?", (core.CONFIRMED, swap_id))
        c.commit()
        return {"ok": True, "swap_id": swap_id, "week_id": sw["week_id"],
                "status": core.CONFIRMED,
                "a_member": ticket["a_member"], "b_member": ticket["b_member"]}
    finally:
        c.close()


def void_ticket(swap_id: int) -> dict:
    """Void a preview ticket. Already confirmed/void tickets stay as they are."""
    c = connect()
    try:
        sw = c.execute("SELECT * FROM swap_requests WHERE id=?", (swap_id,)).fetchone()
        if not sw:
            return {"ok": False, "reason": "not_found"}
        if sw["status"] != core.PREVIEW:
            return {"ok": False, "reason": "not_preview"}
        c.execute("UPDATE swap_requests SET status=? WHERE id=?", (core.VOID, swap_id))
        c.commit()
        return {"ok": True, "swap_id": swap_id, "status": core.VOID}
    finally:
        c.close()


def list_tickets() -> list[dict]:
    c = connect()
    try:
        return [dict(r) for r in c.execute("SELECT * FROM swap_requests ORDER BY id DESC")]
    finally:
        c.close()
