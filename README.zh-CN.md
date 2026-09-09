# Skill Field Lab

[English](README.md)

> **Study before you install. Test only what matters.**
>
> 先研究，再安装；只测试真正重要的东西。

Skill Field Lab 是一套 local maintainer workbench：用来研究外部 agent Skills、
演化自己的 reusable behavior，并为一个明确 claim 产出有边界的 evidence，而
不是把每个有用机制都变成 dependency。

一份 user-level installation 可以研究或运行任何显式选择的 local subject。
Subject 仍由它自己的 repo 独立拥有和使用；Field Lab 不会把 runtime 复制进去、
替它安装 Skill，也不会让它反过来依赖 Field Lab。

当前 release contract：**0.2.0**。它的 source acceptance 包含一次真实、严格
capped 的 target-agent canary。本机 installation、Git tag、published assets、
后续新 task 的 controller discovery 与 owner acceptance 仍是彼此独立的可观察状态。

架构图：[简体中文](docs/ARCHITECTURE.zh-CN.md) ·
[English](docs/ARCHITECTURE.md)。

## 工作模型

```text
external source
  -> Pattern Intake
       -> ADOPT | ADAPT | REJECT | DEFER | ALREADY COVERED
       -> 不建 lab 也是完整成功结果
       -> 只有一个会改变决策的 unresolved claim
            -> Field Trial
                 -> 先看 ordinary work 是否已经足够
                 -> 仍不足时才做最小 no-spend plan
                 -> 另行授权后才跨过 capped live boundary
```

三档介入深度：

1. **Level 0 — intake only。** `$pattern-intake` pin 并研究一个外部机制；不需要
   manifest、fixture、subject write 或 model run。
2. **Level 1 — external local lab。** `fieldlab init` 在猫选择的位置建立透明的
   lab。Subject 只会被读入 disposable workspace，原 repo 保持不变。
3. **Level 2 — subject-owned evidence。** `fieldlab promote` 只把明确选择的
   records 复制到指定 evidence directory；不会复制 runtime、manifest、plans
   或 run workspaces。

`$skill-eval` 的 display name 是 **Field Trial**，并且只能 explicit invoke。
它负责为一个 unresolved claim 选择 evidence path，不负责给 Skill 打总分。

## 一次安装

需要 Python 3.10+、Git 和 Codex CLI。v0.2 的 live execution 只支持 POSIX；
Windows 在有等价 process containment 之前 fail closed。

```bash
python3 scripts/install.py
~/.local/bin/fieldlab doctor
```

Transactional installer 会安装：

- app：`~/.local/share/skill-field-lab`；
- launcher：`~/.local/bin/fieldlab`；
- 两个 controller Skills：`${CODEX_HOME:-~/.codex}/skills`；
- app 内的 installation receipt。

它拒绝覆盖陌生 target。确认升级时使用 `--replace`：旧 app、launcher 和
controllers 会先复制进 recoverable backup；`--cli-only` 则完全不碰 Skill
discovery path。自定义路径、rollback 与 uninstall 见
[安装与恢复](docs/INSTALLATION.md)。

## 建立 v2 lab

```bash
fieldlab init /path/to/my-study --lab-id my-study
fieldlab validate /path/to/my-study/fieldlab.json
fieldlab list /path/to/my-study/fieldlab.json
```

`init` 会创建一个 isolated control 和空的 records/cases 目录。在
`fieldlab.json` 中加入显式 local source：

```json
{
  "schema_version": 2,
  "lab_id": "my-study",
  "description": "Test one unresolved reusable-agent behavior claim.",
  "subjects": {
    "isolated-control": {"kind": "control"},
    "my-skill": {
      "kind": "agent-skill",
      "source": {"type": "local-path", "path": "/path/to/subject/skills/my-skill"}
    }
  },
  "cases_root": "cases",
  "defaults": {
    "adapter": "codex-exec",
    "approval_policy": "never",
    "network_access": false,
    "output_root": "runs",
    "keep_workspace": false
  }
}
```

支持 `local-path`、`local-git-ref`、lab-owned `snapshot` 和 `control`。
Field Lab 不自动 clone URL、不解析 marketplace，也不猜 installed Skills。

Case 可以检查 final agent response、workspace files、bounded commands、raw
trace properties 或明确列出的 human-review needs。`fixture/` 和 `expected/`
都是 optional；有 `expected/` oracle 时，下面的 no-spend gate 会证明 unresolved
fixture 至少失败一项，而 expected overlay 全部通过：

```bash
fieldlab selftest /path/to/my-study/fieldlab.json
```

Repo 自带两个 v2 labs：一个 file-edit oracle；一个完全不改文件、只验证 final
response 的 legal-research case：

```bash
fieldlab validate examples/demo/fieldlab.json
fieldlab selftest examples/demo/fieldlab.json
fieldlab validate examples/legal-research/fieldlab.json
fieldlab selftest examples/legal-research/fieldlab.json
```

## Existing work first

Ordinary trace、diff、test result 或 review 可以直接绑定 claim，不必先造 synthetic
case：

```bash
fieldlab observe /path/to/my-study/fieldlab.json \
  --subject my-skill \
  --claim one-bounded-claim \
  --outcome supported \
  --artifact review=/path/to/review.md \
  --note "这份 artifact 证明什么，以及证明不到哪里。"
```

Observed receipt 是 content-light 的，且不会启动 target agent。后续 human
review 另存为独立 record，并绑定 immutable receipt digest。

