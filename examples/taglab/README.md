**简体中文** | [English](README.en.md)

# TagLab 使用说明

TagLab 用于公开文字的标注、模型对比和错误复核。目前以播客标题与简介为样本，判断主题和节目形式，并记录每个判断的原文依据。项目基于 Argilla 扩展，核心应用位于本目录。

## 从哪里开始

- 先看 [约 3 分钟的 Demo 步骤](docs/DEMO.md)，了解完整流程。
- 了解判断与版本设计，读 [原理与实现](docs/原理与实现.md) 和 [系统架构](docs/ARCHITECTURE.md)。
- 查看做过什么验证、还缺什么，读 [验证记录](docs/VALIDATION.md) 与 [实验记录](docs/PILOT-20261108.md)。

## 工作台怎样处理一次判断

盲标任务只展示输入与规范；机器复核任务展示某次实验、某个策略的候选。机器标签通过 Argilla 的 Suggestions 保存，用户提交通过 Responses 保存。

回传的回答需要通过输入、引用、规范和版本检查，再进入待裁决提案。明确裁决后才能更新人工参考。看过机器候选的复核意见不会通过盲标裁决入口变成独立参考；有争议的意见可以保留并请求后续复核。

每个导出包带内容指纹，数据集名称也包含该指纹。同一提案重复同步不会重复写入；已接收的完全相同提案按无操作处理，同一批任务仍可继续接收后续回答。

## 本地安装与测试

以下命令在本目录执行，测试环境为 Python 3.11：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-lock.txt
.venv\Scripts\python -m pytest tests workbench -q
```

依赖文件安装本 Fork 的 SDK。测试使用合成样本和独立数据库，当前 40 项通过。离线认证测试明确使用模拟 HTTP 响应，不代表真实服务器已连接。

## 启动 TagLab 工作台

新下载的仓库没有私人语料、参考或实验记录。先采集允许使用的公开 RSS 元数据，再启动：

```powershell
.venv\Scripts\python workbench\scripts\collect_podcasts.py
.venv\Scripts\python workbench\app.py
```

默认页面为 `http://127.0.0.1:8877/`。人工标注、离线规则与模型实验分别保留来源和结果。模型实验需要在本地页面填写自己的模型供应商配置；密钥只保存在服务内存，服务重启后重新填写。

## 启动 Argilla 标注服务

先让 Docker Desktop 的 Linux 引擎正常运行，再执行：

```powershell
.venv\Scripts\python prepare_runtime.py
docker compose --env-file private/runtime.env -f compose.yaml up -d
```

准备脚本检查引擎后，在 `private/runtime.env` 创建随机本地凭据，不覆盖已有文件。打开 `http://127.0.0.1:6900/`，使用其中的本地用户名和密码登录。Argilla 登录凭据与模型供应商密钥是两套配置。

部署使用官方 `argilla/argilla-server:v2.8.0` 镜像，仅对本机开放网页端口。项目没有修改上游网页和服务端源码。部署时的实际问题及处理见验证记录。

## 导出、上传与回收

工作台可以导出 pilot 或 dev 数据；留出集不会通过开发桥接导出。先检查导出包，离线构造 SDK 对象：

```powershell
.venv\Scripts\python taglab_argilla.py validate path/to/bundle.json
```

该命令报告 `server_sync: false`，只验证本地协议。真实同步需要在当前终端配置 `ARGILLA_API_URL` 与 `ARGILLA_API_KEY`，再执行：

```powershell
.venv\Scripts\python taglab_argilla.py push path/to/bundle.json --confirm-upload
.venv\Scripts\python taglab_argilla.py pull path/to/bundle.json --output private/proposals.json
```

`push` 创建数据集并通过 SDK 上传；`pull` 保存通过校验的提案及拒绝原因，不更新人工参考。工作台的 `argilla_bridge.py stage` 负责暂存，`accept` 是另一步显式裁决。

人工粘贴的引用只有在去除首尾空白后能连续匹配原文时，才做带审计的规范化。内部改写、标点差异和省略号拼接仍会被拒绝；模型输出校验规则不变。

## 检查真实服务往返

```powershell
.venv\Scripts\python live_smoke.py --confirm-local-qa
```

该命令读取本地凭据，在独立的 `taglab-qa` 工作空间创建合成记录和自动测试回答，并保存私人报告。它验证有效提交、草稿过滤、无效引用和输入篡改等路径，不写入真实参考，不调用模型。测试数据保留供检查。

## 参考修订后的离线复算

在已有数据与实验的工作台中执行：

```powershell
python reference_audit.py EXPERIMENT_ID
```

工具复用原输出另存参考修订分析，保留原实验。输入或标签规范变化时会拒绝复用；待复核参考不进入新评分。看过输出后的参考修订属于敏感性分析，分数变化不表示模型改进。

## 当前验证与使用范围

本地部署、网页提交、回传、裁决、重复同步和机器复核均已实际操作。一次 10 条样本、20 次请求的 A/B 运行中，18 次输出通过机械校验，后续仍发现语义支持不足的情况。

本地 7 条参考与 8 次实验用于验证流程，样本来源与主题覆盖有限。单人标注加助手依据复核不等于独立双人共识，争议反馈也不计入独立参考。详细数据与后续参考修订见实验记录。

上游 Apache-2.0 许可证和作者归属保留；来源基点、SDK 与服务版本见 [上游说明](UPSTREAM.md)。本仓库不包含私人语料、用户回答、完整模型输出或密钥。
