import httpx
import asyncio

# 从 .env 读取的 API Key
API_KEY = "sk-CBn0QTjWZ03Qv13fcagxXY6lGhCsTfraWH6eXlsJcgVqAEYj"

async def test_kimi():
    url = "https://api.moonshot.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "kimi-k2-turbo-preview",
        "messages": [{"role": "user", "content": "你好，请回复'测试成功'"}],
        "max_tokens": 50,
    }
    
    print("=" * 60)
    print("🧪 测试 Kimi API")
    print("=" * 60)
    print(f"API Key 前缀: {API_KEY[:8]}...")
    print(f"API Key 长度: {len(API_KEY)}")
    print(f"\n🔄 正在请求...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            print(f"\n📊 HTTP 状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(f"\n✅ 成功！")
                print(f"📝 AI 回复: {content}")
                print("\n" + "=" * 60)
                return True
            elif response.status_code == 401:
                print(f"\n❌ 认证失败 (401)")
                print(f"错误详情:\n{response.text}")
                print("\n可能原因:")
                print("1. API Key 无效或已过期")
                print("2. API Key 格式不正确")
                print("3. API Key 权限不足")
                print("\n" + "=" * 60)
                return False
            else:
                print(f"\n❌ 请求失败 ({response.status_code})")
                print(f"错误: {response.text[:500]}")
                print("\n" + "=" * 60)
                return False
    except Exception as e:
        print(f"\n❌ 异常: {type(e).__name__}: {e}")
        print("\n" + "=" * 60)
        return False

if __name__ == "__main__":
    result = asyncio.run(test_kimi())
    exit(0 if result else 1)
