# Workflow 是工具，不是第二条循环

固定编排（审查多维度、可并行、要续跑）写成宿主注册的脚本，经 `Workflow` 工具进入主循环。模型只传 `name`、`args`、`resume_from_run_id`，不能提交可执行代码。

中间结果进 journal 和脚本变量，不灌进主对话。这和一次性 Subagent 不同：Subagent 是临场派一次；Workflow 是可恢复的宿主代码。

**Status**: accepted
