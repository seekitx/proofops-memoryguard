# Sibyl Labs Memory Hackathon 官方规则刷新（2026-09-05）

## 先说结论

截至 **2026-09-05（中国标准时间，UTC+8）**，Sibyl Labs Hackathon 官方网站仍明确：

1. **Sibyl Memory 必须是核心功能的必经之路**。新会话必须读回以前的状态，并真正改变决策、动作或结果；删掉 Sibyl Memory 后如果核心功能仍然正常，会在资格门阶段直接淘汰。[官方首页](https://hack.sibyllabs.org/) [官方规则](https://hack.sibyllabs.org/rules)
2. **最终截止时间是 2026-09-10 23:59 UTC**，换算成北京时间是 **2026-09-11 07:59**。只有已报名的队伍能通过报名后收到的私有 build page（作品提交页）提交，必须在截止前标记 `ready`。[官方提交说明](https://hack.sibyllabs.org/submissions)
3. 评分顺序是：**先过资格门，再评 100 分主体，再加最多 10 分 PMF（产品市场匹配）奖励，最后乘 partner 倍率**。公式是 `(主体分 + PMF) × 倍率`。[官方规则](https://hack.sibyllabs.org/rules)
4. Base 和 Virtuals 不是参赛必选项。判定为 1 个真实 partner stack 时是 `x1.15`，2 个是 `x1.25` 上限；只装包、挂 Logo、写合约但不在演示中真正运行，不计分。[官方首页评分说明](https://hack.sibyllabs.org/#scoring) [官方规则](https://hack.sibyllabs.org/rules)
5. 当前最大的公开规则空白是：**Base 公开规则没有写清 Base Sepolia 测试网是否计倍率，也没有写必须 mainnet（主网）**。所以不能仅根据公开规则断言测试网或主网一定算分，需要向主办方或 Base workshop 书面确认。[官方规则](https://hack.sibyllabs.org/rules)

## 研究边界与证据等级

- **已当日核验**：Sibyl Hackathon 官方首页、Rules、Submissions、Register 和 Leaderboard，访问日期均为 2026-09-05。
- **已当日核验，但不可公开链接**：已注册队伍的官方私有 build page。该页明示“任何拿到链接的人都能编辑”，因此本文不记录私有 URL、编辑链接或任何账号信息。公开的提交流程见[官方提交说明](https://hack.sibyllabs.org/submissions)。
- **未解决的官方信息空白**：Base 网络要求、partner 必须标记的精确社交账号、私有页中“团队与 partner stacks”的编辑入口。公开官方页面没有足够信息，本文不猜。
- 本次只做规则和页面核对，**没有编译、没有运行测试、没有保存私有提交页、没有标记 ready、没有发帖、没有执行链上交易**。

## 1. 时间线和截止时间

| 事项 | 官方时间（全部为 UTC） | 北京时间 | 核验结果 |
|---|---|---|---|
| 报名 | 2026-08-16 至 08-31 23:59 | 截止为 2026-09-01 07:59 | **已核验，已过期**。页面仍显示报名表单不等于官方允许补报；官方明说只有已注册队伍能提交。[报名页](https://hack.sibyllabs.org/register) [提交页](https://hack.sibyllabs.org/submissions) |
| 开发与提交 | 2026-09-01 至 09-10 23:59 | 截止为 2026-09-11 07:59 | **已核验，当前正处于开发期**。须在私有 build page 标记 ready。[规则页](https://hack.sibyllabs.org/rules) [提交页](https://hack.sibyllabs.org/submissions) |
| Partner workshops | 2026-09-05 至 09-07 | 精确北京时间不详 | **已核验日期**，但公开规则页没有每场的精确时刻和入口。[规则页](https://hack.sibyllabs.org/rules) |
| 评审 | 2026-09-11 至 09-12 | 精确北京时间不详 | **已核验日期**；官方没有公布小时级起止时间。[规则页](https://hack.sibyllabs.org/rules) |
| 公布前五 | 2026-09-13 至 09-15 | 精确北京时间不详 | **已核验日期**；官方没有公布精确宣布时刻。[规则页](https://hack.sibyllabs.org/rules) [排行榜](https://hack.sibyllabs.org/leaderboard) |

截至访问时，官方 Leaderboard 显示 **364 支队伍**、**还没有分数**，并明说分数在 09-12 评审结束后显示。这是 2026-09-05 的动态快照，不是固定参赛队伍数。[官方 Leaderboard](https://hack.sibyllabs.org/leaderboard)

## 2. 资格门：Memory 必须真正“承重”

这一部分是先决条件，不是 40 分普通评分项。如果资格门失败，后面的 100 分、PMF 和 partner 倍率都不会生效。[官方规则](https://hack.sibyllabs.org/rules)

| 官方要求 | 已核验内容 | 对作品的直接影响 |
|---|---|---|
| Fresh session recall | 演示视频必须在一段**连续、未剪辑**的画面里，让全新 session 读回之前写入的状态，并在屏幕上显示时间戳或 commit hash。[官方规则](https://hack.sibyllabs.org/rules) | 只刷新网页、只换一个前端 session ID、只展示事先准备的 JSON，都不足以自动证明真的 fresh session。 |
| 改变核心结果 | 读回的持久化上下文必须改变 Agent 的决策、动作或结果。[官方首页](https://hack.sibyllabs.org/) | 只是多了一段说明文字，但实际工具路径没变，有被当成装饰性记忆的风险。 |
| README 代码指针 | README 要指向真正的 memory 写入和读取位置，评委应在两分钟内找到。[官方规则](https://hack.sibyllabs.org/rules) | 仅在依赖文件中出现 Sibyl 包名不算。 |
| Deletion test | 删掉 Sibyl Memory 层或移除 memory calls 后，核心功能必须失败或有实质降级；如果仍做到同样的事，则不符合资格。[官方首页](https://hack.sibyllabs.org/) [官方规则](https://hack.sibyllabs.org/rules) | 删掉 Sibyl 后不得悄悄从 JSON、浏览器存储、进程状态或其他数据库读回同样事实。 |
| 依赖而非数量 | 一条整个项目依赖的 entity 就可以通过；一万条从不读取的数据不行。[官方规则](https://hack.sibyllabs.org/rules) | 不用为了数据量堆细节，应把评委注意力放在“哪条记忆导致了什么变化”。 |

资格门由评审小组多数决定，**平票算不通过**。[官方规则](https://hack.sibyllabs.org/rules)

## 3. 评分方式

### 主体 100 分

| 维度 | 分数 | 官方关注点 |
|---|---:|---|
| Memory is load-bearing | 40 | Memory 是否位于产品核心、使用是否深。Recall 有竞争力，coordination 和 dynamic-storage 模式位于高分档。[官方规则](https://hack.sibyllabs.org/rules) |
| Innovation & originality | 25 | 新颖、原创，而且真的有用；“聪明但没用”会被限制在低分。[官方规则](https://hack.sibyllabs.org/rules) |
| Technical execution | 20 | 干净、稳健、没有造假，能经受第二次运行和好奇评委的检查。[官方规则](https://hack.sibyllabs.org/rules) |
| Pitch & presentation | 15 | 2–5 分钟内讲清一个紧凑故事，让 load-bearing 时刻一眼可见。[官方规则](https://hack.sibyllabs.org/rules) |

### 评分公式

- 主体分最高 100。
- PMF 奖励最高 +10，因此乘倍率前最高 110。
- 0 个核验 partner：`x1.00`。
- 1 个核验 partner：`x1.15`。
- 2 个核验 partner：`x1.25` 封顶，不是 `1.15 × 1.10`。
- 理论最高 Builder Score 是 `110 × 1.25 = 137.5`。
- Rubric 和 PMF 分数是将该项目放行过资格门的评委分数取平均值。[官方规则](https://hack.sibyllabs.org/rules)

## 4. PMF 最多 +10 分的精确条件

PMF 是 product-market fit，意思是“这个东西是不是真正解决了一类人的真问题”。官方没有要求原型必须拿到 PMF 分，默认 0 分也完全可以。[官方规则](https://hack.sibyllabs.org/rules)

| 条件 | 官方明确 | 判断 |
|---|---|---|
| 真实受众 | 要有明确的 named audience（具体受众）和已验证的痛点。[官方规则](https://hack.sibyllabs.org/rules) | 只写“AI Agent 市场很大”不够。 |
| 可接受的证据类型 | waitlist（等待名单）、design partners（共创客户）、real usage（真实使用）或 pilots（试点）。[官方规则](https://hack.sibyllabs.org/rules) | 列表是官方示例，不要把没有用户身份和时间证据的截图当成自动通过。 |
| 公开可验证 | 任何非 0 分都需要一个评委能在 **5 分钟内检查**的公开证据。[官方规则](https://hack.sibyllabs.org/rules) | 私聊中的口头评价、无法访问的后台数据和开发者自述都有高风险。 |
| 明确不计分 | 市场规模幻灯片，或“用户会喜欢”的声明。[官方规则](https://hack.sibyllabs.org/rules) | 就是 0 分，不能用营销语言代替证据。 |
| 造假后果 | 伪造 PMF 证据直接取消资格，即使发奖后发现也追溯处理。[官方规则](https://hack.sibyllabs.org/rules) | 不得把 SafeHire 等旧项目的用户或成果重新标成 MemoryGuard 的 PMF。 |

## 5. Base partner 倍率条件

### 官方已明确

1. **Deployment（部署）只是资格底线**。
2. 要获得 partner 倍率，需要有一个**已执行的链上动作**，并在演示里看得到它实际工作。
3. 官方列出的例子是：wallet operation、x402 payment、B20 read 或 contract interaction。
4. 该动作必须服务于产品真实功能，只有装饰性集成或未运行包不算。[官方规则](https://hack.sibyllabs.org/rules)

### 公开规则没有写清

- 没有出现 `Base Sepolia`、`mainnet` 或 `testnet` 字样。[官方规则](https://hack.sibyllabs.org/rules)
- 没写需要多少笔交易、多少价值或多少个确认。
- 没定义“B20 read”的更详细技术范围。
- 没明说单独的合约 deployment transaction（部署交易）是否同时能当作可计分 action；但由于规则特意区分“deployment 是底线”和“executed action 才获奖励”，保守解读应是**另外演示一次真实合约交互，不把单独部署当成已拿到倍率**。这是对官方文字的保守推断，不是主办方的额外明文。

### 对 MemoryGuard 的最低证据标准（项目约束，非官方新规则）

本项目不应在仅有合约源码、按钮或配置项时申报 Base。要符合官方“在 demo 中真正执行”的要求，至少应有：合约地址、钱包用户确认、成功交易哈希、链上 receipt/event（回执/事件）和 demo 中的实际调用画面。上述是为了让评委能核验的工程证据建议，不是官方页面逐字列出的新条款。

## 6. Virtuals partner 倍率条件

### 官方已明确

以下任何一类 Virtuals-native（Virtuals 原生）集成，必须在 demo 中真正运行：

- ACP job（Agent Commerce Protocol 任务）；
- registered or transacting agent（已注册或发生交易的 Agent）；
- 其他 Virtuals-native integration。[官方规则](https://hack.sibyllabs.org/rules)

规则同时要求 partner stack 必须在提交作品中“doing real work”，并服务于产品实际功能；只导入 SDK（开发包）或演示 Logo 不算。[官方首页](https://hack.sibyllabs.org/) [官方规则](https://hack.sibyllabs.org/rules)

### 公开规则没有写清

- 没规定 ACP job 必须到哪个细分状态才算完成。
- 没写 Virtuals 的网络、最低交易金额、最少任务数量或 Agent 注册的额外验证要求。
- 没写“已注册 Agent”如何在 demo 里证明为当前作品实际功能服务。

因此，如果要申报 Virtuals，不能只根据一个注册页面或一段未运行的代码就断言已经拿到倍率。

## 7. 官方提交材料和字段

### 公开规则层面

| 提交项 | 官方要求 |
|---|---|
| 公开 GitHub 仓库 | 必须是 public，使用 OSI 认可开源许可证（官方举例 MIT 或 Apache-2.0），有真实 commit 历史。[官方规则](https://hack.sibyllabs.org/rules) |
| 2–5 分钟 demo | 展示问题和谁遇到它、产品、如何工作、如何用 Sibyl Memory，并包含 fresh-session recall 时刻。[官方规则](https://hack.sibyllabs.org/rules) [官方提交说明](https://hack.sibyllabs.org/submissions) |
| README | 说明作品做什么、memory 在哪里 load-bearing、partner stack 用在哪里、一段“how memory made this possible”、Prior Work 声明，并有完整安装和运行说明。[官方规则](https://hack.sibyllabs.org/rules) [官方提交说明](https://hack.sibyllabs.org/submissions) |
| 团队和 partner stacks | 公开提交页要求列出构建者，以及实际使用的 Base 或 Virtuals stack。[官方提交说明](https://hack.sibyllabs.org/submissions) |
| Memory implementation note | 说明 Agent 持久化了什么、fresh session 如何读回，以及用它改变了什么决策。[官方提交说明](https://hack.sibyllabs.org/submissions) |
| 两条公开帖子 | 一条为 demo video，至少一条为 build log；标记 `@sibylcap` 和每个声称使用的 partner。[官方规则](https://hack.sibyllabs.org/rules) |
| 最终提交动作 | 不是另外填公开表单；在报名后收到的私有 build page 补齐 repo、demo 和 posts，然后在 09-10 23:59 UTC 前标记 ready。[官方提交说明](https://hack.sibyllabs.org/submissions) |

### 2026-09-05 当日在私有 build page 看到的精确字段

> 证据边界：以下内容来自已报名队伍当日打开的 Sibyl 官方私有 build page。本文不收录该私有编辑链接，公开流程见[官方提交说明](https://hack.sibyllabs.org/submissions)。

| 页面字段 | 当日可见说明 |
|---|---|
| `Public repo URL` | 填入后 repo milestone 自动完成。 |
| `Demo video URL` | 视频链接字段。 |
| `Post URLs (one per line, 2+)` | 支持 X 或 Farcaster；一行一个，两条或以上才标记 posts milestone。 |
| `What breaks when memory is deleted?` | 要求一至两句。页面说它与下方至少一个 primitive 一起使 memory milestone 完成，也是评估 memory PMF 的核心。 |
| `Memory walkthrough (judges score the 40% from this)` | 要求正好说清三件事：持久化什么、fresh session 如何读回、改变什么决策或动作。页面文案说评委不看视频也应能据此判断 memory 是否 load-bearing。 |
| `Memory primitives you used` | 可选项为 `recall`、`entities`、`semantic search`、`temporal / time-travel`、`summarization`、`reflection`、`consolidation`。只能选择真正实现并能演示的项。 |
| `Save my build` | 保存按钮；本次只读核验，未点击。 |
| `Mark ready for judging` | 最终评审开关。页面说 repo 和 demo video 已有时再标记 ready，截止前可以取消标记。本次未勾选。 |

页面顶部的四个里程碑是 `Public repo`、`Demo video`、`2 posts`、`Memory fields`。**2026-09-05 当日只读观察时，这四个里程碑仍全部未完成；文本字段为空，memory primitives 和 `Mark ready for judging` 均未勾选。**本次没有保存或改动页面。

### 发现的官方页面不一致

公开 Submissions 页要求完整提交包含 **Team & partner stacks**，但本次看到的私有 build page 上没有独立的“构建者名单”或“Base/Virtuals partner stack”编辑字段。[官方提交说明](https://hack.sibyllabs.org/submissions)

可能性包括它沿用了报名数据、仅在 README 和 demo 声明，或页面尚未提供该字段。**这些都只是可能性，不是已核验事实**。提交前应向主办方确认如何更新构建者和 partner stack，不应自行假设系统会从 README 自动读取。

## 8. 参赛与授权其他条款

- 参赛者需满 18 岁，且不在受制裁司法辖区；Sibyl Labs 员工和 reference builds 可展示但不能获奖。[官方首页 FAQ](https://hack.sibyllabs.org/) [官方规则](https://hack.sibyllabs.org/rules)
- 队伍规模是 1–5 人；一个邮箱只报名一次，由一人代表队伍报名。[官方首页 FAQ](https://hack.sibyllabs.org/) [官方报名页](https://hack.sibyllabs.org/register)
- 作品 IP（知识产权）仍归参赛者；提交后向 Sibyl Labs 和已命名 partners 授予非独家、免版税展示许可，可将视频、仓库、截图和描述用于赛事报道，需保留署名。[官方规则](https://hack.sibyllabs.org/rules)
- 奖金以 Base 上的 USDC 支付；获奖者需提供发奖信息，前五团队还需参加一次简短 case-study 访谈。[官方规则](https://hack.sibyllabs.org/rules)

## 9. 对 ProofOps MemoryGuard 的直接判断

以官方规则来看，优先级应该是：

1. **先保资格**：在连续未剪辑视频中展示 Session A 写入、真的 fresh Session B 读回、同一高风险意图改变决策/工具动作，再展示删掉 Sibyl 后核心功能失败或实质降级。
2. **补齐正式提交材料**：公开仓库、2–5 分钟 demo、两条公开帖、memory deletion 说明、三行 walkthrough、真实 primitives，并在截止前标记 ready。
3. **Base 只在条件满足后申报**：公开规则对 Sepolia/主网不清楚，先向官方确认；有真实部署、另外执行的产品相关链上动作和 demo 内证据再声称倍率。
4. **Virtuals 不应为凑 `x1.25` 分散主线**：除非能在 demo 中真正运行 ACP job、注册/交易 Agent 或其他 Virtuals-native 功能。
5. **PMF 不能用旧项目材料替代**：要拿非 0 分，必须有评委 5 分钟内能打开的 MemoryGuard 特定公开证据。

一句话归纳：**官方评审先看“记忆是否真正改变行为”，再看完成度、创新和演示，最后才是 partner 和 PMF 加分。链接多不会自动变成高分，但缺 repo、demo、posts 或最终 ready 会直接影响是否能进入完整评审。**

## 官方来源索引

- [Sibyl Labs Hackathon 官方首页](https://hack.sibyllabs.org/)（当日核验：2026-09-05）
- [Rules · Sibyl Labs Hackathon](https://hack.sibyllabs.org/rules)（当日核验：2026-09-05）
- [Submissions · Sibyl Labs Hackathon](https://hack.sibyllabs.org/submissions)（当日核验：2026-09-05）
- [Register · Sibyl Labs Hackathon](https://hack.sibyllabs.org/register)（当日核验：2026-09-05）
- [Leaderboard · Sibyl Labs Hackathon](https://hack.sibyllabs.org/leaderboard)（当日核验：2026-09-05）
- 已注册队伍的 Sibyl 官方私有 build page（当日只读核验：2026-09-05；因链接可以直接编辑提交，不在仓库中记录 URL）
