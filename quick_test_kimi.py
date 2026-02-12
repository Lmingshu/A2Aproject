import os
import sys
import asyncio
from pathlib import Path

# 直接读取 .env 文件
env_file = Path(__file__).parent / "backend" / ".env"
api_key = None

if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('MOONSHOT_API_KEY='):
                api_key = line.split('=', 1)[1].strip()
                break
            elif line.startswith('KIMI_API_KEY='):
                api_key = line.split('=', 1)[1].strip()
                break
            elif line.startswith('ANTHROPIC_API_KEY=') and not api_key:
                api_key = line.split('=', 1)[1].strip()
                break

if not api_key:
    print("❌ 未找到 API Key")
    sys.exit(1)

api_key = api_key.strip()
print(f"✅ 找到 API Key（长度: {len(api_key)}，前缀: {api_key[:8]}...）")

try:
    import httpx
except ImportError:
    print("❌ 请安装 httpx: pip install httpx")
    sys.exit(1)

async def test():
    url = "https://api.moonshot.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "kimi-k2-turbo-preview",
        "messages": [{"role": "user", "content": "你好，请回复'测试成功'"}],
        "max_tokens": 50,
    }
    
    print(f"\n🔄 正在测试 Kimi API...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            print(f"📊 状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(f"✅ 成功！AI 回复: {content}")
                return True
            elif response.status_code == 401:
                print(f"❌ 认证失败 (401)")
                print(f"错误: {response.text[:300]}")
                return False
            else:
                print(f"❌ 失败 ({response.status_code})")
                print(f"错误: {response.text[:300]}")
                return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

result = asyncio.run(test())
sys.exit(0 if result else 1)
