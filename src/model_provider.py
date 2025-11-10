"""模型提供者模块

该模块负责创建和管理自定义LLM连接。
"""

from openai import AsyncOpenAI
from agents import ModelProvider, OpenAIChatCompletionsModel


class CustomModelProvider(ModelProvider):
    """自定义模型提供者
    
    该类继承自ModelProvider，用于配置和管理与OpenAI兼容的API连接。
    支持自定义API密钥、基础URL和模型名称。
    """
    
    def __init__(self, api_key: str, base_url: str, model_name: str):
        """初始化模型提供者
        
        Args:
            api_key: OpenAI API密钥
            base_url: OpenAI API基础URL
            model_name: 模型名称（如gpt-4, gpt-3.5-turbo等）
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        
        # 创建异步OpenAI客户端
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
    
    def get_model(self, model_name: str | None = None) -> OpenAIChatCompletionsModel:
        """获取模型实例
        
        Args:
            model_name: 可选的模型名称，用于覆盖初始化时设置的模型名称
            
        Returns:
            OpenAIChatCompletionsModel: 配置好的模型实例
        """
        # 如果提供了model_name参数，使用它；否则使用初始化时的model_name
        effective_model_name = model_name if model_name is not None else self.model_name
        
        # 创建并返回OpenAIChatCompletionsModel实例
        return OpenAIChatCompletionsModel(
            model=effective_model_name,
            openai_client=self.client
        )