创建该 review 时，JSON object 的 keys 必须与 receipt 中声明的
human-review requirements 完全一致。只有 receipt 没有声明任何
requirements 时才可以省略 `--requirement-outcomes`：

```bash
fieldlab review /path/to/my-study/fieldlab.json \
  --review-id one-bounded-review \
  --receipt /path/to/my-study/runs/one-attempt/receipt.json \
  --independence separate-agent \
  --judgment supported \
  --rationale "这份 review 支持什么，以及哪些仍未验证。" \
  --requirement-outcomes /path/to/requirement-outcomes.json
```

每个 value 只能是 `supported`、`not-supported` 或 `inconclusive`。
Missing、extra、duplicate、malformed、symlinked 或超过大小限制的
outcome input 都会 fail closed。Review command 不启动 target agent，也不修改
receipt。

## Spend 之前必须先 plan

Plan 对 subject 是 read-only，也不会启动 target model：

```bash
fieldlab plan /path/to/my-study/fieldlab.json \
  --subject isolated-control \
  --subject my-skill \
  --case one-case \
  --mode matched \
  --repeat 1 \
  --model gpt-5.6-sol \
  --reasoning-effort high \
  --output /path/to/my-study/plans/one-plan.json
```

Plan 会列出每一次 invocation，并 pin manifest、prompt、case、fixture、subject
source、Field Lab source 和当前可解析的 Codex executable。任何 input drift 都
fail closed。Plan 本身不授权 execution。

Live run 必须同时具备三道 gate：

```bash
fieldlab run /path/to/my-study/plans/one-plan.json \
  --live \
  --max-invocations 2
```

没有 implicit retry、grader、repeat、baseline 或 full suite。Target 与 verifier
各自在 dedicated POSIX process group 中运行；只有 group quiescent 后才 seal
evidence。

## V1 只是一条 migration input

v0.1 没有外部用户，所以 v0.2 不背 dual runtime，也不保留旧 command aliases。
Normal commands 只接受 schema-v2 `fieldlab.json`。猫自己留下的旧 pack 可以一次性
迁移：

```bash
fieldlab migrate-v1 /path/to/fieldlab-pack.json \
  --output /path/to/new-external-lab/fieldlab.json
```

Migrator 不改 source pack；它把 cases 真正改写成 schema v2，把 legacy overlays
snapshot 进新 lab，并在 receipt 中记录任何 semantic change。

## Evidence ceiling

Receipt 把这些维度分开：

- origin：`observed | synthetic`；
- subject scope：`isolated-control | workspace-scoped | hermetic`；
- comparison：`unmatched | single | matched`；
- verification methods：`deterministic | human | llm`；
- independence：`implementer-run | separate-agent | external-reviewer`。

`hermetic` 仍然 reserved。`workspace-scoped` 不等于“只有选中的 Skill 导致结果”。
Requested model / effort 只是 caller-selection evidence，除非 provider 暴露更强
runtime identity。

## Repo authority map

| Path | Authority |
| --- | --- |
| `docs/PRODUCT_SPEC_V0.2.md` | 已接受的 product / acceptance contract |
| `docs/WORKSPACE_MODEL_V0.2.md` | source identity、materialization、drift、write boundary |
| `docs/SCHEMA_DELTA_V1_TO_V2.md` | v2 object authority 与一次性 migration mapping |
| `docs/ARCHITECTURE.zh-CN.md` / `docs/ARCHITECTURE.md` | 中英两版 Mermaid：controller、workspace、execution、evidence、installation 与 subject ownership boundaries |
| `docs/EVIDENCE_MODEL.md` | claim ceiling 与 receipt/review interpretation |
| `docs/INSTALLATION.md` | install、upgrade、rollback、uninstall、doctor |
| `schemas/v2/` | active JSON Schemas |
| `schemas/v1/` | 只用于理解 migration input 的历史 schemas |
| `examples/` | self-contained v2 labs |
| `case-studies/` | integration notes 与 screened receipts；不是 subject source |

Softpowers 与 Repository Operational Truth Audit 都保持独立。它们自己的 repo
拥有 Skill 和 cases；Field Lab 只保存 integration note 与有边界的 evidence。

## V0.2 release evidence

2026-08-30，installed v0.2 launcher 对 Repository Operational Truth Audit 的
snapshot 运行了一次显式 `source-artifact-split` canary：一次 target
invocation、零 LLM grader、requested `gpt-5.6-sol` / `high`、network disabled，
且没有 retry。Deterministic receipt 通过，另有一份 implementer-run human
review，只接受 pinned synthetic false-green claim。

它不证明 provider-resolved model identity、exclusive causality、subject 的
installed / activated behavior、任意 repo、owner acceptance、comparison
superiority 或 longitudinal reliability。详见 [bundle report](BUNDLE_REPORT.md)
与经过筛选的 [case study](case-studies/repository-operational-truth-audit.md)。

## 开发验证

```bash
python3 -m unittest discover -s tests -p 'test*.py'
python3 scripts/check_bundle.py
git diff --check
```

Runner regression 使用 fake adapters；普通 repo test 不会启动 target model。

## Licensing

Project-original functional materials 使用 SUL-1.0；project-original standalone
documentation 使用 CC BY-NC-SA 4.0。精确 path map 见 [LICENSING.md](LICENSING.md)。
第三方与独立 subject material 继续受它自己的条款约束。
