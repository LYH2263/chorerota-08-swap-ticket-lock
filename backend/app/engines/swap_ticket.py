"""Swap preview tickets (对调预演票).

Pure core — no DB. A preview ticket freezes the swap's four-tuple
(a_day, a_task, b_day, b_task) plus the snapshot of both assignees
(a_member, b_member) at issue time. Confirm later writes the ticket-face
members, never recomputing from the live grid.
"""
from app.engines.rota import swap_legal

PREVIEW = "preview"
CONFIRMED = "confirmed"
VOID = "void"


def issue_preview(slots: list[dict], a_day: int, a_task: int, b_day: int, b_task: int) -> dict:
    """Validate legality against current slots and freeze the ticket face.

    Read-only: `slots` is never mutated, nothing is confirmed here.
    """
    check = swap_legal(slots, a_day, a_task, b_day, b_task)
    if not check["ok"]:
        return {"ok": False, "reason": check["reason"]}
    return {
        "ok": True,
        "ticket": {
            "a_day": a_day,
            "a_task": a_task,
            "b_day": b_day,
            "b_task": b_task,
            "a_member": check["a_member"],
            "b_member": check["b_member"],
        },
    }


def face_members(ticket: dict) -> dict:
    """The pinned face: which member the ticket froze on each of its two cells."""
    return {
        (ticket["a_day"], ticket["a_task"]): ticket["a_member"],
        (ticket["b_day"], ticket["b_task"]): ticket["b_member"],
    }


def confirm_guard(ticket: dict, slots: list[dict]) -> dict:
    """Gate a confirm: ticket must still be a live preview and the grid must
    not have drifted from the ticket face. Failing the guard changes nothing.
    """
    if ticket.get("status") != PREVIEW:
        return {"ok": False, "reason": "not_preview"}
    face = face_members(ticket)
    live = {}
    for s in slots:
        key = (s["day"], s["task_id"])
        if key in face:
            live[key] = s["member_id"]
    if live != face:
        return {"ok": False, "reason": "drifted"}
    return {"ok": True}


def confirm_writes(ticket: dict) -> dict:
    """The pinned write set: exchange the two ticket-face members between the
    two cells. Sourced only from the ticket — live slots are never read here.
    """
    return {
        (ticket["a_day"], ticket["a_task"]): ticket["b_member"],
        (ticket["b_day"], ticket["b_task"]): ticket["a_member"],
    }
