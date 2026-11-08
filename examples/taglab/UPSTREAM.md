**简体中文** | [English](UPSTREAM.en.md)

# 上游来源与改动范围

- 上游仓库：[argilla-io/argilla](https://github.com/argilla-io/argilla)
- 当前 Fork：[MariaMaizi/taglab-argilla](https://github.com/MariaMaizi/taglab-argilla)
- 基础分支：`develop`
- 基础提交：`5338519accb13ae422f8bf9c0642651c249c49af`
- 应用扩展分支：`taglab/podcast-review`
- 许可证：Apache-2.0，原许可证保留在仓库根目录。
- 安装的 Fork SDK：源代码报告版本为 `2.8.0.dev0`。
- 本地服务镜像：官方 `argilla/argilla-server:v2.8.0`，并非自行构建的 Fork 服务端镜像。

应用新增与修改集中在 `examples/taglab/`。另有两处 SDK 修复：补充 `requests` 依赖声明，并支持显式传入自定义 HTTP transport。上游服务端和网页前端没有被本应用修改。

上游 README 说明原作者已转向新项目，后续重点是修复和补丁。本仓库用于应用实践与扩展，不代表获得上游官方背书，也不宣称改动已被上游接收。根目录单独保存了上游原始 README。
