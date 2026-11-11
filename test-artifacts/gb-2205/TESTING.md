# 运行恢复与重复投递验收

## 范围

验证工况计算在领取后被中断时自动恢复、沿用原运行记录完成，以及重复投递、并发领取和过期结果的处理。测试使用独立 SQLite 数据库和内存队列替身，不连接真实 PostgreSQL/Redis，也不改动演示数据。

## 运行方式

```sh
pip install -r backend/requirements.txt pytest
PYTHONPATH=backend python -m pytest -q test-artifacts/gb-2205
```

测试文件为 `test_recovery.py`，会话开始前会重建 `/tmp/qingyu-run-recovery-tests.db`。

## 场景与断言

| 场景 | 断言 |
|---|---|
| 领取后中断 | worker A 领取后不发布；租约过期后 worker B 按同一 `run_id` 恢复，`attempts` 从1变2，运行最终 `completed`，运行表仍只有一条记录 |
| 重复投递 | 已 `completed` 的运行再次投递不会重新计算，`attempts`、结果均保持原值 |
| 并发领取 | 两个会话同时领取同一运行，只有一个拿到 `claim_token`，`attempts` 只增加一次 |
| 过期结果晚到 | worker B 已发布新结果后，worker A 的旧令牌发布被拒绝，结果仍为 B 的新值 |
| 失败原因 | 计算参数错误时运行置 `failed`，`error` 含可读原因并可从序列化结果读取；重复投递不会清除原因或盲目重试 |
| 复核与归档 | 运行完成后创建复核并归档报告；重复投递不改变运行结果，复核仍引用原 `run_id`，报告快照保持原值 |
| 队列消息丢失 | 模拟 BLPOP 取走消息后进程中断（数据库仍为 `queued`），worker 扫描直接恢复并完成 |
| 连续中断上限 | 连续中断达到 `RUN_MAX_ATTEMPTS` 后运行置 `failed`，记录可读原因，不再无限挂起 |

## 最近一次结果

```
........                                                                 [100%]
8 passed in 1.18s
```

## 实现要点

- `backend/src/services/run_service.py`：条件 `UPDATE` 原子领取并递增 `attempts`；`claim_token` 作为发布围栏；`publish_result` / `publish_failure` 仅在令牌仍匹配时生效。
- `backend/src/worker.py`：队列消息仅作唤醒提示，每轮还会扫描数据库中的 `queued` 运行和租约已过期的 `running` 运行，因此 BLPOP 后中断、领取后中断都能恢复。
- `backend/src/models/run.py` 与 `backend/migrations/002_run_claims.sql`：新增领取字段；存量库启动时做追加式升级，运行 id、结果、复核和报告快照不受影响。
- 默认 `RUN_LEASE_SECONDS=15`、`RUN_MAX_ATTEMPTS=5`，可由环境变量调整。
