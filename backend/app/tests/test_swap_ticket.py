"""预演票锁定测例：
- 预演不改表（只冻结票面，assignments 不变、无 confirmed）
- 确认钉票面（按票面成员交换两格，不按现场重算）
- 现场漂移拒确认（票面成员≠现场则失败，格表不动）
- 重复确认 / 已作废拒绝
"""
import os
import pytest
from app.db import connect
from app import seed
from app.modules.swap_ticket.core import create_preview
from app.modules.swap_ticket.confirm import confirm_ticket, void_ticket


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    seed.init_db()
    c = connect()
    # week 1 落两格：D0/T1=成员1(阿明)，D1/T1=成员2(小雨)
    c.execute("DELETE FROM assignments WHERE week_id=1")
    c.execute("INSERT INTO assignments(week_id,day,task_id,member_id) VALUES (1,0,1,1)")
    c.execute("INSERT INTO assignments(week_id,day,task_id,member_id) VALUES (1,1,1,2)")
    c.commit(); c.close()
    return connect


def _members(c):
    return {r["day"]: r["member_id"]
            for r in c.execute("SELECT day,member_id FROM assignments WHERE week_id=1")}


def test_preview_does_not_change_grid(db):
    c = db()
    before = _members(c)
    t = create_preview(c, 1, a_day=0, a_task=1, b_day=1, b_task=1)
    c.commit()
    assert t["status"] == "preview"
    # 票面冻结双方成员快照
    assert t["a_member"] == 1 and t["b_member"] == 2
    # assignments 原样不动，没有任何 confirmed 票
    assert _members(c) == before
    assert c.execute("SELECT COUNT(*) n FROM swap_requests WHERE status='confirmed'").fetchone()["n"] == 0
    c.close()


def test_confirm_pins_ticket_members(db):
    c = db()
    t = create_preview(c, 1, a_day=0, a_task=1, b_day=1, b_task=1)
    c.commit()
    confirm_ticket(c, t["id"])
    c.commit()
    after = _members(c)
    # 按票面钉两格：成员1↔成员2
    assert after == {0: 2, 1: 1}
    assert c.execute("SELECT status FROM swap_requests WHERE id=?", (t["id"],)).fetchone()["status"] == "confirmed"
    c.close()


def test_member_drift_rejects_confirm_and_grid_untouched(db):
    c = db()
    t = create_preview(c, 1, a_day=0, a_task=1, b_day=1, b_task=1)
    c.commit()
    # 预演后现场漂移：D0/T1 被别的流程改成成员3（爷爷），票面仍记成员1
    c.execute("UPDATE assignments SET member_id=3 WHERE week_id=1 AND day=0 AND task_id=1")
    c.commit()

    with pytest.raises(ValueError, match="member_drift"):
        confirm_ticket(c, t["id"])
    c.rollback()

    # 格表维持漂移后的现场，确认没有把任何格改回票面值
    assert _members(c) == {0: 3, 1: 2}
    assert c.execute("SELECT status FROM swap_requests WHERE id=?", (t["id"],)).fetchone()["status"] == "preview"
    c.close()


def test_confirm_twice_rejected_and_grid_untouched(db):
    c = db()
    t = create_preview(c, 1, a_day=0, a_task=1, b_day=1, b_task=1)
    c.commit()
    confirm_ticket(c, t["id"]); c.commit()
    with pytest.raises(ValueError, match="already_confirmed"):
        confirm_ticket(c, t["id"])
    c.rollback()
    assert _members(c) == {0: 2, 1: 1}
    c.close()


def test_void_ticket_rejects_confirm(db):
    c = db()
    t = create_preview(c, 1, a_day=0, a_task=1, b_day=1, b_task=1)
    c.commit()
    void_ticket(c, t["id"]); c.commit()
    with pytest.raises(ValueError, match="ticket_void"):
        confirm_ticket(c, t["id"])
    c.rollback()
    assert _members(c) == {0: 1, 1: 2}  # 格表不动
    c.close()
