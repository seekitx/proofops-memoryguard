# Casework 2.2：真实接口与工具接入手册

## A. GitHub 与 Base 只读证据

本包实现的是“你的软件可以调用的真实接口适配器”，不是本轮已经调用过你的真实工单/链上交易。
GitHub 端只允许明确仓库；Base 端只允许配置的 HTTPS RPC。HTTP 不跟随重定向，不继承代理环境变量。
GitHub issue 正文、标题、作者不进入持久业务明文；Base 不保存可执行 calldata，不接受任意 RPC 方法。

`SourceSpec.independence_group` 是你声明的来源运营分组，不是程序验证过的独立组织。
使用 GitHub 与 Base 两源也不能自动证明同一事实；关联关系必须由调查员/审核员确认。
`TTL` 是刷新规则，不代表 TTL 内不可能发生重组、工单修改或其他变化。
它限制的是观察缓存时间，不是保证工单或交易本身发生在最近几分钟。
Base 采集器验证链/哈希/目标/区块，不声称解析任意合约 ABI 的方法或核对 USD 与 token 金额；这些业务关联仍要明确审核。
HTTP 还有分块读取的总时长检查；底层阻塞操作受 httpx 的连接/读取超时约束，不把它宣传成实时系统硬截止。

## B. Virtuals：请求—任务—复核消息的绑定

### 本次对照的官方版本

官方仓库：`Virtual-Protocol/acp-cli`。
核验源码提交：`dd7af20c8ddf0bb4fac1b3fb51aa040c2836a730`。
该提交的 package.json 标记 CLI `1.0.35`，Node 要求 `>=20.19.0`。
使用与此提交响应合同一致的部署；后续 CLI 更新必须重新核对解析器，不能默认兼容。

### 本包实际可执行的 CLI 命令

Python 适配器只执行：

```text
acp job history --job-id <digits> --chain-id <8453|84532> --json
```

它不执行 create-job、fund、complete、wallet 或 trade。
命令使用 argv 数组而不是 shell 字符串，输出总量和时间有上限，错误文本不会回传给业务客户端。

官方 v2 history 是未包裹 JSON：

```json
{
  "jobId": "42",
  "chainId": 84532,
  "protocol": "v2",
  "status": "completed",
  "entryCount": 3,
  "entries": []
}
```

这里的 42 和空 entries 只是结构示意，**不能通过实际验证**。
解析器要求 entryCount 与实际记录数量一致，status 与最后可识别的系统事件一致。
拒绝 legacy、未知结构、错误链、错误 job ID，而不是猜测字段名后假装成功。

### 本地创建复核请求

调查员调用：

```text
POST /api/v2/cases/{case_id}/partner-review
```

请求含普通 Command 字段以及 `report_id`。
服务器验证报告仍然有效、报告归属调查员、scope 与 Virtuals 配置相符。
保存的计划绑定 `report_root / basis_hash / case_version / source_bundle_root / provider / client / chain / offering`。
配置变化、报告过期、case 重开后，不会继续把老计划当成当前计划。

保存响应到自己选择的私有本地文件，然后：

```bash
python scripts/casework_acp_handoff.py --plan /private/review-plan.json
```

脚本只打印按官方 CLI 语法构造的创建命令；不会执行。
你在独立操作员终端核对 offering、价格、网络、订阅和钱包后，才实际创建与处理任务。
`max_budget_micros` 是你声明的 USDC 微单位上限，**当前代码不强制约束官方 CLI 的远端报价/订阅计费**。
因此不得把它宣传成“服务器已保证最多花 0.1 USDC”；创建、出资、完成均应按外部钱包/CLI 的实际确认处理。

### 对接的 provider 需要满足什么合同

不是任意公共 Agent 都能直接接入。你选定的 offering 必须接受本包打印的 requirements JSON，并发送下面格式的 ACP 消息：

```json
{
  "schema_version": "memoryguard-review/1",
  "request_hash": "替换为当前计划真实64位哈希",
  "recommendation": "MORE_EVIDENCE",
  "finding_codes": ["MANUAL_REVIEW_REQUIRED"]
}
```

允许 recommendation：`KEEP_BLOCKED / MORE_EVIDENCE / REVIEW_COMPLETED`。
允许 finding_codes：`SOURCE_CONFLICT / INSUFFICIENT_EVIDENCE / STALE_SOURCE / CONSISTENT_SNAPSHOTS / MANUAL_REVIEW_REQUIRED`。
Provider 应发送这份 JSON 消息，再按其正常流程提交 deliverable。不要假设 SDK 内部所有 deliverable 事件都有相同字段。

核验同时要求：

1. 客户的 `contentType: requirement` 消息来自配置的客户地址，内容哈希与本地 requirements 完全一致。
2. 复核 JSON 消息来自配置的 provider 地址，不能由客户自己发送来冒充。
3. 请求哈希准确，字段与枚举严格匹配。
4. completed 必须与 system event 历史一致，且有匹配 provider 复核消息。
5. 同一个 job 不得被当前租户另一份计划重复认领。

结果标签为 `ACP_CLI_HISTORY_BOUND`，不是独立链上回执认证。
即便 complete_review_observed=true，case 仍不会自动解除，系统也不会把它写成官方已授予倍率。
旧任务可以保留为历史，但 `current=false` 时不能成为当前工作成功的证明。

### 本机或可选容器部署

Python 默认镜像不含 Node/ACP。不要只填一个路径就认为 CLI 已安装。
推荐先在隔离、无主要钱包秘密的构建环境审查并构建固定提交，保留 lockfile 与依赖审计结果。
示意流程（由操作员明确执行，不属于本次已执行动作）：

