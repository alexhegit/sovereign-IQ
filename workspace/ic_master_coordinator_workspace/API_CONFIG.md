# SIQ 投委会 API 配置

## 已配置 API

### 1. 企查查 API ✅
- **状态**: 已配置
- **CLI 工具**: `qcc-agent-cli` (已安装并初始化)
- **配置文件**: `~/.qcc/config.json`
- **可用端点**:
  - `qcc-company` - 企业工商信息 (12 个工具)
  - `qcc-risk` - 风险信息 (5 个工具)
  - `qcc-ipr` - 知识产权 (3 个工具)
  - `qcc-operation` - 经营信息 (3 个工具)

### 2. Tavily API ✅
- **状态**: 已配置
- **API Key**: `tvly-dev-...` (已保存至 ~/.openclaw/.env)
- **用途**: 新闻检索、舆情分析、市场动态
- **可用工具**: `~/.openclaw/skills/openclaw-tavily-search/scripts/tavily_search.py`

### 3. Exa API ✅
- **状态**: 已配置
- **API Key**: `636a31f8-...` (已保存至 ~/.openclaw/.env)
- **用途**: 深度网络检索、竞品分析、技术文档检索
- **使用方式**: 通过 agent-reach 或自定义脚本调用

---

## 配置验证

所有 API 已配置完成，可立即用于 SIQ 尽调流程。

## 使用建议

- **企查查**: 用于企业工商信息校验（R0 阶段核心工具）
- **Tavily**: 用于新闻/舆情检索（R1-R3 阶段补充信息）
- **Exa**: 用于深度技术/竞品分析（R2-R3 阶段交叉验证）