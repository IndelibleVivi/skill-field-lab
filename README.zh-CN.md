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

最新已发布版本为 **v0.2.0**；本 checkout 是 **0.2.1 source candidate（尚未发布）**。
当前候选检查与历史 v0.2.0 安装／live 证据分别见 [bundle report](BUNDLE_REPORT.md)。
本机 installation、Git tag、published assets、controller discovery 与 owner acceptance
仍是独立的可观察状态。

每个 target attempt 在调用前将实际 subject mount 与 saved plan 的 tree digest 对比；
Git subject 使用计划里已解析的 commit。交付不一致时，以 `input-drift` 停止后续 matrix，
该 attempt 的 target calls 为零；materialization 错误归入 `preflight-failed`。
metadata、verification 和 receipt 都保留 `subject_delivery`，同时区分 host selection
仍为 unknown、content application 需要 semantic review。每次 repeat 和 matched control
都经过同一边界。

Trace 输出 `command_reference_mentions`，对应 assertion 为
`command_reference_mentions_include`；`echo references/example.md` 也会产生 mention，
不能据此证明读取内容。旧 `reference_reads_include` 是保留的 deprecated v2 assertion
alias。`activation` 仅声明场景，不证明宿主实际激活了 Skill。

`selftest` 为每个 case 报告 `deterministic_oracle_status`、已执行／未执行 surfaces 与
零 target invocations。它只在 fixture／expected overlay 上测试已声明的 workspace 和
command assertions；result、trace assertions 和 human review 仍未执行。旧 `oracle_status`
保留为 deterministic status 的兼容 alias。

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

## 先 explain claim，再决定是否相信它

`fieldlab explain` 是 read-only 的。它从 claims、immutable receipts 和独立
reviews 重新计算一个 claim 的 evidence view，不会直接相信手写的
`claim.status`，也不会把 `PASS` 当作结论：

```bash
fieldlab explain /path/to/my-study/fieldlab.json --claim one-bounded-claim
```

报告会把 `supported`、`unsupported`、`inconclusive` 分开，并在 bound reviews
彼此冲突时给出 `mixed`；在 receipt 有记录时显示 subject identity、sealed
worker-final output、verifier attribution、declared review material 与
retention。同一个 receipt 被复制到多个 canonical location 时会按 digest
deduplicate；缺少 worker-final boundary marker 的 legacy receipt 会标记为
`legacy-ambiguous`。报告还列出 pending、failed 或 conflicting 的 review
requirements，以及 missing 或 digest-drifted 的 artifacts，并给出最小的 next
evidence gap。`--json` 输出同样的结构，方便工具消费。它不启动 target model，
也不修改 lab 或 subject。

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

Runner 会在任何 verifier process 启动之前，先 seal worker-final 的
changed-file set、diff 与 tree digest。Workspace assertions 读取这些 sealed
worker bytes；每条 command assertion 都从同一棵 sealed tree 的**独立** byte
copy 开始，因此不会继承其他 command 的修改。copy 内的改动会被 attribution 为
verifier-derived，不能把 worker 结果变成干净的 `pass`，copy 在 attempt 结束后
删除。seal diff 使用 disposable Git index copy，因此不会改动 workspace 自身的
index bytes 与 cached diff。这是 protected-source/derived-output contract，
不是对 OS-level containment 的声明。

Live worker workspace 不再默认保留。Case 声明了 human-review requirements 时，
可以再声明 `human_review_material`：pending review 真正需要的、精确的
workspace-relative 文件路径。Glob、目录、symlink、逃逸路径、缺失文件或超限集合
都会被拒绝。Declared files 在任何 verifier 运行之前被原子复制到 attempt 自己的
`review-material/`，并附带记录精确 path、digest、byte size 与固定 limits 的
manifest；manifest digest 与 status 绑定进 `verification.json` 和 immutable
receipt。capture 失败属于 evidence-sealing error：不会留下 partial material
set，也不会产生正常 receipt，并会记录为独立的 `evidence-failed` attempt/run
state（而不是 `termination-failed`）。只有 review requirements、没有 declared
material 的 case 依赖标准 attempt artifacts（`case.json`、`prompt.md`、
`trace.jsonl`、`stderr.log`、`final-output.md`、`diff.patch`、
`verification.json`）。`keep_workspace=true` 仍然是唯一保留整个 workspace 的
开关。

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

另外，subject 自己于 2026-09-17 发布了 `v0.2.0`，附带覆盖 routing、Audit 与
one-request Operate 行为的公开 forward receipt，以及 maintainer 侧的
source-owner gate。Field Lab 把它记为 imported、有日期的 observed evidence，并
保留明确的 ceiling：它不是 Field Lab rerun、raw trace，也不是
installed / discovery / fresh-host / publication proof。
[case study](case-studies/repository-operational-truth-audit.md) 保留
2026-08-30 的历史，并新增 2026-09-17/18 章节。

## 开发验证

```bash
python3 -m unittest discover -s tests -p 'test*.py'
python3 scripts/check_bundle.py
skill-validate skills/pattern-intake
skill-validate skills/skill-eval
git diff --check
```

Runner regression 使用 fake adapters；普通 repo test 不会启动 target model。

## Licensing

Project-original functional materials 使用 SUL-1.0；project-original standalone
documentation 使用 CC BY-NC-SA 4.0。精确 path map 见 [LICENSING.md](LICENSING.md)。
第三方与独立 subject material 继续受它自己的条款约束。
