**简体中文** | [English](README.en.md)

# TagLab · 内容标注与模型评测工作台

TagLab 把人工标注、模型 A/B 输出和错误复核放在同一条流程里。遇到一个判断时，可以回看模型读过的文字、它引用的依据、人的修改，以及修改前后的评分。

当前以播客标题与简介分类为例：选择主要主题和节目形式，附上原文依据；资料不足时允许保留“无法判断”。项目基于 [Argilla](https://github.com/argilla-io/argilla) 扩展，应用代码位于 [examples/taglab](examples/taglab/README.md)。

## 主要功能

- **独立标注**：先读资料再判断，盲标任务不显示机器建议和已有参考。
- **模型 A/B 对比**：相同输入与生成参数下，对比基础提示词和带定义、反例的提示词。
- **依据检查**：校验引用是否逐字连续出现在输入中，再单独复核它是否支持结论。
- **反馈与裁决**：保留回答者、争议、输入版本和裁决理由，机器建议与人工参考分开保存。
- **历史与复算**：旧实验保留原快照；参考修订后可复用原输出另做分析，记录分数为什么变化。

流程：**公开资料 → 清洗与版本记录 → 人工盲标 / 模型实验 → 依据校验 → 争议复核 → 显式裁决 → 评测与归档**。

## 产品设计与能力实践

项目围绕两条相互关联的工作展开：一条是整理内容数据、建立参考并评估模型；另一条是把模糊判断写成规则，通过错误案例验证策略，再决定是否调整。

| 方向 | 在项目中的实践 |
| --- | --- |
| 内容理解与标签设计 | 将主题与节目形式分开判断，定义标签边界、正反例与“无法判断”选项。 |
| 评测与数据质量 | 记录清洗前后差异，区分机器建议、人工回答与评分参考；共同输入下比较两种提示策略。 |
| 规则与策略设计 | 将“不要猜测”落实为输出约束、依据要求和人工裁决条件，而不只依赖提示词。 |
| 错误分析与策略验证 | 分开处理格式错误、无效引用、语义支持不足和参考争议；保留实验条件与修订记录。 |

详见 [产品设计与策略验证](examples/taglab/docs/PRODUCT.md)：任务如何定义、关键取舍、失败案例及评测指标。当前验证对象是播客标题与简介，没有进行音频理解或线上用户分流实验。

## 已完成的验证

截至 2026-11-08，已完成本地 Docker 部署、网页标注与回传、同一批任务的重复同步，以及模型候选的独立复核任务。应用测试共 **40 项通过**。

一次固定 10 条输入的真实 A/B 运行发出 20 次请求，18 次输出通过格式与连续引用检查。后续发现了引用存在但不足以证明节目形式的案例，也保留了用户与规范之间的争议。参考修订后的评分单独保存，原输出和旧分数不被覆盖。

本机目前保留 7 条人工参考与 8 次实验。样本集中在两档偏商业、科技的节目，参考数量较少；这些记录用于验证流程和发现问题，不能作为模型整体质量或策略优胜的结论。详见 [小样本实验记录](examples/taglab/docs/PILOT-20261108.md)。

## 阅读入口

| 内容 | 中文 | English |
| --- | --- | --- |
| 产品问题、规则与策略验证 | [产品设计](examples/taglab/docs/PRODUCT.md) | [Product design](examples/taglab/docs/PRODUCT.en.md) |
| 使用、安装与测试 | [使用说明](examples/taglab/README.md) | [Guide](examples/taglab/README.en.md) |
| 约 3 分钟的演示 | [Demo 步骤](examples/taglab/docs/DEMO.md) | [Demo](examples/taglab/docs/DEMO.en.md) |
| 技术原理与案例 | [原理与实现](examples/taglab/docs/原理与实现.md) | [Principles](examples/taglab/docs/PRINCIPLES.en.md) |
| 架构与指标 | [架构与评测](examples/taglab/docs/ARCHITECTURE.md) | [Architecture](examples/taglab/docs/ARCHITECTURE.en.md) |
| 验证范围与限制 | [验证记录](examples/taglab/docs/VALIDATION.md) | [Validation](examples/taglab/docs/VALIDATION.en.md) |
| 实际实验与复核 | [实验记录](examples/taglab/docs/PILOT-20261108.md) | [Pilot notes](examples/taglab/docs/PILOT-20261108.en.md) |
| 开源来源 | [上游说明](examples/taglab/UPSTREAM.md) | [Provenance](examples/taglab/UPSTREAM.en.md) |

新下载的仓库只包含代码、文档和合成测试数据。原始语料、私人标注、完整实验输出和密钥保留在本机；安装及数据准备见使用说明。

## 与上游的关系

本仓库是 Argilla 的应用扩展 Fork。新增工作台、数据交换、依据校验和评测逻辑，并修复了 SDK 的依赖声明和自定义 HTTP transport 传参问题。网页标注服务使用官方 `v2.8.0` 镜像，未修改上游网页和服务端源码。

保留上游 [Apache-2.0 许可证](LICENSE)、作者归属和 [原始项目介绍](README.upstream.md)。
