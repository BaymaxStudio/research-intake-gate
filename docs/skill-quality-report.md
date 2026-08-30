# Research Intake Gate 打磨报告

> 评估日期：2026-08-30。当前分数计入本地实测与私有 GitHub 仓库 CI；公网安装和模型对照尚未计分。

## 1. 验料结果

挑战 1 - 真实问题：成立。多来源研究进入长期维护的数据集之前，需要把来源访问状态、适用周期、逐条证据和人工决定分开记录。

挑战 2 - 独特角度：来自工作流与确定性脚本。重点不是再写一份研究报告，而是建立 `staging → validate → human review → approved` 的写入门槛。

挑战 3 - 安装理由：临时提示词难以稳定复用退出码、重复写入保护、隐私检查、审核文件和批次差异。可执行脚本让这些规则不依赖 Agent 当时的措辞。

挑战 4 - 公共传播性：一句话定位是“让 AI 的研究结果先过证据与人工审核，再进入正式数据。”可展示产物包括离线审核页、正式 JSON、差异报告和真实 CLI 回放 GIF。

验料结论：真实需求、可复用资产和可展示产物均成立，适合做独立公共 Skill。

## 2. 访行记录

| 同行 | 类型 | 一句话定位 | 可学的手艺 | 本项目不照搬的部分 |
|---|---|---|---|---|
| [Industry Research Skill](https://github.com/lu90/industry-research-skill) | 直接 | 用 claim 与证据台账约束行业研究报告 | claim routing、证据清单、失败记录 | 以报告交付为中心，缺少正式数据写入门槛 |
| [Research Pipeline](https://tessl.io/registry/sayed/research-pipeline/files/SKILL.md) | 直接 | 分阶段研究、检查点与引用校验 | 阶段化流程、citation validator | 多 Agent 报告流程较重 |
| [Reddit Pain Research](https://github.com/haseebeqx/reddit-pain-research-skill) | 直接 | 脚本化研究与人工审批 | 稳定产物、恢复执行、标准库测试 | 数据源与场景过于专门 |
| [Research skill](https://www.skills.sh/warpdotdev/common-skills/research) | 间接 | 通用研究工作流 | 首屏价值和安装入口 | 不提供本项目的数据写入门槛 |
| [Research Swarm](https://clawhub.ai/openclawprison/skills/research-swarm) | 间接 | 多 Agent 并行研究 | 外部输入与数据外传规则 | 服务器和外部 POST 不符合本地优先边界 |
| [LangExtract](https://github.com/google/langextract) | 间接 | 带原文跨度的结构化抽取 | 来源定位与交互式 HTML | 侧重抽取，不负责人工批准后的正式版本 |
| [FActScore](https://github.com/shmsw25/FActScore) | 间接 | 把长文本拆成原子事实并评分 | 原子 claim 思路 | 自动评分不能替代人工决定 |
| [Open Deep Research](https://github.com/langchain-ai/open_deep_research) | 间接 | 自动生成深度研究报告 | 研究编排与来源整合 | 运行栈和目标范围明显更大 |
| [Anthropic Skills](https://github.com/anthropics/skills) | 手艺 | 官方 Skill 示例集合 | 渐进加载、目录结构、行为评估 | 各目录许可不同，不复制具体实现 |
| [OpenAI Plugins](https://github.com/openai/plugins) | 手艺 | Codex 插件与确定性 CLI 示例 | Skill 与脚本边界、manifest 验证 | 不引入本项目不需要的 MCP 或 App |

## 3. 生态位判断

纵向结论：它来自招聘决策台和博士招生监测中反复出现的同一问题——研究可以由 Agent 批量完成，但进入正式数据前必须给人留下核验、驳回和追踪窗口。下一阶段先证明安装与工作流稳定，再考虑自动监测。

横向结论：相邻工具大多停在“生成报告”“记录引用”或“自动评分”。人工决定之后生成追加式正式数据，是更窄但更清楚的位置。

交叉洞察：本项目不争夺通用深度研究入口，而是做研究结果进入长期数据集前的最后一道本地门槛。

一句话定位：让 AI 的研究结果先过证据与人工审核，再进入正式数据。

## 4. 过尺结果

### 活体检查

- Python 3.12 与 3.14：22 项测试全部通过。
- 正向工作流：`init`、`validate`、`review`、人工决定、`promote`、`diff` 已用合成数据完整运行。
- 反例：旧周期、搜索摘要、blocked 页面、无引用、错误引用、重复 ID、冲突、敏感字段和未完成审核均触发预期门槛。
- 确定性：同输入生成的 JSON、Markdown 与 HTML 逐字节一致；重复正式写入返回退出码 2。
- 结构：Agent Skills 官方 `skills-ref`、Codex Skill 校验器、Codex plugin validator、`claude plugin validate --strict` 全部通过。
- 页面：1280×800 与 390×844 均无横向溢出；筛选正常；无外部脚本或样式；无控制台错误。
- 键盘：卡片有 `tabindex="0"` 和可见焦点样式；当前浏览器自动化没有成功模拟 Tab 焦点移动，保留一次人工复核。
- 隐私：凭据与私人路径扫描通过；示例只使用虚构机构和 `example.invalid`。
- GIF：由 `scripts/make_demo.py` 运行真实 CLI 后生成，终端文字无私人路径。
- 独立 Agent：首轮发现来源字段误用和审核材料内容缺口；修复后复验通过。联系页支持招聘状态时 `validate=1`、`review=1`、`promote=1`，没有正式文件生成。
- GitHub Actions：首轮在 macOS 发现临时目录路径差异；修复后 [第 33317384273 次运行](https://github.com/BaymaxStudio/research-intake-gate/actions/runs/33317384273) 的 Python 3.10/3.14、结构检查、隐私扫描和演示复现全部通过。

### 九维评分

| 维度 | 权重 | 得分 | 证据 | 当前损耗 |
|---|---:|---:|---|---|
| Frontmatter 与触发条件 | 7 | 7 | 正负触发边界明确，两个校验器通过 | 无 |
| 工作流清晰度 | 12 | 12 | 五个命令与人工暂停点均有文档和实跑 | 无 |
| 失败模式编码 | 12 | 12 | 旧周期、摘要、blocked、冲突、隐私与覆盖保护均有测试 | 无 |
| 检查点设计 | 6 | 6 | review 模板默认 `needs_followup`，promote 再校验 | 无 |
| 可执行具体性 | 17 | 15 | 标准库 CLI、明确退出码、22 项测试 | 仍需手工编辑决定 JSON |
| 资源整合度 | 4 | 4 | 规则、契约、案例、产物和录制脚本均被入口引用 | 无 |
| 整体架构 | 12 | 11 | 核心可随 Skill 安装，仓库入口为薄包装 | 单文件 CLI 较长 |
| 实测表现 | 23 | 21 | 双 Python 版本、本地浏览器、四类结构校验、私有仓库 CI | 公网安装、Claude 模型对照未完成 |
| 反例与黑名单 | 7 | 7 | SKILL、README、安全文档和测试均覆盖 | 无 |
| **总分** | **100** | **95** | **本地与私有 CI 实测** | **公网项目尚未计分** |

## 5. 差距清单

### P0：公开前必须完成

- 公开前再次检查 README 渲染、相对链接、GIF 和仓库可见内容。
- 公开后从 GitHub 实测 `npx skills add` 与 Claude Code marketplace 安装。

### P1：完成后提高可信度

- 用真实键盘手动复核审核页的 Tab 顺序。
- 在取得模型额度授权后，运行 Claude plugin eval 的有 Skill/无 Skill 对照。
- 给 CLI 增加可选的包级命令入口，减少长路径输入。

### P2：后续版本再做

- 发布 JSON Schema，供编辑器和其他语言直接复用。
- 在不破坏本地边界的前提下增加独立监测适配层。
- 从真实公开反馈中补充新的失败案例。

### 与同行相比，当前最缺的三件事

1. 公网安装回放。
2. 模型级行为对照，而不只是脚本与文档测试。
3. 第三方用户反馈。

### 当前最清楚的三项差异

1. `claim → source → excerpt/status → human decision` 的完整审计链。
2. 被驳回的错误结论可以保留审核记录，但不会进入正式数据。
3. 本地、零 Key、追加式写入，并明确拒绝强制覆盖。

## 6. 三个打磨方向

### 方向 A：保持单 Skill，完成 v0.1.0 发布

范围：只完成公网 CI、两种安装实测、README 渲染和 release。优点是边界稳定；风险是人工编辑 JSON 的使用门槛仍在。

### 方向 B：增加本地审核交互层

范围：保留现有数据契约，增加本地表单或终端交互，用于写 review decision。优点是减少手工编辑错误；风险是需要维护新的交互代码和安全检查。

### 方向 C：拆成研究质量套件

范围：在 intake gate 之外增加监测、抓取适配与领域规则包。优点是覆盖更完整；风险是定位变宽、依赖与维护成本上升。

本轮采用方向 A。v0.1.0 先证明最窄工作流可安装、可审查、可重复，再根据使用反馈判断是否进入方向 B。

## 7. 已落地的候选改写

本轮改动边界：只创建独立仓库，不复用或修改两个来源项目的代码与真实数据。

| 文件 | 作用 | 验证 |
|---|---|---|
| `skills/research-intake-gate/SKILL.md` | 触发、流程、暂停点与安全边界 | 两个 Skill 校验器通过 |
| `scripts/research_gate.py` | 仓库 CLI 入口 | 22 项测试与端到端回放 |
| `skills/.../scripts/research_gate.py` | 可随 Skill 安装的确定性核心 | Python 3.12/3.14 |
| `examples/` | 两类失败语义与审核产物 | 实际生成 HTML/JSON/Markdown |
| `scripts/make_demo.py` | 固化展示回放 | 生成 GIF、正式数据和 diff |
| `scripts/check_private_data.py` | 固化发布前隐私检查 | 当前扫描通过 |
| `supportsFields` 数据契约 | 阻止联系页等来源跨字段证明结论 | 独立 Agent 首轮发现，修复后复验通过 |

验证手段已沉淀为测试、结构检查、隐私扫描、行为 prompts 和可复现演示，不依赖本报告的文字判断。

## 8. README 与 Showcase

- 首屏使用已选定的一句话定位，不添加新的营销口号。
- GIF 放在安装之前，展示真实命令与退出码。
- 三个可点击产物分别展示审核、正式数据和版本差异。
- 安装覆盖 Agent Skills、Claude Code marketplace 与手动复制。
- 中文主版与英文版互链；安全边界和负触发单列。

## 9. 执行计划

### 发布前

- [x] 完成 CLI、Skill、两种插件 manifest 和合成案例。
- [x] 完成本地测试、结构校验、隐私扫描和页面检查。
- [x] 完成两轮独立 Agent 验收并处理首轮发现的问题。
- [x] 创建私有 GitHub 仓库。
- [x] 按功能拆分提交并推送，私有仓库线上 CI 通过。

### 公开前

- [ ] 展示线上 CI、README、HTML、GIF 和隐私扫描结果。
- [ ] 取得明确授权后把仓库改为公开。

### 公开后

- [ ] 从 GitHub 实测两种安装路径。
- [ ] 取得明确授权后创建 `v0.1.0` 标签与 GitHub Release。

### 本轮不做

- 通用爬虫、定时任务、自动事实裁决、多人数据库、ClawHub 与 Tessl 提交。

## 10. 出师证书

```text
┌──────────────────────────────────────────┐
│  出师证书 · 鲁班工坊                     │
│                                          │
│  作品：Research Intake Gate              │
│  过尺：开工前未成型 → 当前 95 分          │
│  标记：本地与私有 CI；公网安装尚未计分     │
│  定位：AI 研究进入正式数据前的人工审核门   │
│  核心：证据状态、人工决定、追加式正式版本   │
│  下一步：公开授权与公网安装验收            │
│                                          │
│  验收：鲁班方法 + 独立 Agent 复验通过      │
└──────────────────────────────────────────┘
```

## 11. 回炉清单

- 观察 [Reddit Pain Research](https://github.com/haseebeqx/reddit-pain-research-skill) 的人工审批与恢复执行做法。
- 观察 [LangExtract](https://github.com/google/langextract) 的来源定位与 HTML 审核交互。
- 观察 [Agent Skills 规范](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx) 与 [OpenAI Plugins](https://github.com/openai/plugins) 的结构变化。
- 每次修改验证规则必须新增失败样例与通过样例。
- 每次 release 说明为什么改变审核语义，并重跑公开安装。
- 下一轮入口优先读取真实 issue 与安装失败记录，不为未发生的场景扩展功能。

## 12. 待确认动作

- 仓库公开属于单独发布动作，必须在私有仓库 CI 通过后取得明确授权。
- `v0.1.0` 标签与 GitHub Release 属于另一个发布动作，需再次授权。
- Claude plugin eval 会消耗模型额度，执行前单独说明预计调用量。

## 13. 参考来源

- [Agent Skills specification](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx)
- [Claude Code plugins](https://code.claude.com/docs/en/plugins)
- [Claude Code plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- [Industry Research Skill](https://github.com/lu90/industry-research-skill)
- [Research Pipeline](https://tessl.io/registry/sayed/research-pipeline/files/SKILL.md)
- [Reddit Pain Research](https://github.com/haseebeqx/reddit-pain-research-skill)
- [Research skill](https://www.skills.sh/warpdotdev/common-skills/research)
- [Research Swarm](https://clawhub.ai/openclawprison/skills/research-swarm)
- [LangExtract](https://github.com/google/langextract)
- [FActScore](https://github.com/shmsw25/FActScore)
- [Open Deep Research](https://github.com/langchain-ai/open_deep_research)
- [Anthropic Skills](https://github.com/anthropics/skills)
- [OpenAI Plugins](https://github.com/openai/plugins)
