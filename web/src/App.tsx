import { useState, useEffect, useCallback } from 'react';
import { wsService } from './services/websocket';
import { Message, Session } from './types';
import SessionList from './components/SessionList';
import ChatWindow from './components/ChatWindow';
import './App.css';

function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Record<string, Message[]>>({});
  const [isConnected, setIsConnected] = useState(false);

  // 加载会话历史记录
  const loadHistory = useCallback((sessionId: string) => {
    wsService.send({
      type: 'load_history',
      session_id: sessionId,
    });
  }, []);

  // 创建默认会话
  const createDefaultSession = useCallback(() => {
    const defaultSessionId = 'default_session';
    const defaultSession: Session = {
      id: defaultSessionId,
      name: '默认会话',
      createdAt: Date.now(),
    };

    setSessions([defaultSession]);
    setCurrentSessionId(defaultSessionId);
    setMessages({ [defaultSessionId]: [] });

    // 通知服务器创建会话
    wsService.send({
      type: 'create_session',
      session_id: defaultSessionId,
    });
    
    // 加载默认会话的历史记录
    loadHistory(defaultSessionId);
  }, [loadHistory]);

  // 加载会话列表
  const loadSessions = useCallback(() => {
    wsService.send({ type: 'list_sessions' });

    wsService.onMessage('sessions_list', (data: { sessions: string[] }) => {
      const sessionList: Session[] = data.sessions.map((id, index) => ({
        id,
        name: `会话 ${index + 1}`,
        createdAt: Date.now(),
      }));

      setSessions(prev => {
        // 合并现有会话和新加载的会话
        const existingIds = new Set(prev.map(s => s.id));
        const newSessions = sessionList.filter(s => !existingIds.has(s.id));
        return [...prev, ...newSessions];
      });
    });
  }, []);

  // 初始化 WebSocket 连接
  useEffect(() => {
    wsService.connect();

    const unsubscribeConnect = wsService.onConnect(() => {
      setIsConnected(true);
      
      // 注册历史记录加载处理器（必须在 createDefaultSession 之前注册）
      wsService.onMessage('history_loaded', (data: { session_id: string; messages: any[] }) => {
        const { session_id, messages } = data;
        
        // 将后端消息格式转换为前端格式
        const formattedMessages: Message[] = messages.map((msg, index) => {
          // 处理 content 字段，确保是字符串
          let contentStr = '';
          if (typeof msg.content === 'string') {
            // 尝试解析 JSON 字符串
            try {
              const parsed = JSON.parse(msg.content);
              if (Array.isArray(parsed)) {
                // 如果是数组，提取 text 字段
                contentStr = parsed
                  .map((item: any) => {
                    if (typeof item === 'object' && item !== null) {
                      return item.text || item.content || JSON.stringify(item);
                    }
                    return String(item);
                  })
                  .filter((s: string) => s)
                  .join('\n');
              } else if (typeof parsed === 'object' && parsed !== null) {
                // 如果是对象，提取 text 字段
                contentStr = parsed.text || parsed.content || JSON.stringify(parsed);
              } else {
                contentStr = msg.content;
              }
            } catch {
              // 不是 JSON，直接使用
              contentStr = msg.content;
            }
          } else if (typeof msg.content === 'object' && msg.content !== null) {
            // 如果 content 是对象，尝试提取 text 字段
            if (Array.isArray(msg.content)) {
              contentStr = msg.content
                .map((item: any) => {
                  if (typeof item === 'object' && item !== null) {
                    return item.text || item.content || JSON.stringify(item);
                  }
                  return String(item);
                })
                .filter((s: string) => s)
                .join('\n');
            } else if ('text' in msg.content) {
              contentStr = String(msg.content.text);
            } else if ('content' in msg.content) {
              contentStr = String(msg.content.content);
            } else {
              contentStr = JSON.stringify(msg.content);
            }
          } else {
            contentStr = String(msg.content || '');
          }
          
          // 确保消息 ID 唯一（检查无效的 ID）
          const uniqueId = (msg.id && msg.id !== '__fake_id__' && msg.id !== 'undefined' && msg.id !== 'null')
            ? msg.id 
            : `msg_${session_id}_${index}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
          
          // 处理不同的消息格式
          // 首先检查是否是工具调用或工具输出消息（优先检查 type 字段）
          const msgType = msg.type || (msg.role === 'user' ? 'user' : msg.role === 'assistant' ? 'assistant' : 'assistant');
          
          if (msgType === 'tool_call' || msgType === 'tool_output' || msgType === 'think') {
            return {
              id: uniqueId,
              type: msgType,
              content: contentStr,
              timestamp: msg.timestamp || Date.now() - (messages.length - index) * 1000,
              toolName: msg.toolName,
              toolArgs: msg.toolArgs,
              toolOutput: msg.toolOutput,
              status: msg.status || 'completed',
            };
          } else if (msg.role === 'user') {
            return {
              id: uniqueId,
              type: 'user',
              content: contentStr,
              timestamp: msg.timestamp || Date.now() - (messages.length - index) * 1000,
            };
          } else if (msg.role === 'assistant') {
            return {
              id: uniqueId,
              type: 'assistant',
              content: contentStr,
              timestamp: msg.timestamp || Date.now() - (messages.length - index) * 1000,
            };
          } else {
            // 其他类型的消息（工具调用等）
            return {
              id: uniqueId,
              type: msg.type || 'assistant',
              content: contentStr,
              timestamp: msg.timestamp || Date.now() - (messages.length - index) * 1000,
              toolName: msg.toolName,
              toolArgs: msg.toolArgs,
              toolOutput: msg.toolOutput,
              status: msg.status,
            };
          }
        });
        
        // 更新消息列表
        // 确保所有消息都有有效的 ID，并去重
        const messagesWithValidIds = formattedMessages
          .map((msg, idx) => {
            // 确保 ID 有效
            const validId = (msg.id && 
                            msg.id !== '__fake_id__' && 
                            msg.id !== 'undefined' && 
                            msg.id !== 'null' &&
                            typeof msg.id === 'string' &&
                            msg.id.trim() !== '')
              ? msg.id 
              : `msg_${session_id}_${idx}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            
            return {
              ...msg,
              id: validId
            };
          })
          // 去重：基于 ID 去重，保留第一个
          .filter((msg, idx, arr) => {
            const firstIndex = arr.findIndex(m => m.id === msg.id);
            return firstIndex === idx;
          });
        
        setMessages(prev => ({
          ...prev,
          [session_id]: messagesWithValidIds,
        }));
      });
      
      // 连接成功后，创建默认会话并获取会话列表
      createDefaultSession();
      loadSessions();
    });

    const unsubscribeDisconnect = wsService.onDisconnect(() => {
      setIsConnected(false);
    });

    return () => {
      unsubscribeConnect();
      unsubscribeDisconnect();
      wsService.disconnect();
    };
  }, [createDefaultSession, loadSessions]);

  // 创建新会话
  const createSession = useCallback(() => {
    const newSessionId = `session_${Date.now()}`;
    const newSession: Session = {
      id: newSessionId,
      name: `新会话 ${sessions.length + 1}`,
      createdAt: Date.now(),
    };

    setSessions(prev => [...prev, newSession]);
    setCurrentSessionId(newSessionId);
    setMessages(prev => ({ ...prev, [newSessionId]: [] }));

    wsService.send({
      type: 'create_session',
      session_id: newSessionId,
    });
  }, [sessions.length]);

  // 切换会话
  const switchSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId);
    wsService.send({
      type: 'switch_session',
      session_id: sessionId,
    });
    // 切换会话时加载历史记录
    loadHistory(sessionId);
  }, [loadHistory]);

  // 删除会话
  const deleteSession = useCallback((sessionId: string) => {
    if (window.confirm('确定要删除这个会话吗？这将删除所有聊天记录。')) {
      wsService.send({
        type: 'delete_session',
        session_id: sessionId,
      });

      setSessions(prev => prev.filter(s => s.id !== sessionId));
      setMessages(prev => {
        const newMessages = { ...prev };
        delete newMessages[sessionId];
        return newMessages;
      });

      // 如果删除的是当前会话，切换到其他会话或创建新会话
      if (currentSessionId === sessionId) {
        const remainingSessions = sessions.filter(s => s.id !== sessionId);
        if (remainingSessions.length > 0) {
          switchSession(remainingSessions[0].id);
        } else {
          createDefaultSession();
        }
      }
    }
  }, [currentSessionId, sessions, switchSession, createDefaultSession]);

  // 发送消息
  const sendMessage = useCallback((content: string) => {
    if (!currentSessionId || !content.trim()) {
      return;
    }

    const userMessage: Message = {
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type: 'user',
      content,
      timestamp: Date.now(),
    };

    setMessages(prev => ({
      ...prev,
      [currentSessionId]: [...(prev[currentSessionId] || []), userMessage],
    }));

    wsService.send({
      type: 'message',
      session_id: currentSessionId,
      content,
    });
  }, [currentSessionId]);

  // 处理 WebSocket 消息
  useEffect(() => {
    const unsubscribeTextDelta = wsService.onMessage('text_delta', (data: { content: string }) => {
      if (!currentSessionId) return;

      setMessages(prev => {
        const sessionMessages = prev[currentSessionId] || [];
        const lastMessage = sessionMessages[sessionMessages.length - 1];

        if (lastMessage && lastMessage.type === 'assistant') {
          // 更新最后一条助手消息
          const updatedMessages = [...sessionMessages];
          updatedMessages[updatedMessages.length - 1] = {
            ...lastMessage,
            id: lastMessage.id || `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            content: lastMessage.content + data.content,
          };
          return { ...prev, [currentSessionId]: updatedMessages };
        } else {
          // 创建新的助手消息
          const newMessage: Message = {
            id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            type: 'assistant',
            content: data.content,
            timestamp: Date.now(),
          };
          return {
            ...prev,
            [currentSessionId]: [...sessionMessages, newMessage],
          };
        }
      });
    });

    const unsubscribeThink = wsService.onMessage('think', (data: { content: string }) => {
      if (!currentSessionId) return;

      const thinkMessage: Message = {
        id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        type: 'think',
        content: data.content,
        timestamp: Date.now(),
      };

      setMessages(prev => ({
        ...prev,
        [currentSessionId]: [...(prev[currentSessionId] || []), thinkMessage],
      }));
    });

    const unsubscribeToolCall = wsService.onMessage('tool_call', (data: { tool_name?: string; toolName?: string; arguments?: any }) => {
      if (!currentSessionId) return;

      // 兼容两种字段名：tool_name 和 toolName
      const toolName = data.tool_name || data.toolName || 'unknown';
      const toolArgs = data.arguments || {};
      

      const toolCallMessage: Message = {
        id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        type: 'tool_call',
        content: `调用工具: ${toolName}`,
        timestamp: Date.now(),
        toolName: toolName,
        toolArgs: toolArgs,
        status: 'pending',
      };

      setMessages(prev => {
        const sessionMessages = prev[currentSessionId] || [];
        const newMessages = [...sessionMessages, toolCallMessage];
        return {
          ...prev,
          [currentSessionId]: newMessages,
        };
      });
    });

    const unsubscribeToolOutput = wsService.onMessage('tool_output', (data: { tool_name?: string; toolName?: string; output?: any }) => {
      if (!currentSessionId) {
        console.warn('工具输出事件：没有当前会话ID');
        return;
      }

      // 工具输出消息的 tool_name 固定为 "工具调用结果"
      const toolName = data.tool_name || data.toolName || '工具调用结果';

      setMessages(prev => {
        const sessionMessages = prev[currentSessionId] || [];
        
        // 找到最近的 pending 状态的工具调用消息并更新状态
        let foundToolCall = false;
        let targetMessageId: string | undefined = undefined;
        
        // 从后往前查找最近的 pending 状态的工具调用消息
        for (let i = sessionMessages.length - 1; i >= 0; i--) {
          const msg = sessionMessages[i];
          if (msg.type === 'tool_call' && (msg.status === 'pending' || msg.status === undefined)) {
            targetMessageId = msg.id;
            foundToolCall = true;
            break;
          }
        }
        
        if (!foundToolCall) {
          // 如果没找到 pending 状态的，尝试查找任何非 completed 状态的工具调用消息
          for (let i = sessionMessages.length - 1; i >= 0; i--) {
            const msg = sessionMessages[i];
            if (msg.type === 'tool_call' && msg.status !== 'completed') {
              targetMessageId = msg.id;
              foundToolCall = true;
              break;
            }
          }
        }
        
        if (!foundToolCall) {
          console.error(`无法找到对应的工具调用消息`);
        }
        
        // 使用 map 创建新数组，更新匹配的消息状态
        const updatedMessages = sessionMessages.map(msg => {
          if (msg.id === targetMessageId && msg.type === 'tool_call') {
            return {
              ...msg,
              status: 'completed' as const,
            };
          }
          return msg;
        });

        // 添加工具输出消息（紧跟在对应的工具调用之后）
        const toolOutputMessage: Message = {
          id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          type: 'tool_output',
          content: '',
          timestamp: Date.now(),
          toolName: toolName,
          toolOutput: data.output,
          status: 'completed',
        };

        // 找到对应的工具调用位置，在其后插入工具输出
        let insertIndex = updatedMessages.length;
        if (targetMessageId) {
          for (let i = updatedMessages.length - 1; i >= 0; i--) {
            const msg = updatedMessages[i];
            if (msg.id === targetMessageId) {
              insertIndex = i + 1;
              break;
            }
          }
        }

        updatedMessages.splice(insertIndex, 0, toolOutputMessage);
        
        // 确保返回新的数组引用，触发 React 重新渲染
        const finalMessages = [...updatedMessages];

        return {
          ...prev,
          [currentSessionId]: finalMessages,
        };
      });
    });

    const unsubscribeComplete = wsService.onMessage('complete', () => {
      // 消息完成，可以在这里做一些清理工作
    });

    const unsubscribeError = wsService.onMessage('error', (data: { message: string }) => {
      console.error('服务器错误:', data.message);
      alert(`错误: ${data.message}`);
    });

    return () => {
      unsubscribeTextDelta();
      unsubscribeThink();
      unsubscribeToolCall();
      unsubscribeToolOutput();
      unsubscribeComplete();
      unsubscribeError();
    };
  }, [currentSessionId]);

  return (
    <div className="flex h-screen bg-gray-100">
      {/* 左侧会话列表 */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <SessionList
          sessions={sessions}
          currentSessionId={currentSessionId}
          onCreateSession={createSession}
          onSwitchSession={switchSession}
          onDeleteSession={deleteSession}
          isConnected={isConnected}
        />
      </div>

      {/* 右侧聊天窗口 */}
      <div className="flex-1 flex flex-col">
        {currentSessionId ? (
          <ChatWindow
            sessionId={currentSessionId}
            messages={messages[currentSessionId] || []}
            onSendMessage={sendMessage}
            isConnected={isConnected}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            请选择一个会话或创建新会话
          </div>
        )}
      </div>
    </div>
  );
}

export default App;

