"""Agent核心模块

该模块负责实现ReACT推理和工具调用逻辑。
"""

import logging
from typing import AsyncGenerator

from agents import Agent, Runner, set_tracing_disabled
from agents.mcp import MCPServer
from agents.memory import Session
from openai.types.responses import ResponseTextDeltaEvent

from .model_provider import CustomModelProvider

# 关闭tracing功能
set_tracing_disabled(disabled=True)

# 配置日志
logger = logging.getLogger(__name__)

# ReACT推理指令
REACT_INSTRUCTIONS = """你是一个智能助手，使用ReACT推理模式来解决问题。

ReACT模式包括：
1. 观察(Observe)：仔细分析用户的问题和当前可用的信息
2. 思考(Think)：推理需要采取什么行动来解决问题
3. 行动(Act)：使用可用的工具执行必要的操作
4. 记忆(Memory)：记住之前的对话和操作结果

工作流程：
- 首先观察用户的问题，理解他们真正需要什么
- 思考解决问题需要哪些步骤和工具
- 如果需要使用工具，调用相应的工具获取信息
- 基于工具返回的结果继续推理
- 重复这个过程直到问题得到完整解决
- 最后给出清晰、有帮助的回答

记住：
- 充分利用可用的工具
- 如果一次工具调用不够，可以进行多轮调用
- 保持回答的准确性和相关性
- 参考之前的对话历史来提供连贯的回答
"""


