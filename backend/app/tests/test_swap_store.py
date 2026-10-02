"""确认写库：预演不改 assignments、确认钉票面成员、漂移/重放/作废拒确认且格表不动。"""
import pytest

from app import seed, swap_store
from app.db import connect


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    seed.init_db()
    c = connect()
    c.executemany(
        "INSERT INTO assignments(week_id,day,task_id,member_id) VALUES (1,?,?,?)",
        [(0, 1, 1), (1, 1, 2), (2, 1, 3)])
    c.commit(); c.close()
    return tmp_path


def grid():
    c = connect()
    rows = c.execute(
        "SELECT day,task_id,member_id FROM assignments WHERE week_id=1 ORDER BY day").fetchall()
    c.close()
    return [(r["day"], r["task_id"], r["member_id"]) for r in rows]


def ticket_row(sid):
    return next(s for s in swap_store.list_tickets() if s["id"] == sid)


def test_preview_leaves_assignments_untouched(db):
    before = grid()
    r = swap_store.create_ticket(1, 0, 1, 1, 1)
    assert r["ok"] and r["status"] == "preview"
    assert (r["a_member"], r["b_member"]) == (1, 2)  # 票面冻结双方成员快照
    assert grid() == before  # 预演不改表
    assert ticket_row(r["id"])["status"] == "preview"  # 不写入已确认态


def test_confirm_pins_ticket_face_members(db):
    t = swap_store.create_ticket(1, 0, 1, 1, 1)
    r = swap_store.confirm_ticket(t["id"])
    assert r["ok"] and r["status"] == "confirmed"
    assert grid() == [(0, 1, 2), (1, 1, 1), (2, 1, 3)]  # 按票面成员交换两格
    row = ticket_row(t["id"])
    assert row["status"] == "confirmed"
    # 看板与列表票面同钉：现场格位 == 票面交换结果
    live = {(d, tk): m for d, tk, m in grid()}
    assert live[(row["a_day"], row["a_task"])] == row["b_member"]
    assert live[(row["b_day"], row["b_task"])] == row["a_member"]


def test_confirm_rejects_drift_and_leaves_grid_untouched(db):
    t = swap_store.create_ticket(1, 0, 1, 1, 1)
    c = connect()  # 发票后现场漂移：A 格被第三方改走
    c.execute("UPDATE assignments SET member_id=3 WHERE week_id=1 AND day=0 AND task_id=1")
    c.commit(); c.close()
    before = grid()
    r = swap_store.confirm_ticket(t["id"])
    assert not r["ok"] and r["reason"] == "drifted"
    assert grid() == before  # 格表不动
    assert ticket_row(t["id"])["status"] == "preview"  # 票未消费


def test_confirm_rejects_replay_and_void(db):
    t = swap_store.create_ticket(1, 0, 1, 1, 1)
    assert swap_store.confirm_ticket(t["id"])["ok"]
    before = grid()
    r = swap_store.confirm_ticket(t["id"])  # 票已确认：重放拒写
    assert not r["ok"] and r["reason"] == "not_preview"
    assert grid() == before

    t2 = swap_store.create_ticket(1, 0, 1, 1, 1)
    assert swap_store.void_ticket(t2["id"])["ok"]
    r2 = swap_store.confirm_ticket(t2["id"])  # 票已作废：拒写
    assert not r2["ok"] and r2["reason"] == "not_preview"
    assert grid() == before


def test_confirm_unknown_ticket(db):
    assert swap_store.confirm_ticket(999)["reason"] == "not_found"
    assert swap_store.void_ticket(999)["reason"] == "not_found"
