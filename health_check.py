"""系统健康检查脚本"""
import asyncio
from src.config import Config
from src.model_provider import CustomModelProvider
from src.session_manager import SessionManager

async def health_check():
    """执行系统健康检查"""
    print("🏥 系统健康检查")
    print("=" * 50)
    
    checks_passed = 0
    checks_total = 0
    
    # 检查1: 环境配置
    checks_total += 1
    try:
        env_config = Config.load_env_config()
        print("✓ 环境配置正常")
        checks_passed += 1
    except Exception as e:
        print(f"✗ 环境配置异常: {e}")
    
    # 检查2: MCP配置
    checks_total += 1
    try:
        mcp_config = Config.load_mcp_config()
        print(f"✓ MCP配置正常 ({len(mcp_config.servers)} 个服务器)")
        checks_passed += 1
    except Exception as e:
        print(f"✗ MCP配置异常: {e}")
    
    # 检查3: 模型提供者
    checks_total += 1
    try:
        provider = CustomModelProvider(
            api_key=env_config.api_key,
            base_url=env_config.base_url,
            model_name=env_config.model_name
        )
        provider.get_model()
        print("✓ 模型提供者正常")
        checks_passed += 1
    except Exception as e:
        print(f"✗ 模型提供者异常: {e}")
    
    # 检查4: 会话管理
    checks_total += 1
    try:
        session = SessionManager.create_session(
            session_id="health_check",
            storage_type="sqlite"
        )
        print("✓ 会话管理正常")
        checks_passed += 1
    except Exception as e:
        print(f"✗ 会话管理异常: {e}")
    
    print("=" * 50)
    print(f"健康检查结果: {checks_passed}/{checks_total} 通过")
    
    if checks_passed == checks_total:
        print("🎉 系统状态：健康")
        return True
    elif checks_passed >= checks_total * 0.75:
        print("⚠️  系统状态：部分功能异常")
        return True
    else:
        print("❌ 系统状态：严重异常")
        return False

if __name__ == "__main__":
    result = asyncio.run(health_check())
    exit(0 if result else 1)
