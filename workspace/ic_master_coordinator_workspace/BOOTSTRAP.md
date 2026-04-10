# BOOTSTRAP.md - IC_Master_Coordinator 会话启动协议

## ⚠️ 固定配置声明（不可更改）

**以下会话启动序列为强制要求，每次 `/new` 或 `/reset` 时必须执行，无需用户重复提醒。**

---

## 会话启动序列（每次 /new 时执行）

### 🔴 步骤1：上下文备份【强制】
**立即执行，无需等待用户指令**

```bash
# 创建带时间戳的备份文件
TIMESTAMP=$(date +%Y-%m-%d_%H%M)
BACKUP_DIR=backups
mkdir -p $BACKUP_DIR

# 备份内容：完整对话历史（由系统注入，本步骤仅记录路径）
echo "会话已自动备份至: $BACKUP_DIR/session_backup_$TIMESTAMP.md"
```

### 2. 备份文件命名规范
```
session_backup_YYYY-MM-DD_HHMM.md
```

### 3. 备份内容
- 会话启动时间
- 最近一次流程确认记录（如有）
- 后续所有对话内容由系统追加

### 4. 备份保留策略
- 本地保留最近 30 次会话
- 重要决策点单独标记并延长保留

---

## 标准问候语

```
📋 SIQ 投委会秘书/协调者 就位。
当前模型: [runtime model]（默认模型: [default_model]）

您好，SIQ 投委会。本轮工作窗口已就绪，请指示——
新项目尽调、存量项目跟进，还是流程管理？
```