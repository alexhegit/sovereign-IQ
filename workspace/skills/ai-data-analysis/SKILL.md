# Data Analysis Service

自动化数据处理和洞察分析服务。

## 能力

- CSV/Excel 数据处理
- 数据清洗和转换
- 统计分析和可视化
- 趋势识别
- 异常检测
- 报告生成

## 使用方式

```bash
# 分析CSV数据
openclaw run data-analysis --file data.csv --analysis "sales_trends"

# 处理Excel
openclaw run data-analysis --file sales.xlsx --output report.md

# 数据清洗
openclaw run data-analysis --file data.csv --action "clean" --format "json"

# 生成可视化图表
openclaw run data-analysis --file metrics.csv --chart "bar" --output charts/
```

## 核心功能

### 数据处理
- 支持 CSV, Excel, JSON
- 自动类型推断
- 缺失值处理
- 数据标准化

### 统计分析
- 描述性统计
- 假设检验
- 相关性分析
- 回归分析

### 可视化
- 趋势图
- 柱状图
- 折线图
- 散点图
- 热力图

### 报告生成
- PDF/HTML 导出
- 自定义模板
- 数据仪表板

## 特性

- ✅ 本地处理，数据隐私安全
- ✅ 支持大数据集
- ✅ 可导出 PDF/HTML
- ✅ 可视化图表库
- ✅ Pandas 集成

## 依赖

- Python 3.7+
- pandas
- numpy
- matplotlib
- seaborn
- jinja2

## 开发者

OpenClaw AI Agent
License: MIT
Version: 2.0.0