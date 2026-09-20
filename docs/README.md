# Documentation map · 文档地图

Start with the question you came to answer. This page routes readers; the
linked contracts remain authoritative. 阅读顺序服务你的问题，不改变规范的权威顺序。

## Choose a reading path · 按问题开始

| Your task · 你想做什么 | Read in this order · 阅读顺序 |
| --- | --- |
| Understand the product · 第一次理解产品 | [English overview](../README.md) / [中文介绍](../README.zh-CN.md) → [Architecture](ARCHITECTURE.md) / [中文架构](ARCHITECTURE.zh-CN.md) |
| Install and try it · 安装与初次使用 | [Installation](INSTALLATION.md) → [Lab examples](../README.md#start-a-v2-lab) / [中文示例](../README.zh-CN.md#建立一个-v2-lab) |
| Return to maintenance · 继续维护 | [AGENTS](../AGENTS.md) → [Current state](CURRENT_STATE.md) → [Product spec](PRODUCT_SPEC_V0.2.md) → [Contributing](../CONTRIBUTING.md) |
| Connect a local subject · 接入本地 subject | [Workspace model](WORKSPACE_MODEL_V0.2.md) → [V2 records and schemas](SCHEMA_DELTA_V1_TO_V2.md) |
| Interpret evidence · 判断 receipt 能证明什么 | [Evidence model](EVIDENCE_MODEL.md) → [Case studies](../case-studies/README.md) |
| Understand execution boundaries · 理解执行边界 | [Architecture](ARCHITECTURE.md) / [中文架构](ARCHITECTURE.zh-CN.md) → [Adapter contract](ADAPTER_CONTRACT.md) → [Quota and spend](QUOTA_AND_SPEND.md) |
| Migrate an old pack · 迁移 v1 pack | [V1-to-v2 migration](MIGRATION_V1_TO_V2.md) → [Schema delta](SCHEMA_DELTA_V1_TO_V2.md) |
| Check a distributed version · 核对分发版本 | [Current state](CURRENT_STATE.md) → [Changelog](../CHANGELOG.md) → [Packaging](PACKAGING.md) |

## Where truth lives · 各类事实的权威来源

| Surface | Owns · 负责什么 |
| --- | --- |
| [Product spec](PRODUCT_SPEC_V0.2.md) | Accepted product behavior and acceptance contract · 产品行为与验收合同 |
| [Workspace model](WORKSPACE_MODEL_V0.2.md) | Subject identity, materialization, drift, retention and write boundaries · subject 身份、物化与写入边界 |
| [Evidence model](EVIDENCE_MODEL.md) | Receipt/review interpretation and claim ceilings · 证据解释与结论上限 |
| [Schema delta](SCHEMA_DELTA_V1_TO_V2.md) and [schemas/v2](../schemas/v2/) | Record semantics and active machine-readable schemas · record 语义与有效 schema |
| [AGENTS](../AGENTS.md) | Repository development, verification and authorization rules · 仓库内开发约束 |
| [Current state](CURRENT_STATE.md) | Dated source, support and release/evidence state · 有日期的当前状态 |
| Root READMEs and paired Architecture pages | Product explanation and navigation · 产品解释与导航，不是并行规范 |
| [Installation](INSTALLATION.md), [Packaging](PACKAGING.md), [Adapter contract](ADAPTER_CONTRACT.md), [Quota and spend](QUOTA_AND_SPEND.md) | Operations and focused technical contracts · 操作指南与专题合同 |
| [Changelog](../CHANGELOG.md) | Shipped changes · 已发布历史 |
| [Bundle report](../BUNDLE_REPORT.md), [test report](../TEST_REPORT.txt), [case studies](../case-studies/README.md) | Dated evidence with explicit limits · 有日期、有边界的证据，不是下一轮施工指令 |
| [Licensing](../LICENSING.md) and [Provenance](../PROVENANCE.md) | Path-specific terms and source attribution · 路径许可与来源 |

## Historical context · 历史背景

These completed records preserve why the current design exists. They are not
an active plan or a second runtime. 以下文档保留决策来路，不作为当前待办：

- [V0.2 implementation and acceptance plan](history/v0.2-implementation-plan.md)
- [Mechanisms carried over from Softpowers](history/source-carryover-from-softpowers.md)
- [Completed migration from embedded Soft Eval](history/migration-from-soft-eval.md)

[V1-to-v2 migration](MIGRATION_V1_TO_V2.md) remains an active user guide;
[schemas/v1](../schemas/v1/) remains historical migration reference.
