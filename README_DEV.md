# 开发说明

## 建议环境
- Python 3.10+
- 虚拟环境（venv/uv/conda任选其一）

## 快速开始
```bash
cd /Users/a147735/agent_study/agent_project
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn agent_project.app.api.server:app --host 127.0.0.1 --port 8000 --app-dir src
```
