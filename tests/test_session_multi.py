"""多会话管理测试"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.session_manager import SessionManager, SessionError


class TestMultiSessionManagement:
    """测试多会话管理功能"""
    
    @pytest.mark.asyncio
    async def test_list_sqlite_sessions(self):
        """测试列出 SQLite 会话"""
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                ("session1",),
                ("session2",),
                ("session3",)
            ]
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            
            with patch('pathlib.Path.exists', return_value=True):
                sessions = await SessionManager._list_sqlite_sessions()
                
                assert len(sessions) == 3
                assert "session1" in sessions
                assert "session2" in sessions
                assert "session3" in sessions
    
    @pytest.mark.asyncio
    async def test_list_sqlite_sessions_no_database(self):
        """测试数据库不存在时返回空列表"""
        with patch('pathlib.Path.exists', return_value=False):
            sessions = await SessionManager._list_sqlite_sessions()
            assert sessions == []
    
    @pytest.mark.asyncio
    async def test_list_redis_sessions(self):
        """测试列出 Redis 会话"""
        mock_client = MagicMock()
        mock_client.keys.return_value = [
            b"agents:session:session1:items",
            b"agents:session:session2:items",
            b"agents:session:session1:meta",
        ]
        
        with patch('redis.from_url', return_value=mock_client):
            sessions = await SessionManager._list_redis_sessions("redis://localhost:6379/0")
            
            assert len(sessions) == 2
            assert "session1" in sessions
            assert "session2" in sessions
    
    @pytest.mark.asyncio
    async def test_list_redis_sessions_no_url(self):
        """测试未提供 Redis URL 时返回空列表"""
        sessions = await SessionManager._list_redis_sessions(None)
        assert sessions == []
    
    @pytest.mark.asyncio
    async def test_list_sessions_sqlite(self):
        """测试列出 SQLite 会话"""
        with patch.object(SessionManager, '_list_sqlite_sessions', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = ["session1", "session2"]
            
            sessions = await SessionManager.list_sessions(storage_type="sqlite")
            
            assert sessions == ["session1", "session2"]
            mock_list.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_sessions_redis(self):
        """测试列出 Redis 会话"""
        with patch.object(SessionManager, '_list_redis_sessions', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = ["session1"]
            
            sessions = await SessionManager.list_sessions(
                storage_type="redis",
                redis_url="redis://localhost:6379/0"
            )
            
            assert sessions == ["session1"]
            mock_list.assert_called_once_with("redis://localhost:6379/0")
    
    @pytest.mark.asyncio
    async def test_delete_session(self):
        """测试删除会话"""
        session_id = "test_session"
        
        mock_session = Mock()
        mock_session.clear = AsyncMock()
        
        with patch.object(SessionManager, 'create_session', return_value=mock_session) as mock_create:
            await SessionManager.delete_session(session_id, storage_type="sqlite")
            
            mock_create.assert_called_once_with(
                session_id=session_id,
                storage_type="sqlite",
                redis_url=None
            )
            mock_session.clear.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_session_error(self):
        """测试删除会话时出错"""
        session_id = "test_session"
        
        with patch.object(SessionManager, 'create_session', side_effect=Exception("Error")):
            with pytest.raises(SessionError):
                await SessionManager.delete_session(session_id, storage_type="sqlite")
    
    @pytest.mark.asyncio
    async def test_list_sessions_invalid_storage_type(self):
        """测试无效的存储类型"""
        with pytest.raises(ValueError):
            await SessionManager.list_sessions(storage_type="invalid")