class ReactAgent:
    """ReACT模式的智能助手
    
    该类实现了基于ReACT推理模式的智能助手，支持多轮工具调用、
    对话历史管理和流式响应。
    """
    
    def __init__(
        self,
        model_provider: CustomModelProvider,
        mcp_servers: list[MCPServer],
        session: Session | None = None
    ):
        """初始化ReactAgent
        
        Args:
            model_provider: 模型提供者实例
            mcp_servers: MCP服务器列表
            session: 可选的会话实例，用于对话历史管理
        """
        self.model_provider = model_provider
        self.mcp_servers = mcp_servers
        self.session = session
        
        # 创建Agent实例
        self.agent = Agent(
            name="ReactAssistant",
            instructions=REACT_INSTRUCTIONS,
            model=model_provider.get_model(),
            mcp_servers=mcp_servers
        )
        
        logger.info(f"ReactAgent初始化完成，MCP服务器数量: {len(mcp_servers)}")

    async def run(self, user_input: str) -> str:
        """运行Agent处理用户输入
        
        该方法实现了ReACT推理逻辑：
        1. 观察：接收并分析用户输入
        2. 思考：Agent推理需要采取的行动
        3. 行动：调用必要的工具
        4. 记忆：通过会话管理保存对话历史
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            str: Agent的最终输出
            
        Raises:
            Exception: 当Agent执行失败时
        """
        try:
            logger.debug(f"开始处理用户输入: {user_input[:50]}...")
            
            # 使用Runner.run执行Agent
            result = await Runner.run(
                starting_agent=self.agent,
                input=user_input,
                session=self.session
            )
            
            # 提取最终输出
            final_output = str(result.final_output)
            
            logger.debug(f"Agent执行完成，输出长度: {len(final_output)}")
            return final_output
            
        except Exception as e:
            logger.error(f"Agent执行失败: {e}")
            raise

    async def run_with_stream(self, user_input: str) -> AsyncGenerator[str, None]:
        """以流式方式运行Agent
        
        该方法支持流式输出，实时返回Agent生成的文本增量。
        适用于需要实时显示生成内容的场景，如命令行交互界面。
        
        Args:
            user_input: 用户输入文本
            
        Yields:
            str: 文本增量
            
        Raises:
            Exception: 当Agent执行失败时
        """
        try:
            logger.debug(f"开始流式处理用户输入: {user_input[:50]}...")
            
            # 使用Runner.run_streamed进行流式执行
            result = Runner.run_streamed(
                starting_agent=self.agent,
                input=user_input,
                session=self.session
            )
            
            # 处理流式事件
            async for event in result.stream_events():
                # 只处理ResponseTextDeltaEvent事件
                if event.type == "raw_response_event" and isinstance(
                    event.data, ResponseTextDeltaEvent
                ):
                    # yield文本增量
                    if event.data.delta:
                        yield event.data.delta
            
            logger.debug("流式处理完成")
            
        except Exception as e:
            logger.error(f"流式Agent执行失败: {e}")
            raise
    
    async def run_with_stream_and_events(
        self, 
        user_input: str
    ) -> AsyncGenerator[dict, None]:
        """以流式方式运行Agent并捕获所有事件（包括工具调用）
        
        该方法支持流式输出和工具调用事件捕获，适用于需要完整事件信息的场景，
        如 Web 界面需要显示工具调用和输出。
        
        Args:
            user_input: 用户输入文本
            
        Yields:
            dict: 事件字典，包含 type 和 data 字段
                - type: 事件类型 ("text_delta", "tool_call", "tool_output", "complete")
                - data: 事件数据
                
        Raises:
            Exception: 当Agent执行失败时
        """
        try:
            logger.debug(f"开始流式处理用户输入（包含事件）: {user_input[:50]}...")
            
            # 使用Runner.run_streamed进行流式执行
            result = Runner.run_streamed(
                starting_agent=self.agent,
                input=user_input,
                session=self.session
            )
            
            # 处理流式事件
            current_text_buffer = ""  # 用于累积文本，检测思考阶段
            last_event_was_tool_call = False  # 跟踪上一个事件是否是工具调用
            has_sent_think = False  # 跟踪是否已经发送过think消息（避免重复）
            is_after_tool_output = False  # 跟踪是否在工具输出之后（此时文本应该是最终答案）
            is_thinking_phase = False  # 跟踪是否在思考阶段（工具调用之前）
            has_called_tool = False  # 跟踪是否调用过工具（用于判断是否应该发送最终答案）
            think_was_sent = False  # 跟踪是否实际发送过think事件（用于避免重复显示）
            
            async for event in result.stream_events():
                # 记录所有事件类型以便调试
                logger.debug(f"收到事件: type={event.type}, is_after_tool_output={is_after_tool_output}, current_buffer_len={len(current_text_buffer)}")
                
                # 处理文本增量事件
                if event.type == "raw_response_event" and isinstance(
                    event.data, ResponseTextDeltaEvent
                ):
                    if event.data.delta:
                        current_text_buffer += event.data.delta
                        
                        # 如果已经在工具输出之后，文本增量应该作为最终答案的一部分立即流式发送
                        if is_after_tool_output:
                            yield {
                                "type": "text_delta",
                                "content": event.data.delta
                            }
                        # 如果还没有调用过工具，说明在思考阶段，也应该流式输出
                        elif not has_sent_think:
                            # 流式输出思考内容
                            yield {
                                "type": "think",
                                "content": event.data.delta
                            }
                            is_thinking_phase = True
                            think_was_sent = True  # 标记已发送过think事件
                            # 注意：这里不设置 has_sent_think，因为思考内容可能持续多个增量
                            # has_sent_think 会在工具调用时设置
                            # 注意：current_text_buffer 继续累积，用于最后的判断
                            # 但最后如果 think_was_sent 为 True，不会发送 text_delta
                        # 否则累积起来（这种情况应该很少，因为工具调用后应该立即设置 is_after_tool_output）
                        last_event_was_tool_call = False
                
                # 处理 run_item_stream_event - 这是 agents SDK 中工具调用和输出的主要事件类型
                elif event.type == "run_item_stream_event":
                    item = event.item
                    item_type = getattr(item, "type", None)
                    
                    # 处理工具调用
                    if item_type == "tool_call_item":
                        # 在工具调用前，如果有累积的文本且还没有发送过think，说明是第一次工具调用
                        # 由于思考内容已经在流式输出中发送了，这里只需要标记
                        if not has_sent_think:
                            has_sent_think = True
                            is_thinking_phase = False
                        
                        # 标记已调用过工具
                        has_called_tool = True
                        
                        # 清空文本缓冲区
                        current_text_buffer = ""
                        last_event_was_tool_call = True
                        is_after_tool_output = False
                        
                        # 获取工具名称和参数
                        # ToolCallItem 有一个 raw_item 属性，包含 ResponseFunctionToolCall 对象
                        tool_name = None
                        tool_args = {}
                        
                        # 首先尝试从 raw_item 获取
                        if hasattr(item, "raw_item") and item.raw_item:
                            raw_item = item.raw_item
                            try:
                                tool_name = getattr(raw_item, "name", None)
                                if not tool_name:
                                    tool_name = getattr(raw_item, "tool_name", None) or getattr(raw_item, "function_name", None)
                            except Exception as e:
                                logger.error(f"获取工具名称失败: {e}", exc_info=True)
                                tool_name = None
                            
                            if not tool_name:
                                logger.warning(f"无法从 raw_item 获取工具名称")
                            
                            # 获取工具参数
                            try:
                                tool_args_str = getattr(raw_item, "arguments", None)
                                if tool_args_str:
                                    if isinstance(tool_args_str, str):
                                        try:
                                            import json
                                            tool_args = json.loads(tool_args_str)
                                        except Exception as e:
                                            logger.error(f"解析参数 JSON 失败: {e}")
                                            tool_args = {}
                                    else:
                                        tool_args = tool_args_str
                            except Exception as e:
                                logger.error(f"获取工具参数失败: {e}")
                                tool_args = {}
                        
                        # 如果从 raw_item 没有获取到，尝试其他方式
                        if not tool_name:
                            if hasattr(item, "name") and item.name:
                                tool_name = item.name
                            elif hasattr(item, "tool_name") and item.tool_name:
                                tool_name = item.tool_name
                            elif hasattr(item, "function") and hasattr(item.function, "name"):
                                tool_name = item.function.name
                            elif isinstance(item, dict):
                                tool_name = item.get("name") or item.get("tool_name") or item.get("function", {}).get("name")
                        
                        if not tool_args:
                            if hasattr(item, "arguments") and item.arguments:
                                tool_args = item.arguments
                            elif hasattr(item, "args") and item.args:
                                tool_args = item.args
                            elif hasattr(item, "function") and hasattr(item.function, "arguments"):
                                tool_args = item.function.arguments
                            elif isinstance(item, dict):
                                tool_args = item.get("arguments") or item.get("args") or item.get("function", {}).get("arguments", {})
                            
                            # 如果 arguments 是字符串，尝试解析为 JSON
                            if isinstance(tool_args, str):
                                try:
                                    import json
                                    tool_args = json.loads(tool_args)
                                except:
                                    tool_args = {}
                        
                        if not tool_name:
                            logger.warning(f"无法获取工具名称，item 类型: {type(item)}")
                            tool_name = "unknown"
                        
                        # 尝试获取服务器名称（从工具名称中提取或从上下文获取）
                        # 工具名称格式可能是 "server_name:tool_name" 或只是 "tool_name"
                        server_name = None
                        if ":" in tool_name:
                            parts = tool_name.split(":", 1)
                            server_name = parts[0]
                            tool_name = parts[1]
                        else:
                            # 尝试从 MCP 服务器配置中获取服务器名称
                            # 这里我们需要找到对应的 MCP 服务器
                            for mcp_server in self.mcp_servers:
                                try:
                                    # 检查工具是否属于这个服务器
                                    tools = mcp_server.list_tools() if hasattr(mcp_server, 'list_tools') else []
                                    if any(t.get('name') == tool_name for t in tools):
                                        server_name = getattr(mcp_server, 'name', None) or str(mcp_server)
                                        break
                                except:
                                    pass
                        
                        # 格式化工具名称：服务器名:工具名
                        formatted_tool_name = f"{server_name}:{tool_name}" if server_name else tool_name
                        
                        yield {
                            "type": "tool_call",
                            "tool_name": formatted_tool_name,
                            "arguments": tool_args
                        }
                    
                    # 处理工具输出
                    elif item_type == "tool_call_output_item":
                        last_event_was_tool_call = False
                        is_after_tool_output = True  # 标记工具输出已完成，后续文本是最终答案
                        
                        # 获取工具名称和输出
                        # ToolCallOutputItem 可能也有 raw_item 属性
                        tool_name = None
                        tool_output = None
                        
                        # 首先尝试从 raw_item 获取
                        if hasattr(item, "raw_item") and item.raw_item:
                            raw_item = item.raw_item
                            
                            # 尝试获取工具名称
                            try:
                                tool_name = getattr(raw_item, "name", None)
                                if not tool_name:
                                    tool_name = getattr(raw_item, "tool_name", None) or getattr(raw_item, "function_name", None) or getattr(raw_item, "tool_call_id", None)
                            except Exception as e:
                                logger.error(f"获取工具名称失败: {e}", exc_info=True)
                                tool_name = None
                            
                            # 尝试获取工具输出
                            try:
                                if hasattr(raw_item, "output") and raw_item.output is not None:
                                    tool_output = raw_item.output
                                elif hasattr(raw_item, "result") and raw_item.result is not None:
                                    tool_output = raw_item.result
                                elif hasattr(raw_item, "content") and raw_item.content is not None:
                                    tool_output = raw_item.content
                            except Exception as e:
                                logger.error(f"获取工具输出失败: {e}", exc_info=True)
                                tool_output = None
                        
                        # 如果从 raw_item 没有获取到，尝试其他方式
                        if not tool_name:
                            if hasattr(item, "name") and item.name:
                                tool_name = item.name
                            elif hasattr(item, "tool_name") and item.tool_name:
                                tool_name = item.tool_name
                            elif hasattr(item, "function") and hasattr(item.function, "name"):
                                tool_name = item.function.name
                            elif isinstance(item, dict):
                                tool_name = item.get("name") or item.get("tool_name") or item.get("function", {}).get("name")
                        
                        if not tool_output:
                            if hasattr(item, "output") and item.output is not None:
                                tool_output = item.output
                            elif hasattr(item, "result") and item.result is not None:
                                tool_output = item.result
                            elif isinstance(item, dict):
                                tool_output = item.get("output") or item.get("result")
                        
                        if not tool_name:
                            logger.warning(f"无法获取工具输出名称，item 类型: {type(item)}")
                            tool_name = "unknown"
                        
                        # 尝试获取服务器名称（与工具调用保持一致）
                        server_name = None
                        if ":" in tool_name:
                            parts = tool_name.split(":", 1)
                            server_name = parts[0]
                            tool_name = parts[1]
                        else:
                            # 尝试从 MCP 服务器配置中获取服务器名称
                            for mcp_server in self.mcp_servers:
                                try:
                                    tools = mcp_server.list_tools() if hasattr(mcp_server, 'list_tools') else []
                                    if any(t.get('name') == tool_name for t in tools):
                                        server_name = getattr(mcp_server, 'name', None) or str(mcp_server)
                                        break
                                except:
                                    pass
                        
                        # 工具输出消息的 tool_name 固定为 "工具调用结果"
                        yield {
                            "type": "tool_output",
                            "tool_name": "工具调用结果",
                            "output": tool_output
                        }
                
                # 处理其他可能的事件类型（向后兼容，但主要应该使用 run_item_stream_event）
                else:
                    # 检查是否有其他方式可以识别工具调用
                    if hasattr(event, 'data') and event.data:
                        logger.debug(f"事件类型: {event.type}, 事件数据: {type(event.data)}")
                        if hasattr(event.data, '__dict__'):
                            logger.debug(f"事件数据属性: {list(event.data.__dict__.keys())[:10]}")
                    logger.debug(f"未处理的事件类型: {event.type}")
            
            # 发送完成事件
            # 如果有剩余的文本缓冲区内容，确保它被作为最终答案处理
            # 逻辑说明：
            # 1. 在工具输出之后（is_after_tool_output）- 文本增量已经在流式过程中作为text_delta发送了，
            #    不应该再发送current_text_buffer中的内容，避免重复
            # 2. 没有发送过think事件且没有调用过工具 - 这是直接回答（没有思考过程），需要发送text_delta
            # 3. 发送过think事件但没有调用过工具 - 思考内容已经作为think事件流式发送了，
            #    不应该再发送text_delta，避免重复显示
            #    注意：CLI端会正常显示think事件，不需要text_delta；Web端也会正常显示think事件
            if current_text_buffer.strip():
                if is_after_tool_output:
                    # 工具输出后的文本增量已经在流式过程中作为text_delta发送了
                    # current_text_buffer中的内容都是已经发送过的，不应该再发送，避免重复
                    pass
                elif not think_was_sent and not has_called_tool:
                    # 没有思考过程，直接回答，需要发送text_delta
                    yield {
                        "type": "text_delta",
                        "content": current_text_buffer
                    }
                # 如果发送过think但没有调用工具，不发送text_delta，避免重复
                # CLI端已经通过think事件显示了内容，不需要text_delta
            yield {"type": "complete"}
            
        except Exception as e:
            logger.error(f"流式Agent执行失败: {e}")
            raise