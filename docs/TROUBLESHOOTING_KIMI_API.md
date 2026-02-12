# Kimi API 401 错误排查指南

## 🔍 问题症状

使用 Kimi API 时出现 `[AI 服务暂时不可用 (401)，请稍后重试]` 错误。

## ✅ 排查步骤

### 1. 检查 API Key 是否正确配置

#### 本地开发环境
检查 `backend/.env` 文件：
```bash
MOONSHOT_API_KEY=sk-你的API密钥
```

**注意：**
- API Key 应该以 `sk-` 开头
- 不要有多余的空格或换行符
- 不要用引号包裹（除非值本身包含特殊字符）

#### Zeabur 生产环境
1. 登录 Zeabur 控制台
2. 进入你的项目 → 服务 → Environment Variables
3. 检查是否有 `MOONSHOT_API_KEY` 环境变量
4. 确保值正确（以 `sk-` 开头，无多余空格）

### 2. 使用调试端点检查配置

访问调试端点查看当前配置状态：
```
GET /api/dating/debug/llm-status
```

返回示例：
```json
{
  "kimi": {
    "configured": true,
    "key_length": 45,
    "key_prefix": "sk-xxxxx...",
    "key_format_valid": true
  },
  "claude": {
    "configured": false,
    "key_length": 0,
    "key_prefix": ""
  },
  "active": "kimi"
}
```

### 3. 检查 API Key 有效性

#### 验证 API Key 格式
- ✅ 正确格式：`sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- ❌ 错误格式：
  - `sk-xxx `（末尾有空格）
  - `"sk-xxx"`（有引号）
  - `sk-xxx\n`（有换行符）
  - `MOONSHOT_API_KEY=sk-xxx`（包含了变量名）

#### 验证 API Key 权限
1. 登录 [Moonshot AI 控制台](https://platform.moonshot.cn/)
2. 检查 API Key 是否：
   - ✅ 已激活
   - ✅ 未过期
   - ✅ 有足够的余额/配额
   - ✅ 权限正确（chat 接口权限）

### 4. 检查日志

查看应用日志中的详细错误信息：
```bash
# 本地开发
python -m uvicorn backend.server:app --reload

# Zeabur 生产环境
# 在 Zeabur 控制台查看 Logs
```

查找以下日志：
- `Kimi API Key 已加载（长度: XX，前缀: sk-xxxx...）`
- `Kimi API 错误 401: ...`
- `API Key 认证失败！请检查：`

### 5. 常见问题及解决方案

#### 问题 1：API Key 未读取
**症状：** 日志显示 `Kimi API Key 未找到`

**解决方案：**
- 检查环境变量名称是否为 `MOONSHOT_API_KEY`（不是 `KIMI_API_KEY`）
- 确认 `.env` 文件在 `backend/` 目录下
- 重启应用（环境变量只在启动时加载）

#### 问题 2：API Key 格式不正确
**症状：** 日志显示 `Kimi API Key 格式可能不正确（应以 'sk-' 开头）`

**解决方案：**
- 确保 API Key 以 `sk-` 开头
- 检查是否有多余的空格或特殊字符
- 重新从 Moonshot AI 控制台复制 API Key

#### 问题 3：API Key 已过期或无效
**症状：** 401 错误，但 API Key 格式正确

**解决方案：**
1. 登录 Moonshot AI 控制台
2. 创建新的 API Key
3. 更新环境变量
4. 重启应用

#### 问题 4：Zeabur 环境变量未生效
**症状：** 本地正常，但 Zeabur 部署后 401

**解决方案：**
1. 在 Zeabur 控制台检查环境变量
2. 确保变量名完全匹配：`MOONSHOT_API_KEY`
3. 重新部署服务（环境变量更改需要重启）

### 6. 测试 API Key

使用 curl 直接测试 API Key：

```bash
curl https://api.moonshot.cn/v1/chat/completions \
  -H "Authorization: Bearer sk-你的API密钥" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kimi-k2-turbo-preview",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 100
  }'
```

如果返回 401，说明 API Key 本身有问题。
如果返回 200，说明 API Key 正常，问题在应用配置。

## 🔧 代码修复

已添加的改进：
1. ✅ API Key 自动清理（去除首尾空格和换行符）
2. ✅ 详细的错误日志（401 错误会输出具体检查项）
3. ✅ API Key 格式验证（检查是否以 `sk-` 开头）
4. ✅ 调试端点 `/api/dating/debug/llm-status`

## 📞 获取帮助

如果以上步骤都无法解决问题：
1. 检查 Moonshot AI 官方文档：https://platform.moonshot.cn/docs
2. 查看应用完整日志
3. 使用调试端点 `/api/dating/debug/llm-status` 获取配置状态
