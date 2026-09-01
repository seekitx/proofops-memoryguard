# MemoryGuardAgent 对抗式设计决议

日期：2026-09-01（正式 build window 内）

状态：已按本文落地源码；尚未编译、未运行测试、未启动真实模型、未做运行证据。

## 三方争论

本轮由三个独立 Agent 从不同角度攻击方案：

1. **评委怀疑者**：如果只是 `guard.decide()` 后让模型写解释，删掉 Agent 后产品行为不变，评委有理由认为它是“规则服务套壳”。
2. **安全实现者**：模型不能提交 verdict、目标、金额或工具参数；生产环境不能静默使用假模型；仓库不应存在付款、签名或广播 Adapter。
3. **官方规则研究者**：核心资格门槛仍是 load-bearing Sibyl、fresh process/session recall、deletion test 和可核验提交材料。Base 只有真实 exercised onchain action 才值得申报。

一致意见：保留 `MemoryGuard` 作为唯一授权闸门，在它上面增加一个深 Module：`MemoryGuardAgent`。Agent 管理目标、状态、模型计划、封闭工具集合、真实工具轨迹、跨进程检查和 Base 回执恢复；模型只能缩小安全动作，不能扩大权限。

## 最小外部接口

```python
run = agent.run(GuardedPaymentGoal(intent))
same_run = agent.inspect(run.run_id)
updated = agent.resume(run.run_id, AgentHumanSignal(...))
```

- `run`：强制经过 `MemoryGuard.decide`，然后才调用模型和安全工具。
- `inspect`：只读 Sibyl run ledger，不重跑模型、不重做决定、不改变状态。
- `resume`：只接受取消、准备零金额 proof anchor，或“人类钱包已经产生的锚定交易哈希”；不接受改 verdict、换目标、提高金额。`DENY` proof 也可锚定，但状态仍是 `BLOCK_AND_ESCALATE`，永远不会因此变成可执行。

## 不可绕过的状态映射

| MemoryGuard verdict | Agent state | 实际允许工具 |
|---|---|---|
| `READY` | `AWAIT_FINALIZE` | 必选 `human_review.prepare`；模型可选 `causal_evidence_brief.prepare` |
| `DENY` | `BLOCK_AND_ESCALATE` | 必选 `operator_escalation.create`；模型可选 `causal_evidence_brief.prepare` |
| `NEEDS_HUMAN` | `AWAIT_HUMAN_REVIEW` | 必选 `operator_escalation.create`；模型可选 `causal_evidence_brief.prepare` |
| Sibyl 缺失或损坏 | HTTP 503 / 启动失败 | 无 |

模型返回的工具名与上表求交集。未知工具会留下 `SUPPRESSED / tool_not_registered` 轨迹。`payment_execution`、`sign`、`broadcast` 从未注册，因此不是依赖提示词来阻止付款。

## Production 与测试边界

- Production Adapter：`HttpModelAdapter`，调用配置的 HTTPS 结构化模型端点。
- 开发/测试 Adapter：`DeterministicModelAdapter`，运行结果明确标记 `deterministic_test_planner`。
- `APP_ENV=production` 时，若不是 `AGENT_MODEL_MODE=remote`，应用拒绝启动。
- Agent run、状态、executor 生成的 trace 由 `SibylAgentRunAdapter` 写入官方 Sibyl SDK 管理的 entity/event；生产环境拒绝内存 ledger。

模型只看到脱敏后的决策上下文：verdict、reason code、causal memory ID、目标哈希和金额。它看不到原始 Observation、供应商恶意文字、proof nonce、密钥或钱包对象。

模型输出的自由文字不会作为操作指引持久化或显示；trace 只保存其哈希。页面上的解释和下一步来自 verdict + 实际安全动作回执的确定性文案。模型的真实行为杠杆是：在 MemoryGuard 允许的范围内选择是否生成可选 causal evidence brief；模型失败时该可选工具不会调用。

同一 `run_id` 在同一持久盘上由跨进程文件锁串行处理；ledger entity 还保存完整 envelope hash，读取时重验 request/run 绑定、decision proof、工具权限、action receipt、trace output hash 和 Base 状态。它属于本地完整性检查，不是独立防篡改证明：Base 当前锚定的是 decision proof root，不是整个 Agent tool trace。

## 评委应看到的行为差异

Session A：

```text
memoryguard.decide           CALLED -> SUCCEEDED(READY)
model.plan                  CALLED -> SUCCEEDED
human_review.prepare        CALLED -> SUCCEEDED
operator_escalation.create  SUPPRESSED(verdict_ready)
causal_evidence_brief       CALLED -> SUCCEEDED (if requested by model)
```

完整重启 API/Agent 后的 Session B：

```text
memoryguard.decide           CALLED -> SUCCEEDED(DENY)
model.plan                  CALLED -> SUCCEEDED
human_review.prepare        SUPPRESSED(verdict_deny)
operator_escalation.create  CALLED -> SUCCEEDED
causal_evidence_brief       CALLED -> SUCCEEDED (if requested by model)
```

两次结果必须展示相同 `action_fingerprint`、不同 `runtime_instance_id`、Session B 的 `cross_session: true` 和 causal dispute memory ID。

## 已知未完成门槛

源码已经形成上述边界，但以下证据不能靠源码声称完成：

- 安装依赖、运行测试和 deletion test；
- 配置并实际调用真实外部模型；
- 停掉整个 API 后重启，录制 Session B；
- 部署 Base 合约并由用户钱包签署零金额证明锚定交易；
- 后端独立验证回执；
- 公网部署、2–5 分钟未剪辑视频、两条公开帖、build page 最终提交。

这些事项继续由 `submission/status.json` 和 `scripts/submission_gate.py` 作为声明边界。
