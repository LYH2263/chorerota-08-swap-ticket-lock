# Chorerota · 家庭值日轮转

底座：成员+任务 → round-robin 生成周表 → 对调台发预演票（冻结票面四元组与双方成员，不改表）→ 持票确认钉票面改表（现场漂移/票已确认/已作废则拒写）。

| 服务 | 端口 |
| --- | --- |
| 前端 | 5100 |
| API | 10100 |

```bash
docker compose up --build
pytest backend/app/tests
```

种子含 clean/dirty。0-1 空桩：`streak_badge` / `skip_week` / `chore_photo`。
