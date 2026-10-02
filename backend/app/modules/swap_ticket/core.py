"""预演核：对调台先开预演票。

只校验两格合法性，并把票面四元组 (a_day,a_task,b_day,b_task) 与
双方成员快照 (a_member,b_member) 冻结进 swap_requests。
- 不改 assignments
- status 写 preview，绝不写 confirmed
"""
from app.engines.rota import swap_legal

PREVIEW = "preview"


def _rows(c, week_id):
    return [dict(r) for r in c.execute(
        "SELECT day,task_id,member_id FROM assignments WHERE week_id=?", (week_id,))]


def create_preview(c, week_id: int, *, a_day: int, a_task: int,
                   b_day: int, b_task: int, note: str = "") -> dict:
    """校验并冻结预演票，落一行 status=preview 的票；assignments 不动。"""
    week = c.execute("SELECT id FROM weeks WHERE id=?", (week_id,)).fetchone()
    if not week:
        raise LookupError("week_not_found")

    slots = _rows(c, week_id)
    check = swap_legal(slots, a_day, a_task, b_day, b_task)
    if not check["ok"]:
        raise ValueError(check["reason"])

    cur = c.execute(
        """INSERT INTO swap_requests
           (week_id,a_day,a_task,b_day,b_task,a_member,b_member,status,note)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (week_id, a_day, a_task, b_day, b_task,
         check["a_member"], check["b_member"], PREVIEW, note))
    return {
        "id": cur.lastrowid,
        "week_id": week_id,
        "a_day": a_day, "a_task": a_task, "b_day": b_day, "b_task": b_task,
        "a_member": check["a_member"], "b_member": check["b_member"],
        "status": PREVIEW, "note": note,
    }