```bash
git clone https://github.com/Virtual-Protocol/acp-cli /operator/acp
git -C /operator/acp checkout dd7af20c8ddf0bb4fac1b3fb51aa040c2836a730
cd /operator/acp
npm ci
npm run build
npm audit
```

上面的 install/build 会运行已审查项目的构建步骤。必须在没有主钱包/生产凭证的环境运行；本包没有执行或保证审计零问题。

- 本机：安装一个非符号链接、不可被组/其他人写入的 wrapper；填写实际 executable、HOME 与 wrapper SHA-256。
- 容器：可选 `Dockerfile.acp` 只提供 Node + Python，不复制 ACP 或其认证数据。
- 把审查后的 CLI tree 按只读方式挂载到 `/opt/acp`；把独立 CLI HOME 挂载到配置的目录。
- 使用 `tools/acp-history-wrapper.example.sh`，审查后放入只读受控位置并计算其实际 SHA-256。
- 容器中的 UID 10001 必须能读取所需配置，但不要给凭证目录 0777。
- Python 会在隔离的 CLI HOME 作为 cwd 运行，避免 CLI 从应用项目的 `.env` 自动读取无关秘密。

Wrapper 的哈希只固定 wrapper 本身，**不等于对整个 Node 依赖树的供应链认证**。
CLI 及其依赖是新的信任边界，可能进行自己的认证刷新；不要挂入主钱包种子、通用密钥仓或无关云凭证。
本包没有为你注册 Agent，没有实际 ACP job，没有付款记录。

## C. 只读 MCP

模块：`python -m proofops_casework.mcp_readonly`。
支持 MCP 2025-06-18 的 stdio initialize/ping/tools 子集，标准输出仅 JSON-RPC。
没有 Streamable HTTP 服务、订阅、资源变更通知或写工具，也不声称已做完整协议一致性认证。

使用单独 viewer 角色，给 MCP 进程设置：

```text
MEMORYGUARD_API_ORIGIN=https://你的实际MemoryGuard域名
MEMORYGUARD_VIEWER_TOKEN=单独的只读凭证
```

本机演示允许 loopback HTTP。其他 HTTP origin 被拒绝。
凭证必须通过你的客户端安全环境注入，不要提交到仓库或贴进公共配置截图。

工具：

| 工具 | 内容 |
|---|---|
| memoryguard_overview | 当前作用域任务、风险、角色可见状态 |
| memoryguard_recovery | 依赖顺序恢复建议，只读 |
| memoryguard_impact | 全祖先图与有效性 |
| memoryguard_case_history | case 的版本历史 |
| memoryguard_sources | 当前来源回执、时效、覆盖 |
| memoryguard_report_sources | 某份报告实际使用的历史来源快照 |
| memoryguard_partner_review | 保存的 ACP 请求与观察 |

标准 MCP 客户端配置中 command 使用你的 Python 可执行文件、args 使用 `-m proofops_casework.mcp_readonly`。
在完整项目安装环境执行，不需要另外安装 MCP Python SDK。
实际客户端仍需要自行验收；annotations 是提示，真正限制来自这个服务根本没有任何写命令及服务器 RBAC。

## D. 公开实验与评委入口

`CASEWORK_SOURCE_EXPERIMENT_PATH` 只能指向专门生成、明确愿意公开的合成实验 JSON，不是 registry 或数据库路径。
公开 API 仅读取已定义字段并做类型/数量/代码版本检查，不把任意文件原样回传。

显示状态包括：

- `NOT_RECORDED`：没有记录。
- `INVALID_EXPORT`：格式或内容不合要求。
- `TEST_DOUBLE_RECORD`：使用测试存储，不是官方 SDK 结果。
- `HISTORICAL_OR_UNCOMMITTED`：代码不一致或未干净提交。
- `CHECKS_INCOMPLETE`：有自录结果，但指定检查未全通过。
- `CURRENT_SYNTHETIC_SELF_RECORD`：当前代码的自录合成实验；不是独立评审、真实接口访问或收益证明。

原有 Base audit anchor 仍需由钱包进行真实交互。Base 只读采集器读取一笔别的交易不自动获得伙伴加分。

## E. 技术来源（2026-09-05 核验）

- 官方比赛规则：https://hack.sibyllabs.org/rules
- 官方提交入口说明：https://hack.sibyllabs.org/submissions
- GitHub issue API：https://docs.github.com/en/rest/issues/issues#get-an-issue
- Base receipt：https://docs.base.org/base-chain/api-reference/ethereum-json-rpc-api/eth_getTransactionReceipt
- MCP stdio：https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
- ACP 固定版本 README：https://github.com/Virtual-Protocol/acp-cli/blob/dd7af20c8ddf0bb4fac1b3fb51aa040c2836a730/README.md
- ACP history：https://github.com/Virtual-Protocol/acp-cli/blob/dd7af20c8ddf0bb4fac1b3fb51aa040c2836a730/src/commands/job.ts
- ACP create：https://github.com/Virtual-Protocol/acp-cli/blob/dd7af20c8ddf0bb4fac1b3fb51aa040c2836a730/src/commands/client.ts
- ACP provider submit：https://github.com/Virtual-Protocol/acp-cli/blob/dd7af20c8ddf0bb4fac1b3fb51aa040c2836a730/src/commands/provider.ts

没有把对手宣传、官方示例或本地计划当成本项目已经完成的证据。
