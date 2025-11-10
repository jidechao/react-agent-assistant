"""模型提供者模块测试"""

import pytest
from unittest.mock import Mock, patch

from src.model_provider import CustomModelProvider
from agents import OpenAIChatCompletionsModel


class TestCustomModelProvider:
    """测试自定义模型提供者"""
    
    def test_init(self):
        """测试CustomModelProvider初始化"""
        api_key = "test_api_key"
        base_url = "https://api.openai.com/v1"
        model_name = "gpt-4"
        
        provider = CustomModelProvider(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name
        )
        
        assert provider.api_key == api_key
        assert provider.base_url == base_url
        assert provider.model_name == model_name
        assert provider.client is not None
    
    def test_get_model_default(self):
        """测试get_model方法使用默认模型名称"""
        api_key = "test_api_key"
        base_url = "https://api.openai.com/v1"
        model_name = "gpt-4"
        
        provider = CustomModelProvider(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name
        )
        
        model = provider.get_model()
        
        assert isinstance(model, OpenAIChatCompletionsModel)
        assert model.model == model_name
    
    def test_get_model_override(self):
        """测试get_model方法覆盖模型名称"""
        api_key = "test_api_key"
        base_url = "https://api.openai.com/v1"
        model_name = "gpt-4"
        override_model = "gpt-3.5-turbo"
        
        provider = CustomModelProvider(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name
        )
        
        model = provider.get_model(override_model)
        
        assert isinstance(model, OpenAIChatCompletionsModel)
        assert model.model == override_model
    
    def test_get_model_multiple_calls(self):
        """测试多次调用get_model方法"""
        api_key = "test_api_key"
        base_url = "https://api.openai.com/v1"
        model_name = "gpt-4"
        
        provider = CustomModelProvider(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name
        )
        
        model1 = provider.get_model()
        model2 = provider.get_model()
        
        assert isinstance(model1, OpenAIChatCompletionsModel)
        assert isinstance(model2, OpenAIChatCompletionsModel)
        assert model1.model == model2.model
