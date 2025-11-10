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
