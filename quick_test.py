"""快速测试脚本 - 避免MCP清理问题"""
import asyncio
from src.config import Config
from src.model_provider import CustomModelProvider
from src.session_manager import SessionManager

async def quick_test():
    """快速测试核心功能"""
    print("🚀 快速功能测试\n")
    
    tests_passed = 0
    tests_total = 5
    
    # 1. 配置测试
    try:
        env_config = Config.load_env_config()
        mcp_config = Config.load_mcp_config()
        print(f"✓ [1/{tests_total}] 配置加载成功")
        tests_passed += 1
    except Exception as e:
        print(f"✗ [1/{tests_total}] 配置加载失败: {e}")
    
    # 2. 模型提供者测试
    try:
        provider = CustomModelProvider(
            api_key=env_config.api_key,
            base_url=env_config.base_url,
            model_name=env_config.model_name
        )
        model = provider.get_model()
        print(f"✓ [2/{tests_total}] 模型提供者创建成功")
        tests_passed += 1
    except Exception as e:
        print(f"✗ [2/{tests_total}] 模型提供者失败: {e}")
    
    # 3. 会话管理测试
    try:
        session = SessionManager.create_session(
            session_id="quick_test",
            storage_type="sqlite"
        )
        print(f"✓ [3/{tests_total}] 会话管理正常")
        tests_passed += 1
    except Exception as e:
        print(f"✗ [3/{tests_total}] 会话管理失败: {e}")
    
    # 4. 会话操作测试
    try:
        manager = SessionManager(session)
        items = await manager.get_items()
        length = await manager.get_history_length()
        print(f"✓ [4/{tests_total}] 会话操作正常 (历史长度: {length})")
        tests_passed += 1
    except Exception as e:
        print(f"✗ [4/{tests_total}] 会话操作失败: {e}")
    
    # 5. 配置验证
    try:
        assert env_config.api_key, "API Key不能为空"
        assert env_config.base_url, "Base URL不能为空"
        assert env_config.model_name, "Model Name不能为空"
        print(f"✓ [5/{tests_total}] 配置验证通过")
        tests_passed += 1
    except Exception as e:
        print(f"✗ [5/{tests_total}] 配置验证失败: {e}")
    
    # 结果
    print(f"\n{'='*50}")
    print(f"测试结果: {tests_passed}/{tests_total} 通过")
    
    if tests_passed == tests_total:
        print("🎉 所有测试通过！系统就绪。")
        return True
    else:
        print(f"⚠️  {tests_total - tests_passed} 个测试失败")
        return False

if __name__ == "__main__":
    result = asyncio.run(quick_test())
    exit(0 if result else 1)
