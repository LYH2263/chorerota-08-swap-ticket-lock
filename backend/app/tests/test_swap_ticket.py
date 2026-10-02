"""预演核：冻结票面、确认写集钉票面、现场漂移拒确认。"""
from app.engines.swap_ticket import (
    issue_preview, confirm_guard, confirm_writes, face_members,
)

SLOTS = [
    {"day": 0, "task_id": 1, "member_id": 1},
    {"day": 1, "task_id": 1, "member_id": 2},
    {"day": 2, "task_id": 1, "member_id": 3},
]


def _ticket(status="preview"):
    r = issue_preview(SLOTS, 0, 1, 1, 1)
    assert r["ok"]
    return {**r["ticket"], "status": status}


def test_preview_freezes_face_without_mutating_slots():
    snapshot = [dict(s) for s in SLOTS]
    r = issue_preview(SLOTS, 0, 1, 1, 1)
    assert r["ok"]
    assert r["ticket"] == {"a_day": 0, "a_task": 1, "b_day": 1, "b_task": 1,
                           "a_member": 1, "b_member": 2}
    assert SLOTS == snapshot  # 预演不改表


def test_preview_rejects_illegal_swap():
    r = issue_preview(SLOTS, 0, 1, 9, 1)
    assert not r["ok"] and r["reason"] == "slot_missing"


def test_confirm_writes_pin_face_members():
    # 写集只来自票面：A 格钉 b_member，B 格钉 a_member
    assert confirm_writes(_ticket()) == {(0, 1): 2, (1, 1): 1}
    assert face_members(_ticket()) == {(0, 1): 1, (1, 1): 2}


def test_guard_accepts_matching_live_grid():
    assert confirm_guard(_ticket(), SLOTS)["ok"]


def test_guard_rejects_drift():
    drifted = [dict(s) for s in SLOTS]
    drifted[0]["member_id"] = 3  # 现场格位在发票后被改动
    r = confirm_guard(_ticket(), drifted)
    assert not r["ok"] and r["reason"] == "drifted"


def test_guard_rejects_missing_slot():
    r = confirm_guard(_ticket(), SLOTS[1:])
    assert not r["ok"] and r["reason"] == "drifted"


def test_guard_rejects_non_preview_ticket():
    for st in ("confirmed", "void"):
        r = confirm_guard(_ticket(status=st), SLOTS)
        assert not r["ok"] and r["reason"] == "not_preview"
