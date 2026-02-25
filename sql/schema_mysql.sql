CREATE DATABASE IF NOT EXISTS agent_project
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE agent_project;

CREATE TABLE IF NOT EXISTS users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户主键ID',
  phone VARCHAR(20) NOT NULL UNIQUE COMMENT '手机号（登录账号，唯一）',
  password_hash VARCHAR(128) NOT NULL COMMENT '密码哈希（PBKDF2结果）',
  salt VARCHAR(64) NOT NULL COMMENT '密码加盐值',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB COMMENT='用户账号表';

CREATE TABLE IF NOT EXISTS messages (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '消息主键ID',
  session_id VARCHAR(64) NOT NULL COMMENT '会话标识（当前代码中实际使用 user_id 字符串）',
  role VARCHAR(16) NOT NULL COMMENT '消息角色：user / assistant / system',
  content TEXT NOT NULL COMMENT '消息正文',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX idx_messages_session (session_id)
) ENGINE=InnoDB COMMENT='对话消息表（短期记忆）';

CREATE TABLE IF NOT EXISTS memory_items (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '记忆条目主键ID',
  session_id VARCHAR(64) NOT NULL COMMENT '会话标识（当前代码中实际使用 user_id 字符串）',
  mem_type VARCHAR(32) NOT NULL COMMENT '记忆类型：fact / preference / task 等',
  content TEXT NOT NULL COMMENT '记忆内容文本',
  importance DOUBLE NOT NULL COMMENT '重要性分数（越高越重要）',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX idx_memory_session (session_id)
) ENGINE=InnoDB COMMENT='长期记忆条目表';

CREATE TABLE IF NOT EXISTS memory_vectors (
  item_id BIGINT PRIMARY KEY COMMENT '关联 memory_items.id（一条记忆对应一个向量）',
  vector JSON NOT NULL COMMENT '向量数据（embedding数组）',
  model VARCHAR(64) NOT NULL COMMENT '生成该向量的模型名',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  FOREIGN KEY (item_id) REFERENCES memory_items(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='记忆向量表（用于语义检索）';

CREATE TABLE IF NOT EXISTS memory_summary (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '摘要主键ID',
  session_id VARCHAR(64) NOT NULL COMMENT '会话标识（当前代码中实际使用 user_id 字符串）',
  summary TEXT NOT NULL COMMENT '对话阶段性摘要',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX idx_summary_session (session_id)
) ENGINE=InnoDB COMMENT='会话摘要表';

CREATE TABLE IF NOT EXISTS user_profile (
  session_id VARCHAR(64) NOT NULL COMMENT '会话标识（当前代码中实际使用 user_id 字符串）',
  `key` VARCHAR(64) NOT NULL COMMENT '画像字段名（如 name/city/preference）',
  value TEXT NOT NULL COMMENT '画像字段值',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (session_id, `key`)
) ENGINE=InnoDB COMMENT='用户画像KV表';

CREATE TABLE IF NOT EXISTS tasks (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '任务主键ID',
  session_id VARCHAR(64) NOT NULL COMMENT '会话标识（当前代码中实际使用 user_id 字符串）',
  title VARCHAR(255) NOT NULL COMMENT '任务标题（同session下唯一）',
  status VARCHAR(32) NOT NULL COMMENT '任务状态：open / done / cancelled',
  notes TEXT COMMENT '任务备注',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE KEY uniq_task (session_id, title)
) ENGINE=InnoDB COMMENT='任务状态表';

CREATE TABLE IF NOT EXISTS chat_sessions (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '会话主键ID',
  user_id BIGINT NOT NULL COMMENT '所属用户ID（users.id）',
  title VARCHAR(255) NOT NULL COMMENT '会话标题',
  last_message_preview VARCHAR(255) NOT NULL DEFAULT '' COMMENT '最近一条消息的摘要',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX idx_chat_sessions_user_updated (user_id, updated_at),
  CONSTRAINT fk_chat_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='聊天会话表';

CREATE TABLE IF NOT EXISTS chat_messages (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '消息主键ID',
  session_id BIGINT NOT NULL COMMENT '会话ID（chat_sessions.id）',
  user_id BIGINT NOT NULL COMMENT '所属用户ID（冗余字段，便于审计）',
  role VARCHAR(16) NOT NULL COMMENT '消息角色：user / assistant / system',
  content TEXT NOT NULL COMMENT '消息正文',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX idx_chat_messages_session_id (session_id, id),
  CONSTRAINT fk_chat_messages_session FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='聊天消息表（前端会话历史）';


