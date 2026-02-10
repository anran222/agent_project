# Memory Architecture (Agent Project)

## 目标
在可控成本下实现“可用、稳定、可扩展”的记忆系统：
- 短期记忆：最近对话
- 长期记忆：可检索历史事实/任务
- 摘要记忆：减少上下文噪音
- 用户画像：稳定偏好

## 组件
- MemoryStore: SQLite 存储层
- MemoryManager: 记忆写入与检索策略
- LLMClient: 生成与总结（可用Ollama）

## 数据模型
- messages: 短期对话
- memory_items: 长期记忆（fact/task/preference）
- memory_summary: 对话摘要
- user_profile: 用户画像（key/value）
- tasks: 任务状态

## 写入策略
- LLM 结构化抽取：profile_updates / facts / preferences / tasks
- 任务状态自动更新：tasks 表随对话推进更新 status/notes
- 每 N 轮对话 → summary（LLM自动摘要）
- 可选遗忘：抽取的 forget 列表会清理匹配记忆

## 检索策略
- 短期：最近 N 轮
- 长期：向量相似度（Ollama Embedding）+ importance 加权
- 摘要：最近一条摘要
- 任务：最近打开任务

## Prompt 组装优先级
1. User Profile
2. Conversation Summary
3. Open Tasks
4. Long-term Memory
5. Recent Messages

## 端到端链路（API）
1. 用户输入
2. LLM 结构化抽取写入记忆
3. 记忆检索（短期/摘要/任务/长期）
4. RAG 检索知识库
5. 工具调用决策（必要时执行）
6. 组装 Prompt → LLM 生成
7. 写回记忆

## 后续可升级方向
- 语义向量库（FAISS/Milvus）
- 混合检索（BM25 + Embedding）
- LLM 驱动的结构化画像抽取
- 自动记忆清理与过期策略（已加入基础版本）
- 记忆面板可视化（已加入导出 HTML/MD/JSON）
