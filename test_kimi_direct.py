#!/usr/bin/env python3
"""直接测试 Kimi API（使用 .env 中的 API Key）"""

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
    print("✅ 已加载 .env 文件")
except ImportError:
    print("⚠️  python-dotenv 未安装")
except Exception as e:
    print(f"⚠️  加载 .env 失败: {e}")

try:
    import httpx
except ImportError:
    print("❌ 请安装 httpx: pip install httpx")
    sys.exit(1)


async def test():
    """测试 Kimi API"""
    # 读取 API Key（按优先级）
    api_key = (
        os.environ.get("MOONSHOT_API_KEY") or 
        os.environ.get("KIMI_API_KEY") or
        os.environ.get("ANTHROPIC_API_KEY")  # 兼容旧配置
    )
    
    print("\n" + "=" * 60)
    print("🧪 Kimi API 连通性测试")
    print("=" * 60)
    
    if not api_key:
        print("\n❌ 未找到 API Key")
        print("\n检查的环境变量：")
        print("  - MOONSHOT_API_KEY:", os.environ.get("MOONSHOT_API_KEY", "未设置"))
        print("  - KIMI_API_KEY:", os.environ.get("KIMI_API_KEY", "未设置"))
        print("  - ANTHROPIC_API_KEY:", os.environ.get("ANTHROPIC_API_KEY", "未设置"))
        print("\n💡 请在 backend/.env 文件中设置：")
        print("   MOONSHOT_API_KEY=sk-你的API密钥")
        return False
    
    api_key = api_key.strip()
    print(f"\n✅ 找到 API Key")
    print(f"   长度: {len(api_key)}")
    print(f"   前缀: {api_key[:8]}...")
    
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
    
    print(f"\n🔄 正在测试...")
    print(f"   URL: {url}")
    print(f"   模型: {payload['model']}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            print(f"\n📊 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"].get("content", "")
                    print("\n✅ API 连接成功！")
                    print(f"📝 AI 回复: {content}")
                    return True
                else:
                    print("\n⚠️  API 返回成功，但响应格式异常")
                    print(f"   响应: {response.text[:300]}")
                    return False
            elif response.status_code == 401:
                print("\n❌ 认证失败 (401)")
                print("\n可能的原因：")
                print("  1. API Key 无效或已过期")
                print("  2. API Key 格式不正确")
                print("  3. API Key 权限不足")
                print(f"\n错误详情: {response.text[:500]}")
                return False
            elif response.status_code == 429:
                print("\n⚠️  请求过于频繁 (429)，请稍后再试")
                return False
            else:
                print(f"\n❌ API 请求失败 ({response.status_code})")
                print(f"   错误: {response.text[:500]}")
                return False
                
    except httpx.TimeoutException:
        print("\n❌ 请求超时，请检查网络连接")
        return False
    except httpx.ConnectError:
        print("\n❌ 无法连接到 API 服务器，请检查网络")
        return False
    except Exception as e:
        print(f"\n❌ 发生异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test())
    print("\n" + "=" * 60)
    if result:
        print("✅ 测试通过：Kimi API 连接正常")
    else:
        print("❌ 测试失败：请检查 API Key 配置")
    print("=" * 60)
    sys.exit(0 if result else 1)
