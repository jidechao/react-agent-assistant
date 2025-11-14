"""WebSocket API 模块

该模块提供 WebSocket API 服务，支持前后端实时通信和流式响应。
"""

import json
import logging
import uuid
from typing import TYPE_CHECKING, Callable, Optional

import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed
from websockets.protocol import State

if TYPE_CHECKING:
    from .agent_core import ReactAgent
    from .session_manager import SessionManager

# 配置日志
logger = logging.getLogger(__name__)


class WebAPIError(Exception):
    """Web API 相关异常"""
    pass


class WebSocketHandler:
    """WebSocket 连接处理器
    
    该类负责处理 WebSocket 连接、消息路由和会话管理。
    """
    
    def __init__(
        self,
        agent_factory: Callable,
        session_manager_factory: Optional[Callable] = None,
        storage_type: str = "sqlite",
        redis_url: Optional[str] = None
    ):
        """初始化 WebSocket 处理器
        
        Args:
            agent_factory: 用于创建 ReactAgent 实例的工厂函数
            session_manager_factory: 用于创建 SessionManager 的工厂函数（可选，未使用）
            storage_type: 存储类型，"sqlite"或"redis"
            redis_url: Redis 连接 URL（可选）
        """
        self.agent_factory = agent_factory
        self.session_manager_factory = session_manager_factory
        self.storage_type = storage_type
        self.redis_url = redis_url
        # 存储每个 WebSocket 连接对应的会话 ID
        self.connection_sessions: dict[WebSocketServerProtocol, str] = {}
        # 存储每个会话对应的 Agent 实例
        self.session_agents: dict[str, "ReactAgent"] = {}
    
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """处理 WebSocket 连接
        
        Args:
            websocket: WebSocket 连接对象
            path: 连接路径
        """
        logger.info(f"新的 WebSocket 连接: {websocket.remote_address}, path: {path}")
        
        # 检查连接是否仍然打开（websockets 14.x 使用 state 属性）
        if websocket.state != State.OPEN:
            logger.warning(f"WebSocket 连接状态不是 OPEN: {websocket.remote_address}, state: {websocket.state}")
            return
        
        try:
            # 发送连接成功消息
            try:
                await self._send_message(websocket, {
                    "type": "connected",
                    "message": "WebSocket 连接成功"
                })
                logger.debug(f"已发送连接成功消息到 {websocket.remote_address}")
            except Exception as e:
                logger.error(f"发送连接成功消息失败: {e}", exc_info=True)
                # 如果发送失败，检查连接状态
                if websocket.state != State.OPEN:
                    logger.warning(f"连接在发送消息后关闭: {websocket.remote_address}, state: {websocket.state}")
                    return
                # 如果连接仍然打开，继续处理
            
            # 主消息循环 - 保持连接打开直到客户端关闭
            try:
                async for message in websocket:
                    try:
                        await self._handle_message(websocket, message)
                    except Exception as e:
                        logger.error(f"处理消息时出错: {e}", exc_info=True)
                        try:
                            await self._send_error(websocket, f"处理消息失败: {str(e)}")
                        except Exception as send_err:
                            logger.error(f"发送错误消息失败: {send_err}")
            except ConnectionClosed:
                # 正常的连接关闭
                logger.info(f"WebSocket 连接正常关闭: {websocket.remote_address}")
            except Exception as e:
                logger.error(f"WebSocket 消息循环错误: {e}", exc_info=True)
                # 不重新抛出异常，让连接正常关闭
        
        except ConnectionClosed:
            logger.info(f"WebSocket 连接关闭: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"WebSocket 连接错误: {e}", exc_info=True)
        finally:
            # 清理连接相关的资源
            try:
                await self._cleanup_connection(websocket)
            except Exception as e:
                logger.error(f"清理连接资源时出错: {e}", exc_info=True)
    
    async def _handle_message(self, websocket: WebSocketServerProtocol, message: str):
        """处理接收到的消息
        
        Args:
            websocket: WebSocket 连接对象
            message: 接收到的消息（JSON 字符串）
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "message":
                # 处理用户消息
                await self._handle_user_message(websocket, data)
            elif msg_type == "create_session":
                # 创建新会话
                await self._handle_create_session(websocket, data)
            elif msg_type == "switch_session":
                # 切换会话
                await self._handle_switch_session(websocket, data)
            elif msg_type == "delete_session":
                # 删除会话
                await self._handle_delete_session(websocket, data)
            elif msg_type == "list_sessions":
                # 列出所有会话
                await self._handle_list_sessions(websocket)
            elif msg_type == "load_history":
                # 加载会话历史记录
                await self._handle_load_history(websocket, data)
            else:
                await self._send_error(websocket, f"未知的消息类型: {msg_type}")
        
        except json.JSONDecodeError as e:
            await self._send_error(websocket, f"无效的 JSON 格式: {str(e)}")
        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)
            await self._send_error(websocket, f"处理消息失败: {str(e)}")
    
    async def _handle_user_message(self, websocket: WebSocketServerProtocol, data: dict):
        """处理用户消息
        
        Args:
            websocket: WebSocket 连接对象
            data: 消息数据
        """
        session_id = data.get("session_id")
        content = data.get("content", "")
        
        if not session_id:
            await self._send_error(websocket, "缺少 session_id")
            return
        
        if not content:
            await self._send_error(websocket, "消息内容不能为空")
            return
        
        # 获取或创建 Agent 实例
        agent = await self._get_or_create_agent(session_id)
        if not agent:
            await self._send_error(websocket, f"无法创建或获取会话: {session_id}")
            return
        
        # 记录连接与会话的映射
        self.connection_sessions[websocket] = session_id
        
        try:
            # 使用流式方法处理消息（包含工具调用事件）
            async for event in agent.run_with_stream_and_events(content):
                await self._send_message(websocket, event)
        
        except Exception as e:
            logger.error(f"处理用户消息失败: {e}", exc_info=True)
            await self._send_error(websocket, f"处理消息失败: {str(e)}")
    
    async def _handle_create_session(self, websocket: WebSocketServerProtocol, data: dict):
        """处理创建会话请求
        
        Args:
            websocket: WebSocket 连接对象
            data: 消息数据
        """
        session_id = data.get("session_id")
        
        # 如果没有提供 session_id，生成一个新的
        if not session_id:
            session_id = f"web_session_{uuid.uuid4().hex[:8]}"
        
        # 创建 Agent 实例
        agent = await self._get_or_create_agent(session_id)
        
        if agent:
            await self._send_message(websocket, {
                "type": "session_created",
                "session_id": session_id
            })
        else:
            await self._send_error(websocket, f"创建会话失败: {session_id}")
    
    async def _handle_switch_session(self, websocket: WebSocketServerProtocol, data: dict):
        """处理切换会话请求
        
        Args:
            websocket: WebSocket 连接对象
            data: 消息数据
        """
        session_id = data.get("session_id")
        
        if not session_id:
            await self._send_error(websocket, "缺少 session_id")
            return
        
        # 获取或创建 Agent 实例
        agent = await self._get_or_create_agent(session_id)
        
        if agent:
            self.connection_sessions[websocket] = session_id
            await self._send_message(websocket, {
                "type": "session_switched",
                "session_id": session_id
            })
        else:
            await self._send_error(websocket, f"切换会话失败: {session_id}")
    
    async def _handle_delete_session(self, websocket: WebSocketServerProtocol, data: dict):
        """处理删除会话请求
        
        Args:
            websocket: WebSocket 连接对象
            data: 消息数据
        """
        session_id = data.get("session_id")
        
        if not session_id:
            await self._send_error(websocket, "缺少 session_id")
            return
        
        try:
            # 导入 SessionManager
            from .session_manager import SessionManager
            
            # 删除会话
            await SessionManager.delete_session(
                session_id=session_id,
                storage_type=self.storage_type,
                redis_url=self.redis_url
            )
            
            # 清理缓存的 Agent 实例
            if session_id in self.session_agents:
                del self.session_agents[session_id]
            
            # 如果当前连接使用的是被删除的会话，清除映射
            if websocket in self.connection_sessions:
                if self.connection_sessions[websocket] == session_id:
                    del self.connection_sessions[websocket]
            
            await self._send_message(websocket, {
                "type": "session_deleted",
                "session_id": session_id
            })
        
        except Exception as e:
            logger.error(f"删除会话失败: {e}", exc_info=True)
            await self._send_error(websocket, f"删除会话失败: {str(e)}")
    
    async def _handle_list_sessions(self, websocket: WebSocketServerProtocol):
        """处理列出所有会话的请求
        
        Args:
            websocket: WebSocket 连接对象
        """
        try:
            from .session_manager import SessionManager
            
            sessions = await SessionManager.list_sessions(
                storage_type=self.storage_type,
                redis_url=self.redis_url
            )
            
            await self._send_message(websocket, {
                "type": "sessions_list",
                "sessions": sessions
            })
        
        except Exception as e:
            logger.error(f"列出会话失败: {e}", exc_info=True)
            await self._send_error(websocket, f"列出会话失败: {str(e)}")
    
    async def _handle_load_history(self, websocket: WebSocketServerProtocol, data: dict):
        """加载会话历史记录
        
        Args:
            websocket: WebSocket 连接对象
            data: 消息数据，包含 session_id
        """
        session_id = data.get("session_id")
        
        if not session_id:
            await self._send_error(websocket, "缺少 session_id")
            return
        
        try:
            # 创建临时会话以获取历史记录
            from .session_manager import SessionManager
            
            session = SessionManager.create_session(
                session_id=session_id,
                storage_type=self.storage_type,
                redis_url=self.redis_url
            )
            
            # 获取历史记录
            items = await session.get_items()
            
            logger.info(f"加载会话 {session_id} 的历史记录，共 {len(items)} 条原始记录")
            
            # 将历史记录转换为前端格式
            history_messages = []
            for idx, item in enumerate(items):
                try:
                    # 首先检查是否是字典格式（Session.get_items() 可能返回字典）
                    item_dict = item if isinstance(item, dict) else {}
                    if not item_dict and hasattr(item, '__dict__'):
                        # 尝试将对象转换为字典
                        item_dict = item.__dict__
                    elif not item_dict:
                        # 尝试通过属性访问
                        item_dict = {
                            'role': getattr(item, 'role', None),
                            'content': getattr(item, 'content', None),
                            'type': getattr(item, 'type', None),
                            'id': getattr(item, 'id', None),
                            'timestamp': getattr(item, 'timestamp', None),
                        }
                        # 检查是否有工具调用相关属性
                        if hasattr(item, 'name'):
                            item_dict['name'] = getattr(item, 'name', None)
                        if hasattr(item, 'arguments'):
                            item_dict['arguments'] = getattr(item, 'arguments', None)
                        if hasattr(item, 'output'):
                            item_dict['output'] = getattr(item, 'output', None)
                    
                    # 调试：记录消息类型和内容
                    item_type = item_dict.get('type', None)
                    logger.info(f"历史消息 {idx}: type={item_type}, role={item_dict.get('role')}, keys={list(item_dict.keys())}")
                    # 如果是字典格式，记录完整内容
                    if isinstance(item, dict):
                        logger.info(f"历史消息 {idx} 完整内容: {json.dumps(item, ensure_ascii=False, default=str)[:500]}")
                    elif hasattr(item, '__dict__'):
                        logger.info(f"历史消息 {idx} 对象属性: {list(item.__dict__.keys())}")
                    
                    # 检查消息类型
                    
                    # 处理工具调用消息
                    if item_type in ['function_call', 'tool_call', 'tool_call_item']:
                        tool_name = item_dict.get('name', 'unknown')
                        tool_args = item_dict.get('arguments', {})
                        
                        # 如果 arguments 是字符串，尝试解析为 JSON
                        if isinstance(tool_args, str):
                            try:
                                tool_args = json.loads(tool_args)
                            except:
                                tool_args = {}
                        
                        item_id = item_dict.get('id')
                        if not item_id:
                            import time
                            item_id = f"tool_call_{session_id}_{idx}_{int(time.time() * 1000)}"
                        
                        logger.info(f"识别到工具调用消息: {tool_name}, 参数: {tool_args}")
                        
                        history_messages.append({
                            "id": item_id,
                            "type": "tool_call",
                            "role": "assistant",
                            "content": f"调用工具: {tool_name}",
                            "toolName": tool_name,
                            "toolArgs": tool_args,
                            "status": "completed",  # 历史记录中的工具调用都是已完成的
                            "timestamp": item_dict.get('timestamp', idx * 1000)
                        })
                        continue
                    
                    # 处理工具输出消息
                    elif item_type in ['function_call_output', 'tool_output', 'tool_call_output_item']:
                        tool_name = item_dict.get('name', 'unknown')
                        tool_output = item_dict.get('output', None)
                        
                        item_id = item_dict.get('id')
                        if not item_id:
                            import time
                            item_id = f"tool_output_{session_id}_{idx}_{int(time.time() * 1000)}"
                        
                        logger.info(f"识别到工具输出消息: {tool_name}")
                        
                        history_messages.append({
                            "id": item_id,
                            "type": "tool_output",
                            "role": "assistant",
                            "content": "",  # 工具输出不需要文本内容
                            "toolName": tool_name,
                            "toolOutput": tool_output,
                            "status": "completed",
                            "timestamp": item_dict.get('timestamp', idx * 1000)
                        })
                        continue
                    
                    # 处理普通消息（用户或助手）
                    # Session的items通常是Message对象，需要转换为前端格式
                    if hasattr(item, 'role') and hasattr(item, 'content'):
                        # 处理 content 字段
                        content = item.content
                        if isinstance(content, list):
                            # 如果是列表，提取文本内容
                            content_str = '\n'.join([
                                part.get('text', '') if isinstance(part, dict) and 'text' in part else 
                                (str(part.get('content', '')) if isinstance(part, dict) and 'content' in part else str(part))
                                for part in content
                                if part  # 过滤空值
                            ])
                        elif isinstance(content, dict):
                            # 如果是字典，尝试提取 text 字段
                            if 'text' in content:
                                content_str = str(content['text'])
                            elif 'content' in content:
                                content_str = str(content['content'])
                            else:
                                # 尝试转换为 JSON 字符串
                                content_str = json.dumps(content, ensure_ascii=False)
                        elif not isinstance(content, str):
                            # 其他类型，转换为字符串
                            try:
                                content_str = json.dumps(content, ensure_ascii=False) if isinstance(content, (dict, list)) else str(content)
                            except:
                                content_str = str(content)
                        else:
                            content_str = content
                        
                        # 生成唯一 ID
                        item_id = getattr(item, 'id', None)
                        if not item_id:
                            import time
                            item_id = f"msg_{session_id}_{idx}_{int(time.time() * 1000)}_{hash(str(item)) % 10000}"
                        
                        # 确定消息类型
                        msg_type = 'user' if item.role == 'user' else 'assistant'
                        
                        history_messages.append({
                            "id": item_id,
                            "type": msg_type,
                            "role": item.role,
                            "content": content_str,
                            "timestamp": getattr(item, 'timestamp', None) or (idx * 1000)
                        })
                    elif isinstance(item, dict):
                        # 如果已经是字典格式，确保格式正确
                        # 再次检查是否是工具调用消息（字典格式）
                        item_type = item.get('type', None)
                        if item_type in ['function_call', 'tool_call', 'tool_call_item']:
                            tool_name = item.get('name', 'unknown')
                            tool_args = item.get('arguments', {})
                            
                            if isinstance(tool_args, str):
                                try:
                                    tool_args = json.loads(tool_args)
                                except:
                                    tool_args = {}
                            
                            item_id = item.get('id')
                            if not item_id:
                                import time
                                item_id = f"tool_call_{session_id}_{idx}_{int(time.time() * 1000)}"
                            
                            logger.info(f"识别到字典格式的工具调用消息: {tool_name}")
                            
                            history_messages.append({
                                "id": item_id,
                                "type": "tool_call",
                                "role": "assistant",
                                "content": f"调用工具: {tool_name}",
                                "toolName": tool_name,
                                "toolArgs": tool_args,
                                "status": "completed",
                                "timestamp": item.get('timestamp', idx * 1000)
                            })
                            continue
                        
                        elif item_type in ['function_call_output', 'tool_output', 'tool_call_output_item']:
                            tool_name = item.get('name', 'unknown')
                            tool_output = item.get('output', None)
                            
                            item_id = item.get('id')
                            if not item_id:
                                import time
                                item_id = f"tool_output_{session_id}_{idx}_{int(time.time() * 1000)}"
                            
                            logger.info(f"识别到字典格式的工具输出消息: {tool_name}")
                            
                            history_messages.append({
                                "id": item_id,
                                "type": "tool_output",
                                "role": "assistant",
                                "content": "",
                                "toolName": tool_name,
                                "toolOutput": tool_output,
                                "status": "completed",
                                "timestamp": item.get('timestamp', idx * 1000)
                            })
                            continue
                        
                        # 处理 content 字段
                        content = item.get('content', '')
                        if isinstance(content, list):
                            # 如果是列表，提取文本内容
                            content_str = '\n'.join([
                                part.get('text', '') if isinstance(part, dict) and 'text' in part else 
                                (str(part.get('content', '')) if isinstance(part, dict) and 'content' in part else str(part))
                                for part in content
                                if part  # 过滤空值
                            ])
                        elif isinstance(content, dict):
                            # 如果是字典，尝试提取 text 字段
                            if 'text' in content:
                                content_str = str(content['text'])
                            elif 'content' in content:
                                content_str = str(content['content'])
                            else:
                                # 尝试转换为 JSON 字符串
                                content_str = json.dumps(content, ensure_ascii=False)
                        elif not isinstance(content, str):
                            # 其他类型，转换为字符串
                            try:
                                content_str = json.dumps(content, ensure_ascii=False) if isinstance(content, (dict, list)) else str(content)
                            except:
                                content_str = str(content)
                        else:
                            content_str = content
                        
                        # 确保有唯一 ID
                        item_id = item.get('id')
                        if not item_id:
                            import time
                            item_id = f"msg_{session_id}_{idx}_{int(time.time() * 1000)}_{hash(str(item)) % 10000}"
                        
                        msg = {
                            "id": item_id,
                            "role": item.get('role', 'assistant'),
                            "content": content_str,
                            "timestamp": item.get('timestamp', idx * 1000)
                        }
                        history_messages.append(msg)
                    else:
                        # 未知格式，尝试转换
                        logger.warning(f"未知的消息格式: {type(item)}")
                        import time
                        item_id = f"msg_{session_id}_{idx}_{int(time.time() * 1000)}_{hash(str(item)) % 10000}"
                        history_messages.append({
                            "id": item_id,
                            "role": "assistant",
                            "content": str(item),
                            "timestamp": idx * 1000
                        })
                except Exception as e:
                    logger.error(f"转换消息格式失败: {e}", exc_info=True)
                    # 跳过无法转换的消息
                    continue
            
            # 发送历史记录
            await self._send_message(websocket, {
                "type": "history_loaded",
                "session_id": session_id,
                "messages": history_messages
            })
            
            logger.info(f"已加载会话 {session_id} 的历史记录，共 {len(history_messages)} 条")
            # 调试：记录所有消息类型
            message_types = {}
            for msg in history_messages:
                msg_type = msg.get('type', 'unknown')
                message_types[msg_type] = message_types.get(msg_type, 0) + 1
            logger.info(f"消息类型统计: {message_types}")
        
        except Exception as e:
            logger.error(f"加载历史记录失败: {e}", exc_info=True)
            await self._send_error(websocket, f"加载历史记录失败: {str(e)}")
    
    async def _get_or_create_agent(self, session_id: str) -> Optional["ReactAgent"]:
        """获取或创建 Agent 实例
        
        Args:
            session_id: 会话 ID
            
        Returns:
            ReactAgent 实例，如果创建失败则返回 None
        """
        # 如果已存在，直接返回
        if session_id in self.session_agents:
            return self.session_agents[session_id]
        
        try:
            # 创建会话
            from .session_manager import SessionManager
            
            session = SessionManager.create_session(
                session_id=session_id,
                storage_type=self.storage_type,
                redis_url=self.redis_url
            )
            
            # 使用工厂函数创建 Agent
            agent = self.agent_factory(session=session)
            
            # 缓存 Agent 实例
            self.session_agents[session_id] = agent
            
            return agent
        
        except Exception as e:
            logger.error(f"创建 Agent 失败: {e}", exc_info=True)
            return None
    
    async def _send_message(self, websocket: WebSocketServerProtocol, data: dict):
        """发送消息到客户端
        
        Args:
            websocket: WebSocket 连接对象
            data: 要发送的数据字典
        """
        try:
            message = json.dumps(data, ensure_ascii=False)
            await websocket.send(message)
        except Exception as e:
            logger.error(f"发送消息失败: {e}", exc_info=True)
    
    async def _send_error(self, websocket: WebSocketServerProtocol, error_message: str):
        """发送错误消息到客户端
        
        Args:
            websocket: WebSocket 连接对象
            error_message: 错误消息
        """
        await self._send_message(websocket, {
            "type": "error",
            "message": error_message
        })
    
    async def _cleanup_connection(self, websocket: WebSocketServerProtocol):
        """清理连接相关的资源
        
        Args:
            websocket: WebSocket 连接对象
        """
        # 移除连接与会话的映射
        if websocket in self.connection_sessions:
            del self.connection_sessions[websocket]
        
        logger.debug("连接资源已清理")

