"""会话管理模块测试"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from src.session_manager import SessionManager, SessionError
from agents import SQLiteSession


class TestSessionManager:
    """测试会话管理器"""
    
    def test_create_sqlite_session(self):
        """测试创建SQLite会话"""
        session_id = "test_session_123"
        
        session = SessionManager.create_session(
            session_id=session_id,
            storage_type="sqlite"
        )
        
        assert isinstance(session, SQLiteSession)
        assert session.session_id == session_id
    
    def test_create_redis_session_without_url(self):
        """测试创建Redis会话但未提供URL时抛出异常"""
        session_id = "test_session_123"
        
        with pytest.raises(SessionError) as exc_info:
            SessionManager.create_session(
                session_id=session_id,
                storage_type="redis",
                redis_url=None
            )
        
        assert "redis_url" in str(exc_info.value).lower()
    
    def test_create_redis_session_fallback_to_sqlite(self):
        """测试Redis连接失败时降级到SQLite"""
        session_id = "test_session_123"
        redis_url = "redis://localhost:6379/0"
        
        # 模拟RedisSession导入失败
        with patch('agents.extensions.memory.RedisSession') as mock_redis_class:
            mock_redis_class.from_url.side_effect = Exception("Connection failed")
            
            session = SessionManager.create_session(
                session_id=session_id,
                storage_type="redis",
                redis_url=redis_url
            )
            
            # 应该降级到SQLite
            assert isinstance(session, SQLiteSession)
    
    def test_create_session_invalid_storage_type(self):
        """测试使用无效的存储类型"""
        session_id = "test_session_123"
        
        with pytest.raises(SessionError):
            SessionManager.create_session(
                session_id=session_id,
                storage_type="invalid_type"
            )
    
    def test_session_manager_init(self):
        """测试SessionManager初始化"""
        mock_session = Mock()
        manager = SessionManager(mock_session)
        
        assert manager.session == mock_session
    
    @pytest.mark.asyncio
    async def test_get_items(self):
        """测试获取会话项目"""
        mock_session = Mock()
        mock_items = [{"role": "user", "content": "Hello"}]
        mock_session.get_items = AsyncMock(return_value=mock_items)
        
        manager = SessionManager(mock_session)
        items = await manager.get_items()
        
        assert items == mock_items
        mock_session.get_items.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_items_error(self):
        """测试获取会话项目失败时返回空列表"""
        mock_session = Mock()
        mock_session.get_items = AsyncMock(side_effect=Exception("Database error"))
        
        manager = SessionManager(mock_session)
        items = await manager.get_items()
        
        assert items == []
    
    @pytest.mark.asyncio
    async def test_add_items(self):
        """测试添加会话项目"""
        mock_session = Mock()
        mock_session.add_items = AsyncMock()
        manager = SessionManager(mock_session)
        
        items = [{"role": "user", "content": "Hello"}]
        await manager.add_items(items)
        
        mock_session.add_items.assert_called_once_with(items)
    
    @pytest.mark.asyncio
    async def test_add_items_error(self):
        """测试添加会话项目失败时抛出异常"""
        mock_session = Mock()
        mock_session.add_items = AsyncMock(side_effect=Exception("Database error"))
        
        manager = SessionManager(mock_session)
        items = [{"role": "user", "content": "Hello"}]
        
        with pytest.raises(SessionError):
            await manager.add_items(items)
    
    @pytest.mark.asyncio
    async def test_clear(self):
        """测试清空会话历史"""
        mock_session = Mock()
        mock_session.clear = AsyncMock()
        manager = SessionManager(mock_session)
        
        await manager.clear()
        
        mock_session.clear.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_clear_error(self):
        """测试清空会话失败时抛出异常"""
        mock_session = Mock()
        mock_session.clear = AsyncMock(side_effect=Exception("Database error"))
        
        manager = SessionManager(mock_session)
        
        with pytest.raises(SessionError):
            await manager.clear()
    
    @pytest.mark.asyncio
    async def test_get_history_length(self):
        """测试获取会话历史长度"""
        mock_session = Mock()
        mock_items = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"}
        ]
        mock_session.get_items = AsyncMock(return_value=mock_items)
        
        manager = SessionManager(mock_session)
        length = await manager.get_history_length()
        
        assert length == 2
    
    @pytest.mark.asyncio
    async def test_get_history_length_error(self):
        """测试获取会话历史长度失败时返回0"""
        mock_session = Mock()
        mock_session.get_items = AsyncMock(side_effect=Exception("Database error"))
        
        manager = SessionManager(mock_session)
        length = await manager.get_history_length()
        
        assert length == 0
