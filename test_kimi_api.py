#!/usr/bin/env python3
"""测试 Kimi API 连通性和 API Key 有效性"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目路径
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir.parent))

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv(backend_dir / ".env")
except ImportError:
    print("⚠️  python-dotenv 未安装，尝试直接读取环境变量")

try:
    import httpx
except ImportError:
    print("❌ 请安装 httpx: pip install httpx")
    sys.exit(1)


async def test_kimi_api():
    """测试 Kimi API"""
    # 读取 API Key
    api_key = os.environ.get("MOONSHOT_API_KEY") or os.environ.get("KIMI_API_KEY")
    
    if not api_key:
        print("❌ 未找到 MOONSHOT_API_KEY 或 KIMI_API_KEY 环境变量")
        print("\n请检查：")
        print("1. backend/.env 文件是否存在")
        print("2. 环境变量名是否为 MOONSHOT_API_KEY")
        return False
    
    # 清理 API Key
    api_key = api_key.strip()
    
    print(f"✅ 找到 API Key（长度: {len(api_key)}，前缀: {api_key[:8]}...）")
    
    # 检查格式
    if not api_key.startswith("sk-"):
        print("⚠️  警告：API Key 格式可能不正确（应以 'sk-' 开头）")
    
    # 测试 API
    url = "https://api.moonshot.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "kimi-k2-turbo-preview",
        "messages": [
            {"role": "user", "content": "你好，请回复'测试成功'"}
        ],
        "max_tokens": 50,
        "temperature": 0.7,
    }
    
    print("\n🔄 正在测试 Kimi API 连接...")
    print(f"   请求 URL: {url}")
    print(f"   模型: {payload['model']}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            print(f"\n📊 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"].get("content", "")
                    print("✅ API 连接成功！")
                    print(f"📝 AI 回复: {content}")
                    return True
                else:
                    print("⚠️  API 返回成功，但响应格式异常")
                    print(f"   响应内容: {response.text[:200]}")
                    return False
            elif response.status_code == 401:
                print("❌ 认证失败 (401)")
                print("\n可能的原因：")
                print("1. API Key 无效或已过期")
                print("2. API Key 格式不正确（应类似 sk-xxx）")
                print("3. API Key 权限不足")
                print(f"\n错误详情: {response.text[:300]}")
                return False
            elif response.status_code == 429:
                print("⚠️  请求过于频繁 (429)，请稍后再试")
                return False
            else:
                print(f"❌ API 请求失败 ({response.status_code})")
                print(f"   错误详情: {response.text[:300]}")
                return False
                
    except httpx.TimeoutException:
        print("❌ 请求超时，请检查网络连接")
        return False
    except httpx.ConnectError:
        print("❌ 无法连接到 API 服务器，请检查网络")
        return False
    except Exception as e:
        print(f"❌ 发生异常: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Kimi API 连通性测试")
    print("=" * 60)
    
    result = asyncio.run(test_kimi_api())
    
    print("\n" + "=" * 60)
    if result:
        print("✅ 测试通过：Kimi API 连接正常")
    else:
        print("❌ 测试失败：请检查 API Key 配置")
    print("=" * 60)
    
    sys.exit(0 if result else 1)
