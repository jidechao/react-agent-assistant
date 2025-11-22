"""配置管理模块

该模块负责加载和验证系统配置，包括环境变量和MCP配置。
"""

import json
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError


class EnvConfig(BaseModel):
    """环境变量配置数据模型"""
    
    api_key: str = Field(..., description="OpenAI API密钥")
    base_url: str = Field(..., description="OpenAI API基础URL")
    model_name: str = Field(..., description="模型名称")
    redis_url: str | None = Field(None, description="Redis连接URL（可选）")


class MCPServerConfig(BaseModel):
    """MCP服务器配置数据模型"""
    
    name: str = Field(..., description="服务器名称")
    protocol: Literal["stdio", "sse", "streamablehttp"] = Field(
        ..., description="协议类型"
    )
    command: str | None = Field(None, description="命令（stdio协议使用）")
    args: list[str] | None = Field(None, description="命令参数（stdio协议使用）")
    url: str | None = Field(None, description="服务器URL（sse和streamablehttp协议使用）")
    env: dict[str, str] | None = Field(None, description="环境变量（可选）")
    timeout: float | int | None = Field(None, description="超时时间（秒，仅SSE和StreamableHTTP协议支持）")


class MCPConfig(BaseModel):
    """MCP配置数据模型"""
    
    servers: list[MCPServerConfig] = Field(
        default_factory=list, description="MCP服务器列表"
    )


class ConfigError(Exception):
    """配置相关异常"""
    pass


class Config:
    """系统配置类"""
    
    @staticmethod
    def load_env_config(env_file: str = ".env") -> EnvConfig:
        """从.env文件加载环境变量配置
        
        Args:
            env_file: 环境变量文件路径，默认为".env"
            
        Returns:
            EnvConfig: 包含api_key, base_url, model_name和redis_url的配置对象
            
        Raises:
            ConfigError: 当必需的环境变量缺失或配置验证失败时
        """
        # 加载.env文件
        load_dotenv(env_file)
        
        # 读取环境变量
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        model_name = os.getenv("OPENAI_MODEL")
        redis_url = os.getenv("REDIS_URL")
        
        # 验证必需的环境变量
        missing_vars = []
        if not api_key:
            missing_vars.append("OPENAI_API_KEY")
        if not base_url:
            missing_vars.append("OPENAI_BASE_URL")
        if not model_name:
            missing_vars.append("OPENAI_MODEL")
        
        if missing_vars:
            raise ConfigError(
                f"缺失必需的环境变量: {', '.join(missing_vars)}。"
                f"请在{env_file}文件中设置这些变量。"
            )
        
        # 创建并验证配置对象
        try:
            config = EnvConfig(
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                redis_url=redis_url
            )
            return config
        except ValidationError as e:
            raise ConfigError(f"环境变量配置验证失败: {e}")
    
    @staticmethod
    def load_mcp_config(config_path: str = "mcp_config.json") -> MCPConfig:
        """从JSON文件加载MCP配置
        
        Args:
            config_path: MCP配置文件路径，默认为"mcp_config.json"
            
        Returns:
            MCPConfig: MCP服务器配置对象
            
        Note:
            如果文件不存在或格式错误，返回空的MCPConfig对象（包含空的servers列表）
        """
        config_file = Path(config_path)
        
        # 如果文件不存在，返回空配置
        if not config_file.exists():
            print(f"警告: MCP配置文件 {config_path} 不存在，使用空配置")
            return MCPConfig(servers=[])
        
        try:
            # 读取JSON文件
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 验证并创建配置对象
            config = MCPConfig(**data)
            return config
            
        except json.JSONDecodeError as e:
            print(f"警告: MCP配置文件 {config_path} 格式错误: {e}，使用空配置")
            return MCPConfig(servers=[])
        except ValidationError as e:
            print(f"警告: MCP配置验证失败: {e}，使用空配置")
            return MCPConfig(servers=[])
        except Exception as e:
            print(f"警告: 加载MCP配置时发生错误: {e}，使用空配置")
            return MCPConfig(servers=[])
