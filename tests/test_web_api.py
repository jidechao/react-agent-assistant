"""WebSocket API 模块测试"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.web_api import WebSocketHandler, WebAPIError


class TestWebSocketHandler:
    """测试 WebSocket 处理器"""
    
    @pytest.fixture
    def mock_agent_factory(self):
        """创建模拟的 Agent 工厂函数"""
        def factory(session=None):
            agent = Mock()
            agent.run_with_stream_and_events = AsyncMock()
            return agent
        return factory
    
    @pytest.fixture
    def handler(self, mock_agent_factory):
        """创建 WebSocket 处理器实例"""
        return WebSocketHandler(
            agent_factory=mock_agent_factory,
            session_manager_factory=None,
            storage_type="sqlite",
            redis_url=None
        )
    
    @pytest.fixture
    def mock_websocket(self):
        """创建模拟的 WebSocket 连接"""
        ws = Mock()
        ws.remote_address = ("127.0.0.1", 12345)
        ws.send = AsyncMock()
        ws.recv = AsyncMock()
        ws.close = AsyncMock()
        return ws
    
    @pytest.mark.asyncio
    async def test_handle_connection_sends_connected_message(self, handler, mock_websocket):
        """测试连接时发送连接成功消息"""
        mock_websocket.recv.side_effect = [StopAsyncIteration()]
        
        await handler.handle_connection(mock_websocket, "/")
        
        # 验证发送了连接成功消息
        assert mock_websocket.send.called
        call_args = mock_websocket.send.call_args_list[0][0][0]
        message = json.loads(call_args)
        assert message["type"] == "connected"
    
    @pytest.mark.asyncio
    async def test_handle_user_message(self, handler, mock_websocket, mock_agent_factory):
        """测试处理用户消息"""
        session_id = "test_session"
        content = "Hello"
        
        # 创建模拟的 Agent
        agent = mock_agent_factory()
        agent.run_with_stream_and_events.return_value = AsyncMock()
        async def mock_stream():
            yield {"type": "text_delta", "content": "Hi"}
            yield {"type": "complete"}
        agent.run_with_stream_and_events.return_value = mock_stream()
        
        handler.session_agents[session_id] = agent
        
        # 模拟接收消息
        message_data = {
            "type": "message",
            "session_id": session_id,
            "content": content
        }
        mock_websocket.recv.side_effect = [
            json.dumps(message_data),
            StopAsyncIteration()
        ]
        
        await handler.handle_connection(mock_websocket, "/")
        
        # 验证 Agent 被调用
        assert agent.run_with_stream_and_events.called
    
    @pytest.mark.asyncio
    async def test_handle_create_session(self, handler, mock_websocket, mock_agent_factory):
        """测试创建会话"""
        session_id = "new_session"
        
        # 模拟接收创建会话消息
        message_data = {
            "type": "create_session",
            "session_id": session_id
        }
        mock_websocket.recv.side_effect = [
            json.dumps(message_data),
            StopAsyncIteration()
        ]
        
        await handler.handle_connection(mock_websocket, "/")
        
        # 验证发送了会话创建消息
        send_calls = [call[0][0] for call in mock_websocket.send.call_args_list]
        session_created = False
        for call in send_calls:
            message = json.loads(call)
            if message.get("type") == "session_created" and message.get("session_id") == session_id:
                session_created = True
                break
        assert session_created
    
    @pytest.mark.asyncio
    async def test_handle_delete_session(self, handler, mock_websocket):
        """测试删除会话"""
        session_id = "test_session"
        
        # 模拟会话存在
        handler.session_agents[session_id] = Mock()
        
        # 模拟接收删除会话消息
        message_data = {
            "type": "delete_session",
            "session_id": session_id
        }
        mock_websocket.recv.side_effect = [
            json.dumps(message_data),
            StopAsyncIteration()
        ]
        
        with patch('src.web_api.SessionManager.delete_session', new_callable=AsyncMock) as mock_delete:
            await handler.handle_connection(mock_websocket, "/")
            
            # 验证删除方法被调用
            mock_delete.assert_called_once()
            
            # 验证会话从缓存中移除
            assert session_id not in handler.session_agents
    
    @pytest.mark.asyncio
    async def test_handle_list_sessions(self, handler, mock_websocket):
        """测试列出会话"""
        # 模拟接收列出会话消息
        message_data = {"type": "list_sessions"}
        mock_websocket.recv.side_effect = [
            json.dumps(message_data),
            StopAsyncIteration()
        ]
        
        with patch('src.web_api.SessionManager.list_sessions', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = ["session1", "session2"]
            
            await handler.handle_connection(mock_websocket, "/")
            
            # 验证发送了会话列表
            send_calls = [call[0][0] for call in mock_websocket.send.call_args_list]
            sessions_list_sent = False
            for call in send_calls:
                message = json.loads(call)
                if message.get("type") == "sessions_list":
                    sessions_list_sent = True
                    assert message.get("sessions") == ["session1", "session2"]
                    break
            assert sessions_list_sent
    
    @pytest.mark.asyncio
    async def test_handle_invalid_message(self, handler, mock_websocket):
        """测试处理无效消息"""
        # 模拟接收无效消息
        mock_websocket.recv.side_effect = [
            "invalid json",
            StopAsyncIteration()
        ]
        
        await handler.handle_connection(mock_websocket, "/")
        
        # 验证发送了错误消息
        send_calls = [call[0][0] for call in mock_websocket.send.call_args_list]
        error_sent = False
        for call in send_calls:
            message = json.loads(call)
            if message.get("type") == "error":
                error_sent = True
                break
        assert error_sent
    
    @pytest.mark.asyncio
    async def test_get_or_create_agent(self, handler, mock_agent_factory):
        """测试获取或创建 Agent"""
        session_id = "test_session"
        
        # 第一次调用应该创建新的 Agent
        agent1 = await handler._get_or_create_agent(session_id)
        assert agent1 is not None
        assert session_id in handler.session_agents
        
        # 第二次调用应该返回缓存的 Agent
        agent2 = await handler._get_or_create_agent(session_id)
        assert agent1 is agent2

