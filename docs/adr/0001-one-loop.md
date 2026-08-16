# 只有一个 Agent Loop

Coding agent 的下一步由模型在对话里选择工具，不由宿主脚本或第二条循环决定。所有机制（cron、后台通知、压缩、权限、Workflow、Goal）都挂在这一次 `while True` 上。

若为「监督」「编排」「定时」再开循环，状态会分裂，工具结果也不再有单一事实来源。

**Status**: accepted
