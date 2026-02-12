# 如何测试 Kimi API

## 🚀 快速测试方法

### 方法 1：双击运行批处理文件（最简单）
直接双击项目根目录下的 `test_kimi.bat` 文件

### 方法 2：命令行运行
在项目根目录打开命令行，执行：
```bash
python test_kimi_simple.py
```

### 方法 3：使用 curl（如果已安装）
```bash
curl https://api.moonshot.cn/v1/chat/completions ^
  -H "Authorization: Bearer sk-CBn0QTjWZ03Qv13fcagxXY6lGhCsTfraWH6eXlsJcgVqAEYj" ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"kimi-k2-turbo-preview\",\"messages\":[{\"role\":\"user\",\"content\":\"你好\"}],\"max_tokens\":50}"
```

## 📋 预期结果

### ✅ 成功的情况
```
============================================================
🧪 测试 Kimi API
============================================================
API Key 前缀: sk-CBn0Q...
API Key 长度: 45

🔄 正在请求...

📊 HTTP 状态码: 200

✅ 成功！
📝 AI 回复: 测试成功
============================================================
```

### ❌ 401 错误的情况
如果返回 401，可能的原因：
1. **API Key 无效或已过期** - 需要去 Moonshot AI 控制台重新生成
2. **API Key 格式问题** - 确保以 `sk-` 开头，无多余空格
3. **API Key 权限不足** - 检查是否有 chat 接口权限
4. **余额不足** - 检查账户余额

## 🔍 检查清单

- [ ] `.env` 文件中 `MOONSHOT_API_KEY` 已正确设置
- [ ] API Key 以 `sk-` 开头
- [ ] API Key 无多余空格或换行
- [ ] 已安装 `httpx`：`pip install httpx`
- [ ] 网络连接正常

## 📞 如果测试失败

1. **检查 API Key 有效性**
   - 登录 https://platform.moonshot.cn/
   - 查看 API Key 是否激活
   - 检查余额和配额

2. **查看详细错误**
   - 运行测试脚本会显示详细错误信息
   - 401 错误会显示具体的错误原因

3. **验证环境变量**
   - 确认 `backend/.env` 文件存在
   - 确认变量名为 `MOONSHOT_API_KEY`（不是 `ANTHROPIC_API_KEY`）
