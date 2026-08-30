<sub>🌐 <b>中文</b> · <a href="README.en.md">English</a></sub>

<div align="center">

# Research Intake Gate

> 让 AI 的研究结果先过证据与人工审核，再进入正式数据。

[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-5b4ee5)](skills/research-intake-gate/SKILL.md)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-c96f42)](.claude-plugin/plugin.json)
[![Codex](https://img.shields.io/badge/Codex-plugin-111111)](.codex-plugin/plugin.json)
[![skills.sh](https://skills.sh/b/BaymaxStudio/research-intake-gate)](https://skills.sh/BaymaxStudio/research-intake-gate)
[![CI](https://github.com/BaymaxStudio/research-intake-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/BaymaxStudio/research-intake-gate/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**把多来源研究拆成“暂存 → 校验 → 人工决定 → 正式数据”，并保留可追溯的证据链。**

[看产物](#实际产物) · [安装](#安装) · [使用](#使用流程) · [差异](#它和相邻工具有什么不同) · [安全边界](#安全边界)

</div>

![真实 CLI 工作流演示](docs/demo.gif)

<sub>演示由仓库中的合成资料和真实 CLI 输出生成；可用 `python3 scripts/make_demo.py` 复现。</sub>

---

## 它解决什么问题

Agent 很适合收集资料，但“它给出了答案”不等于“这条数据可以进正式表”。往届公告可能被当成当前公告，搜索摘要可能被当成正文，打不开的页面也可能被误写成“没有相关信息”。一旦这些内容直接进入监测表或决策台，错误会在后续批次里继续累积。

Research Intake Gate 把 AI 研究放在暂存区。确定性脚本检查来源状态、适用周期、引用关系、冲突和隐私风险；HTML 与 Markdown 让人逐条审阅；只有人工明确接受或驳回全部结论后，工具才会写入新的正式版本。

它不负责通用网页抓取，也不判断事实真伪。网页访问由 Codex、Claude Code 或其他宿主 Agent 完成，这个仓库只负责研究进入正式数据之前的审核流程。

## 实际产物

| 产物 | 用途 | 样例 |
|---|---|---|
| 离线审核页 | 查看结论、来源、摘录、冲突与风险 | [sample-review.html](docs/sample-review.html) |
| 正式数据 | 只保留人工接受的结论和对应来源 | [sample-approved.json](docs/sample-approved.json) |
| 批次差异 | 展示新增、删除、修改与状态变化 | [sample-diff.json](docs/sample-diff.json) |

两个行为案例也在仓库中：

- [教师招聘合成案例](examples/recruitment/)包含往届公告、搜索摘要和联系方式风险；
- [博士招生合成案例](examples/admissions/)保留 blocked、low-yield 和互相冲突的来源。

这些案例均使用虚构机构和 `example.invalid` 地址，不含真实申请、招聘或个人数据。

## 安装

### Agent Skills 兼容环境

```bash
npx skills add BaymaxStudio/research-intake-gate --skill research-intake-gate
```

### Claude Code 插件

在 Claude Code 中运行：

```text
/plugin marketplace add BaymaxStudio/research-intake-gate
/plugin install research-intake-gate@research-intake-gate
```

### 手动复制

把 `skills/research-intake-gate/` 复制到当前 Agent 的 skills 目录。核心 CLI 使用 Python 3.10+ 标准库，不需要 API Key，也不需要启动服务器。

安装后可以直接说：

```text
用 research-intake-gate 审核这批多来源研究，先生成审核材料，等我决定后再写入正式数据。
```

## 使用流程

### 1. 创建项目

```bash
python3 scripts/research_gate.py init ./my-research --example admissions
```

项目结构固定为：

```text
my-research/
├── project.json       # 研究范围、当前周期、目标和允许字段
├── staging/           # Agent 收集的待审核批次
├── reviews/           # JSON、Markdown、HTML 与人工决定
├── approved/          # 按批次追加的正式数据
└── reports/           # 批次差异报告
```

目标目录非空时，`init` 会拒绝写入。

### 2. 校验证据

```bash
python3 scripts/research_gate.py validate ./my-research --batch admissions-2027-01
```

标成 `current` 的结论必须由已访问正文、不是搜索摘要、适用周期为项目当前周期或 `evergreen`，且声明可证明该字段的来源支持。联系页可以证明联系方式，但不能单独证明招聘状态。

### 3. 生成审核材料

```bash
python3 scripts/research_gate.py review ./my-research --batch admissions-2027-01
```

命令会生成内容一致的 JSON、Markdown、离线单文件 HTML，以及一份全部为 `needs_followup` 的决定模板。HTML 只读，不在页面中修改决定。

### 4. 人工决定后写入正式数据

人工编辑 `reviews/admissions-2027-01-decisions.json`，把每条决定改成 `accept` 或 `reject` 并填写理由，然后运行：

```bash
python3 scripts/research_gate.py promote ./my-research --batch admissions-2027-01
```

只要还有待处理项，或被接受的结论存在阻断错误，写入就会停止。已有正式文件不会被覆盖。

### 5. 比较批次

```bash
python3 scripts/research_gate.py diff ./my-research \
  --from admissions-2027-01 \
  --to admissions-2027-02
```

## 触发方式

- “这批研究先别进正式表，检查证据后给我审核。”
- “把多所学校的资料做成可逐条接受或驳回的审核包。”
- “检查往届公告有没有冒充当前信息。”
- “搜索摘要只能做线索，不能当正式证据。”
- “保留打不开和低产出的来源，不要推断成不存在。”
- “比较这两批正式研究数据有哪些变化。”

普通一次性事实问答不会启动完整建项流程，除非你明确要求生成可审核的证据包。

## 它和相邻工具有什么不同

| 方向 | 常见产物 | Research Intake Gate 的边界 |
|---|---|---|
| 深度研究 Agent | 一篇带引用的报告 | 面向将进入长期维护数据集的逐条结论 |
| 证据台账 | claim 与 citation 清单 | 在台账之后增加人工决定和正式版本写入门槛 |
| 自动事实评分 | 置信度或自动分数 | 不把程序评分当成人工接受 |
| 抓取与监测 | 新网页、变更提醒 | v0.1 不联网，只处理宿主 Agent 已收集的材料 |

方法与展示参考见[质量报告](docs/skill-quality-report.md)，其中列出同行链接、差距、实测证据和后续观察项。

## 安全边界

- 默认本地运行，不联网、不需要 API Key、不启动服务；
- 网页和导入文件均视为不可信输入；
- 凭据、高风险身份与金融字段会阻断校验；
- 邮箱、电话和超过 280 字符的摘录会产生警告；
- 不删除源文件，不生成自动接受决定，不提供强制覆盖参数；
- 正式数据按批次新增文件，历史版本保留。

详细规则见 [evidence-rules.md](skills/research-intake-gate/references/evidence-rules.md) 与 [data-contract.md](skills/research-intake-gate/references/data-contract.md)。

## 验证与测试

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_structure.py
python3 scripts/check_private_data.py
```

测试覆盖有效批次、届次错配、搜索摘要、受阻页面、来源字段误用、无来源结论、错误引用、重复 ID、冲突证据、隐私字段、未完成审核、驳回排除、重复写入、确定性输出和批次差异。CI 同时在 Python 3.10 与 3.14 上运行，并重建演示产物检查差异。

## 文件结构

```text
skills/research-intake-gate/   # 可安装的开放 Agent Skill
scripts/research_gate.py       # 仓库 CLI 入口
scripts/make_demo.py           # 可复现演示与样例生成器
examples/                      # 两个脱敏合成案例及真实审核产物
tests/                         # 单元、端到端与行为触发样例
docs/                          # GIF、样例产物与质量报告
```

## 致谢

本项目遵循 [Agent Skills 规范](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx)。同行研究参考了 [Industry Research Skill](https://github.com/lu90/industry-research-skill)、[Reddit Pain Research](https://github.com/haseebeqx/reddit-pain-research-skill)、[LangExtract](https://github.com/google/langextract)、[FActScore](https://github.com/shmsw25/FActScore) 和 [OpenAI Plugins](https://github.com/openai/plugins)。这里借鉴的是可审计证据、人工检查点和公共 Skill 包装方法，代码与合成案例均为独立实现。

## License

[MIT](LICENSE)
