"""Agent核心模块测试"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from src.agent_core import ReactAgent, REACT_INSTRUCTIONS
from src.model_provider import CustomModelProvider
from agents import Agent, Runner
from agents.mcp import MCPServer
from openai.types.responses import ResponseTextDeltaEvent


class TestReactAgent:
    """测试ReactAgent"""
    
    def test_init_without_session(self):
        """测试ReactAgent初始化（不使用会话）"""
        mock_provider = Mock(spec=CustomModelProvider)
        # 使用字符串模型名称而不是Mock对象
        mock_provider.get_model.return_value = "gpt-4"
        mock_servers = []
        
        agent = ReactAgent(
            model_provider=mock_provider,
            mcp_servers=mock_servers,
            session=None
        )
        
        assert agent.model_provider == mock_provider
        assert agent.mcp_servers == mock_servers
        assert agent.session is None
        assert agent.agent is not None
        assert isinstance(agent.agent, Agent)
    
    def test_init_with_session(self):
        """测试ReactAgent初始化（使用会话）"""
        mock_provider = Mock(spec=CustomModelProvider)
        mock_provider.get_model.return_value = "gpt-4"
        mock_servers = []
        mock_session = Mock()
        
        agent = ReactAgent(
            model_provider=mock_provider,
            mcp_servers=mock_servers,
            session=mock_session
        )
        
        assert agent.session == mock_session
    
    def test_init_with_mcp_servers(self):
        """测试ReactAgent初始化（使用MCP服务器）"""
        mock_provider = Mock(spec=CustomModelProvider)
        mock_provider.get_model.return_value = "gpt-4"
        
        mock_server1 = Mock(spec=MCPServer)
        mock_server2 = Mock(spec=MCPServer)
        mock_servers = [mock_server1, mock_server2]
        
        agent = ReactAgent(
            model_provider=mock_provider,
            mcp_servers=mock_servers,
            session=None
        )
        
        assert len(agent.mcp_servers) == 2
    
    def test_agent_instructions(self):
        """测试Agent指令包含ReACT关键词"""
        assert "观察" in REACT_INSTRUCTIONS or "Observe" in REACT_INSTRUCTIONS
        assert "思考" in REACT_INSTRUCTIONS or "Think" in REACT_INSTRUCTIONS
        assert "行动" in REACT_INSTRUCTIONS or "Act" in REACT_INSTRUCTIONS
        assert "记忆" in REACT_INSTRUCTIONS or "Memory" in REACT_INSTRUCTIONS
    
    @pytest.mark.asyncio
    async def test_run_success(self):
        """测试run方法成功执行"""
        mock_provider = Mock(spec=CustomModelProvider)
        mock_provider.get_model.return_value = "gpt-4"
        
        agent = ReactAgent(
            model_provider=mock_provider,
            mcp_servers=[],
            session=None
        )
        
        user_input = "Hello, how are you?"
        expected_output = "I'm doing well, thank you!"
        
        # 模拟Runner.run的返回值
        mock_result = Mock()
        mock_result.final_output = expected_output
        
        with patch.object(Runner, 'run', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            output = await agent.run(user_input)
            
            assert output == expected_output
            mock_run.assert_called_once()
            
            # 验证调用参数
            call_args = mock_run.call_args
            assert call_args.kwargs['input'] == user_input
            assert call_args.kwargs['starting_agent'] == agent.agent
    
    @pytest.mark.asyncio
    async def test_run_with_session(self):
        """测试run方法使用会话"""
        mock_provider = Mock(spec=CustomModelProvider)
        mock_provider.get_model.return_value = "gpt-4"
        mock_session = Mock()
        
        agent = ReactAgent(
            model_provider=mock_provider,
            mcp_servers=[],
            session=mock_session
        )
        
        user_input = "Hello"
        expected_output = "Hi there!"
        
        mock_result = Mock()
        mock_result.final_output = expected_output
        
        with patch.object(Runner, 'run', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            output = await agent.run(user_input)
            
            # 验证会话被传递
            call_args = mock_run.call_args
            assert call_args.kwargs['session'] == mock_session
    
    @pytest.mark.asyncio
    async def test_run_error(self):
        """测试run方法执行失败"""
        mock_provider = Mock(spec=CustomModelProvider)
        mock_provider.get_model.return_value = "gpt-4"
        
        agent = ReactAgent(
            model_provider=mock_provider,
            mcp_servers=[],
            session=None
        )
        
        user_input = "Hello"
        
        with patch.object(Runner, 'run', new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = Exception("API error")
            
            with pytest.raises(Exception) as exc_info:
                await agent.run(user_input)
            
            assert "API error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_run_with_stream_success(self):
        """测试run_with_stream方法成功执行"""
        mock_provider = Mock(spec=CustomModelProvider)
        mock_provider.get_model.return_value = "gpt-4"
        
        agent = ReactAgent(
            model_provider=mock_provider,
            mcp_servers=[],
            session=None
        )
        
        user_input = "Hello"
        
        # 创建模拟的流式事件
        mock_event1 = Mock()
        mock_event1.type = "raw_response_event"
        mock_delta1 = Mock(spec=ResponseTextDeltaEvent)
        mock_delta1.delta = "Hello"
        mock_event1.data = mock_delta1
        
        mock_event2 = Mock()
        mock_event2.type = "raw_response_event"
        mock_delta2 = Mock(spec=ResponseTextDeltaEvent)
        mock_delta2.delta = " world"
        mock_event2.data = mock_delta2
        
        mock_event3 = Mock()
        mock_event3.type = "other_event"
        mock_event3.data = Mock()
        
        # 创建模拟的结果对象
        mock_result = Mock()
        
        async def mock_stream_events():
            for event in [mock_event1, mock_event2, mock_event3]:
                yield event
        
        mock_result.stream_events = mock_stream_events
        
        with patch.object(Runner, 'run_streamed') as mock_run_streamed:
            mock_run_streamed.return_value = mock_result
            
            # 收集流式输出
            output_chunks = []
            async for chunk in agent.run_with_stream(user_input):
                output_chunks.append(chunk)
            
            # 验证输出
            assert output_chunks == ["Hello", " world"]
            mock_run_streamed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_with_stream_empty_delta(self):
        """测试run_with_stream方法处理空delta"""
        mock_provider = Mock(spec=CustomModelProvider)
        mock_provider.get_model.return_value = "gpt-4"
        
        agent = ReactAgent(
            model_provider=mock_provider,
            mcp_servers=[],
            session=None
        )
        
        user_input = "Hello"
        
        # 创建包含空delta的事件
        mock_event = Mock()
        mock_event.type = "raw_response_event"
        mock_delta = Mock(spec=ResponseTextDeltaEvent)
        mock_delta.delta = ""
        mock_event.data = mock_delta
        
        mock_result = Mock()
        
        async def mock_stream_events():
            yield mock_event
        
        mock_result.stream_events = mock_stream_events
        
        with patch.object(Runner, 'run_streamed') as mock_run_streamed:
            mock_run_streamed.return_value = mock_result
            
            # 收集流式输出
            output_chunks = []
            async for chunk in agent.run_with_stream(user_input):
                output_chunks.append(chunk)
            
            # 空delta不应该被yield
            assert output_chunks == []
    
    @pytest.mark.asyncio
    async def test_run_with_stream_error(self):
        """测试run_with_stream方法执行失败"""
        mock_provider = Mock(spec=CustomModelProvider)
        mock_provider.get_model.return_value = "gpt-4"
        
        agent = ReactAgent(
            model_provider=mock_provider,
            mcp_servers=[],
            session=None
        )
        
        user_input = "Hello"
        
        with patch.object(Runner, 'run_streamed') as mock_run_streamed:
            mock_run_streamed.side_effect = Exception("Streaming error")
            
            with pytest.raises(Exception) as exc_info:
                async for _ in agent.run_with_stream(user_input):
                    pass
            
            assert "Streaming error" in str(exc_info.value)
