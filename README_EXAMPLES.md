# Examples

## 0. 环境变量
- `LLM_PROVIDER`: `ollama` 或 `mock` (默认 `mock`)
- `LLM_MODEL`: 例如 `llama3.1`
- `LLM_EMBED_MODEL`: 例如 `nomic-embed-text` 或 `llama3.1` (默认与 `LLM_MODEL` 相同)
- `LLM_BASE_URL`: 默认 `http://localhost:11434`

## 依赖说明
- 示例仅使用标准库，无需安装第三方依赖。

## 1. 最小 LLM CLI
```bash
python /Users/a147735/agent_study/agent_project/examples/llm_cli.py "你好，介绍一下Agent"
```

## 2. 最小 RAG
```bash
python /Users/a147735/agent_study/agent_project/examples/rag_basic.py
```

## 3. 工具调用示例
```bash
python /Users/a147735/agent_study/agent_project/examples/tool_call.py
```

## 4. 记忆示例（分层记忆 + 检索策略）
```bash
python /Users/a147735/agent_study/agent_project/examples/memory_agent_v2.py
```

清空记忆：
```bash
python /Users/a147735/agent_study/agent_project/examples/memory_agent_v2.py --reset
```

## 5. 记忆导出/可视化
```bash
python /Users/a147735/agent_study/agent_project/examples/memory_export.py --out /Users/a147735/agent_study/agent_project/data/memory.json
python /Users/a147735/agent_study/agent_project/examples/memory_export.py --out /Users/a147735/agent_study/agent_project/data/memory.md
python /Users/a147735/agent_study/agent_project/examples/memory_export.py --out /Users/a147735/agent_study/agent_project/data/memory.html
```

## 6. 端到端链路 API（记忆 + RAG + 工具）
```bash
PYTHONPATH=/Users/a147735/agent_study/agent_project/src \
python3 /Users/a147735/agent_study/agent_project/src/agent_project/api_server.py
```

测试请求：
```bash
curl -X POST http://127.0.0.1:8080/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"u1","message":"请告诉我北京时间，并解释RAG是什么"}'
```

## 7. 使用 Ollama 的示例
```bash
export LLM_PROVIDER=ollama
export LLM_MODEL=llama3.1
export LLM_EMBED_MODEL=nomic-embed-text
export LLM_BASE_URL=http://localhost:11434
```
