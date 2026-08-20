# Hearth

一个 **coding agent harness**：给模型工具、工作区、权限和生命周期，不替模型做推理。

模型负责推理和选工具。本仓库负责：一个循环、工具、权限、以及以后挂上的压缩、记忆、MCP、Workflow、Goal。

## 新工作区怎么开

1. 用 Cursor 打开本目录。
2. 复制 `.env.example` 为 `.env`，填 `ANTHROPIC_API_KEY` 和 `MODEL_ID`。
3. `python -m venv .venv` 后安装：`pip install -e ".[dev]"`。
4. 把 [FIRST_PROMPT.md](FIRST_PROMPT.md) 贴进新 Agent 对话，按 MVP 往下写。
5. 先读 [AGENTS.md](AGENTS.md) 和 [CONTEXT.md](CONTEXT.md)。

## 命令

```text
pytest
hearth
hearth "列出当前目录里的 Python 文件"
```

## 文档

| 文件 | 用途 |
|------|------|
| [CONTEXT.md](CONTEXT.md) | 领域词，写代码时用这些词 |
| [AGENTS.md](AGENTS.md) | 给 Cursor Agent 的硬约束 |
| [docs/architecture.md](docs/architecture.md) | 循环与模块接缝 |
| [docs/phased-plan.md](docs/phased-plan.md) | MVP → v1 → v2 |
| [docs/adr/](docs/adr/) | 不可轻易推翻的决定 |

## 原则

只有一个 Agent Loop。新能力进 Tool Pool 或 Hook，不进循环分支。
