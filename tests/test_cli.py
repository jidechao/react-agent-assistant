"""CLI模块测试"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from io import StringIO

from src.cli import CLI
from src.agent_core import ReactAgent


class TestCLI:
    """测试命令行交互界面"""
    
    def test_init(self):
        """测试CLI初始化"""
        mock_agent = Mock(spec=ReactAgent)
        cli = CLI(mock_agent)
        
        assert cli.agent == mock_agent
    
    def test_print_welcome(self, capsys):
        """测试打印欢迎信息"""
        mock_agent = Mock(spec=ReactAgent)
        cli = CLI(mock_agent)
        
        cli.print_welcome()
        
        captured = capsys.readouterr()
        assert "ReACT" in captured.out or "智能助手" in captured.out
        assert "exit" in captured.out or "quit" in captured.out
    
    def test_print_user_input(self, capsys):
        """测试打印用户输入"""
        mock_agent = Mock(spec=ReactAgent)
        cli = CLI(mock_agent)
        
        user_text = "Hello, assistant!"
        cli.print_user_input(user_text)
        
        captured = capsys.readouterr()
        assert user_text in captured.out
        assert "您" in captured.out or "You" in captured.out
    
    def test_print_assistant_output(self, capsys):
        """测试打印助手输出"""
        mock_agent = Mock(spec=ReactAgent)
        cli = CLI(mock_agent)
        
        assistant_text = "Hello, user!"
        cli.print_assistant_output(assistant_text)
        
        captured = capsys.readouterr()
        assert assistant_text in captured.out
    
    def test_print_assistant_output_no_newline(self, capsys):
        """测试打印助手输出（不换行）"""
        mock_agent = Mock(spec=ReactAgent)
        cli = CLI(mock_agent)
        
        assistant_text = "Hello"
        cli.print_assistant_output(assistant_text, end="")
        
        captured = capsys.readouterr()
        assert assistant_text in captured.out
        assert not captured.out.endswith("\n")
    
    @pytest.mark.asyncio
    async def test_run_exit_command(self, capsys):
        """测试退出命令"""
        mock_agent = Mock(spec=ReactAgent)
        cli = CLI(mock_agent)
        
        # 模拟用户输入"exit"
        with patch('builtins.input', side_effect=["exit"]):
            await cli.run()
        
        captured = capsys.readouterr()
        assert "再见" in captured.out or "Goodbye" in captured.out
    
    @pytest.mark.asyncio
    async def test_run_quit_command(self, capsys):
        """测试quit命令"""
        mock_agent = Mock(spec=ReactAgent)
        cli = CLI(mock_agent)
        
        # 模拟用户输入"quit"
        with patch('builtins.input', side_effect=["quit"]):
            await cli.run()
        
        captured = capsys.readouterr()
        assert "再见" in captured.out or "Goodbye" in captured.out
    
    @pytest.mark.asyncio
    async def test_run_help_command(self, capsys):
        """测试help命令"""
        mock_agent = Mock(spec=ReactAgent)
        cli = CLI(mock_agent)
        
        # 模拟用户输入"help"然后"exit"
        with patch('builtins.input', side_effect=["help", "exit"]):
            await cli.run()
        
        captured = capsys.readouterr()
        assert "帮助" in captured.out or "help" in captured.out.lower()
    
    @pytest.mark.asyncio
    async def test_run_empty_input(self, capsys):
        """测试空输入"""
        mock_agent = Mock(spec=ReactAgent)
        cli = CLI(mock_agent)
        
        # 模拟用户输入空字符串然后"exit"
        with patch('builtins.input', side_effect=["", "exit"]):
            await cli.run()
        
        # 空输入应该被忽略，不会调用agent
        mock_agent.run_with_stream.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_run_with_user_input(self, capsys):
        """测试处理用户输入"""
        mock_agent = Mock(spec=ReactAgent)
        
        # 模拟流式响应
        async def mock_stream(user_input):
            yield "Hello"
            yield " "
            yield "world"
        
        mock_agent.run_with_stream = mock_stream
        
        cli = CLI(mock_agent)
        
        # 模拟用户输入"Hello"然后"exit"
        with patch('builtins.input', side_effect=["Hello", "exit"]):
            await cli.run()
        
        captured = capsys.readouterr()
        assert "Hello world" in captured.out
    
    @pytest.mark.asyncio
    async def test_run_agent_error(self, capsys):
        """测试Agent执行错误"""
        mock_agent = Mock(spec=ReactAgent)
        
        # 模拟Agent抛出异常
        async def mock_stream_error(user_input):
            raise Exception("API error")
            yield  # 这行不会执行，但需要让函数成为生成器
        
        mock_agent.run_with_stream = mock_stream_error
        
        cli = CLI(mock_agent)
        
        # 模拟用户输入然后"exit"
        with patch('builtins.input', side_effect=["Hello", "exit"]):
            await cli.run()
        
        captured = capsys.readouterr()
        assert "错误" in captured.out or "error" in captured.out.lower()
    
    @pytest.mark.asyncio
    async def test_run_keyboard_interrupt(self, capsys):
        """测试Ctrl+C中断"""
        mock_agent = Mock(spec=ReactAgent)
        cli = CLI(mock_agent)
        
        # 模拟KeyboardInterrupt
        with patch('builtins.input', side_effect=KeyboardInterrupt()):
            await cli.run()
        
        captured = capsys.readouterr()
        assert "再见" in captured.out or "Goodbye" in captured.out
    
    @pytest.mark.asyncio
    async def test_run_eof_error(self, capsys):
        """测试Ctrl+D (EOF)"""
        mock_agent = Mock(spec=ReactAgent)
        cli = CLI(mock_agent)
        
        # 模拟EOFError
        with patch('builtins.input', side_effect=EOFError()):
            await cli.run()
        
        captured = capsys.readouterr()
        assert "再见" in captured.out or "Goodbye" in captured.out
    
    def test_print_help(self, capsys):
        """测试打印帮助信息"""
        mock_agent = Mock(spec=ReactAgent)
        cli = CLI(mock_agent)
        
        cli._print_help()
        
        captured = capsys.readouterr()
        assert "帮助" in captured.out or "help" in captured.out.lower()
        assert "exit" in captured.out or "quit" in captured.out
