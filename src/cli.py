"""命令行交互界面模块

该模块提供交互式命令行界面，支持实时打字机效果的流式输出。
"""

import sys
import logging
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agent_core import ReactAgent

# 配置日志
logger = logging.getLogger(__name__)


class CLI:
    """命令行交互界面
    
    该类提供友好的命令行交互体验，支持：
    - 欢迎信息和使用说明
    - 用户输入提示
    - 流式打字机效果输出
    - 退出命令处理
    """
    
    def __init__(self, agent: "ReactAgent"):
        """初始化CLI
        
        Args:
            agent: ReactAgent实例
        """
        self.agent = agent
        logger.info("CLI初始化完成")
    
    def print_welcome(self):
        """打印欢迎信息和使用说明"""
        welcome_message = """
╔══════════════════════════════════════════════════════════════╗
║          欢迎使用 ReACT 智能助手                              ║
╚══════════════════════════════════════════════════════════════╝

这是一个基于 ReACT 推理模式的智能助手，能够：
  • 观察和理解您的问题
  • 思考并制定解决方案
  • 调用工具执行操作
  • 记住对话历史

使用说明：
  • 输入您的问题或请求，按回车发送
  • 输入 'exit' 或 'quit' 退出程序
  • 输入 'help' 查看帮助信息

让我们开始吧！
"""
        print(welcome_message)
    
    def print_user_input(self, text: str):
        """打印用户输入
        
        Args:
            text: 用户输入的文本
        """
        print(f"\n👤 您: {text}")
    
    def print_assistant_output(self, text: str, end: str = "\n"):
        """打印助手输出
        
        Args:
            text: 助手输出的文本
            end: 结束字符，默认为换行符
        """
        print(text, end=end, flush=True)
    
    async def run(self):
        """运行交互式命令行界面
        
        该方法实现主交互循环：
        1. 显示欢迎信息
        2. 循环读取用户输入
        3. 处理退出命令
        4. 调用Agent处理输入并流式输出结果
        5. 处理异常情况
        """
        # 显示欢迎信息
        self.print_welcome()
        
        try:
            while True:
                # 读取用户输入
                try:
                    user_input = input("\n👤 您: ").strip()
                except EOFError:
                    # 处理Ctrl+D
                    print("\n\n再见！")
                    break
                except KeyboardInterrupt:
                    # 处理Ctrl+C
                    print("\n\n再见！")
                    break
                
                # 检查空输入
                if not user_input:
                    continue
                
                # 处理退出命令
                if user_input.lower() in ["exit", "quit", "bye", "退出"]:
                    print("\n再见！感谢使用 ReACT 智能助手。")
                    break
                
                # 处理帮助命令
                if user_input.lower() in ["help", "帮助"]:
                    self._print_help()
                    continue
                
                # 调用Agent处理输入并流式输出
                try:
                    # 重置思考状态标记
                    if hasattr(self, '_thinking_started'):
                        delattr(self, '_thinking_started')
                    
                    print("\n🤖 助手: ", end="", flush=True)
                    
                    # 使用流式方法获取响应（包含所有事件：思考、工具调用、文本增量等）
                    async for event in self.agent.run_with_stream_and_events(user_input):
                        event_type = event.get("type")
                        
                        if event_type == "think":
                            # 显示思考过程（流式输出）
                            think_content = event.get("content", "")
                            if think_content:
                                # 如果是第一次显示思考，添加前缀
                                if not hasattr(self, '_thinking_started'):
                                    print("\n💭 思考: ", end="", flush=True)
                                    self._thinking_started = True
                                # 流式输出思考内容
                                print(think_content, end="", flush=True)
                        
                        elif event_type == "tool_call":
                            # 显示工具调用
                            # 如果之前有思考内容，先换行
                            if hasattr(self, '_thinking_started'):
                                print()  # 思考内容结束，换行
                                delattr(self, '_thinking_started')
                            
                            tool_name = event.get("tool_name", "unknown")
                            arguments = event.get("arguments", {})
                            print(f"\n🔧 调用工具: {tool_name}")
                            if arguments:
                                args_str = json.dumps(arguments, ensure_ascii=False, indent=2)
                                print(f"   参数: {args_str}")
                            print("🤖 助手: ", end="", flush=True)
                        
                        elif event_type == "tool_output":
                            # 显示工具输出
                            # 如果之前有思考内容，先换行
                            if hasattr(self, '_thinking_started'):
                                print()  # 思考内容结束，换行
                                delattr(self, '_thinking_started')
                            
                            tool_output = event.get("output", "")
                            if tool_output:
                                # 限制输出长度，避免过长
                                output_str = str(tool_output)
                                if len(output_str) > 500:
                                    output_str = output_str[:500] + "... (输出已截断)"
                                print(f"\n✅ 工具结果: {output_str}")
                            print("🤖 助手: ", end="", flush=True)
                        
                        elif event_type == "text_delta":
                            # 显示文本增量（最终答案）
                            # 如果之前有思考内容，先换行并重置标记
                            if hasattr(self, '_thinking_started'):
                                print()  # 思考内容结束，换行
                                delattr(self, '_thinking_started')
                            
                            text_delta = event.get("content", "")
                            if text_delta:
                                self.print_assistant_output(text_delta, end="")
                        
                        elif event_type == "complete":
                            # 完成事件，清理思考状态标记
                            if hasattr(self, '_thinking_started'):
                                delattr(self, '_thinking_started')
                            pass
                    
                    # 输出完成后换行
                    print()
                    
                except Exception as e:
                    logger.error(f"处理用户输入时出错: {e}")
                    print(f"\n❌ 抱歉，处理您的请求时出现错误: {e}")
                    print("请重试或输入 'exit' 退出。")
        
        except Exception as e:
            logger.error(f"CLI运行时出错: {e}")
            print(f"\n❌ 程序出现错误: {e}")
        
        finally:
            logger.info("CLI会话结束")
    
    def _print_help(self):
        """打印帮助信息"""
        help_message = """
╔══════════════════════════════════════════════════════════════╗
║                        帮助信息                               ║
╚══════════════════════════════════════════════════════════════╝

可用命令：
  • help / 帮助    - 显示此帮助信息
  • exit / quit   - 退出程序
  • bye / 退出    - 退出程序

使用技巧：
  • 直接输入您的问题或请求
  • 助手会使用可用的工具来帮助您
  • 助手会记住之前的对话内容
  • 您可以进行多轮对话来解决复杂问题

示例问题：
  • "今天天气怎么样？"
  • "帮我计算 123 * 456"
  • "读取某个文件的内容"
"""
        print(help_message)
