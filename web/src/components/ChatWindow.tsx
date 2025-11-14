import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Message } from '../types';
import MessageInput from './MessageInput';

// 工具调用卡片组件
function ToolCallCard({ message, toolOutput }: { message: Message; toolOutput?: Message }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const content = toolOutput 
      ? JSON.stringify(toolOutput.toolOutput || toolOutput.content, null, 2)
      : JSON.stringify(message.toolArgs || {}, null, 2);
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  // 格式化工具名称（服务器名: 工具名）
  const formatToolName = (toolName: string | undefined, isToolOutput: boolean = false) => {
    // 如果是工具输出且工具名称为空或unknown，显示"工具调用结果"
    if (isToolOutput && (!toolName || toolName === 'unknown')) {
      return '工具调用结果';
    }
    
    if (!toolName || toolName === 'unknown') {
      // 尝试从 message.content 中提取工具名称
      if (message.content && message.content.includes('调用工具:')) {
        const match = message.content.match(/调用工具:\s*(.+)/);
        if (match && match[1]) {
          return match[1].trim();
        }
      }
      return '工具调用';
    }
    // 如果工具名包含冒号，说明已经格式化过了
    if (toolName.includes(':')) return toolName;
    // 否则尝试从 toolName 中提取服务器名和工具名
    // 格式可能是 "server_name:tool_name" 或只是 "tool_name"
    return toolName;
  };

  // 格式化JSON显示（带语法高亮）
  const formatJSON = (obj: any): string => {
    if (typeof obj === 'string') {
      try {
        obj = JSON.parse(obj);
      } catch {
        return obj;
      }
    }
    return JSON.stringify(obj, null, 2);
  };

  // 确定显示内容：如果有工具输出，优先显示工具输出；否则显示工具调用参数
  const displayContent = toolOutput 
    ? (toolOutput.toolOutput !== undefined ? toolOutput.toolOutput : (toolOutput.content !== undefined ? toolOutput.content : {}))
    : (message.toolArgs || {});
  
  // 检查是否有内容需要显示
  // 工具调用卡片应该始终显示，即使没有参数或输出
  const hasContent = toolOutput 
    ? (toolOutput.toolOutput !== undefined || (toolOutput.content !== undefined && toolOutput.content !== '' && toolOutput.content !== null))
    : (message.toolArgs && typeof message.toolArgs === 'object' && Object.keys(message.toolArgs).length > 0);
  

  return (
    <div className="bg-white rounded-lg border border-gray-200 mb-2 shadow-sm">
      {/* 工具名称和状态头部 */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">
            {formatToolName(message.toolName, !!toolOutput)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {(!message.status || message.status === 'pending') && (
            <span className="text-xs text-amber-600 animate-pulse">执行中...</span>
          )}
          {message.status === 'completed' && (
            <span className="flex items-center gap-1 text-xs text-green-600">
              <span className="text-green-500">✓</span>
              <span>已完成</span>
            </span>
          )}
          {/* 复制按钮 */}
          {hasContent && (
            <button
              onClick={handleCopy}
              className="p-1 hover:bg-gray-200 rounded transition-colors"
              title="复制"
            >
              <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </button>
          )}
          {/* 展开/折叠按钮 */}
          {hasContent && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 hover:bg-gray-200 rounded transition-colors"
              title={isExpanded ? "折叠" : "展开"}
            >
              <svg 
                className={`w-4 h-4 text-gray-600 transition-transform ${isExpanded ? '' : 'rotate-180'}`} 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          )}
          {/* 如果没有内容，显示提示信息 */}
          {!hasContent && !toolOutput && (
            <span className="text-xs text-gray-500">无参数</span>
          )}
        </div>
      </div>
      
      {/* 内容区域 - 如果有内容且已展开，则显示 */}
      {hasContent && isExpanded && (
        <div className="px-4 py-3">
          {copied && (
            <div className="mb-2 text-xs text-green-600">已复制到剪贴板</div>
          )}
          <pre className="text-xs bg-gray-50 p-3 rounded border border-gray-200 overflow-x-auto max-h-96 overflow-y-auto font-mono">
            <code className="text-gray-800">
              {formatJSON(displayContent)}
            </code>
          </pre>
        </div>
      )}
    </div>
  );
}

interface ChatWindowProps {
  sessionId: string;
  messages: Message[];
  onSendMessage: (content: string) => void;
  isConnected: boolean;
}

export default function ChatWindow({
  sessionId: _sessionId,
  messages,
  onSendMessage,
  isConnected,
}: ChatWindowProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [inputValue, setInputValue] = useState('');

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (inputValue.trim() && isConnected) {
      onSendMessage(inputValue);
      setInputValue('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <p className="text-lg mb-2">开始对话</p>
              <p className="text-sm">输入您的问题，AI 助手将为您解答</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message, index) => {
              // 确保 key 唯一且有效
              const messageKey = (message.id && 
                                 message.id !== '__fake_id__' && 
                                 message.id !== 'undefined' &&
                                 typeof message.id === 'string' &&
                                 message.id.trim() !== '')
                ? message.id
                : `msg_${index}_${message.timestamp || Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
              
              return (
              <div
                key={messageKey}
                className={`flex ${
                  message.type === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {/* 用户消息 */}
                {message.type === 'user' && (
                  <div className="max-w-3xl rounded-lg px-4 py-3 bg-blue-500 text-white">
                    <div className="whitespace-pre-wrap">{message.content}</div>
                    <div className="text-xs opacity-75 mt-1">
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                )}
                
                {/* 助手消息（包括思考、工具调用、工具输出、最终答案） */}
                {message.type !== 'user' && (
                  <div className="max-w-3xl w-full">
                    {/* 思考消息 - 显示为普通文本 */}
                    {message.type === 'think' && (
                      <div className="bg-white rounded-lg px-4 py-3 border border-gray-200 mb-2">
                        <div className="whitespace-pre-wrap text-gray-800">{message.content}</div>
                      </div>
                    )}
                    
                    {/* 工具调用消息 - 显示为独立卡片（只显示工具调用参数） */}
                    {message.type === 'tool_call' && (
                      <ToolCallCard 
                        message={message}
                        toolOutput={undefined}
                      />
                    )}
                    
                    {/* 工具输出消息 - 显示为独立卡片（显示工具调用结果） */}
                    {message.type === 'tool_output' && (
                      <ToolCallCard 
                        message={{
                          ...message,
                          type: 'tool_call',
                          toolName: message.toolName || 'unknown',
                          toolArgs: {},
                          status: 'completed'
                        }}
                        toolOutput={message}
                      />
                    )}
                    
                    {/* 最终答案消息 */}
                    {message.type === 'assistant' && (
                      <div className="bg-white rounded-lg px-4 py-3 border border-gray-200">
                        <div className="text-gray-800 markdown-content">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              code({ node, className, children, ...props }: any) {
                                const match = /language-(\w+)/.exec(className || '');
                                const isInline = !match;
                                return !isInline && match ? (
                                  <div className="my-2">
                                    <SyntaxHighlighter
                                      style={vscDarkPlus}
                                      language={match[1]}
                                      PreTag="div"
                                      className="rounded-md !mt-0 !mb-0"
                                      {...props}
                                    >
                                      {String(children).replace(/\n$/, '')}
                                    </SyntaxHighlighter>
                                  </div>
                                ) : (
                                  <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono text-gray-800" {...props}>
                                    {children}
                                  </code>
                                );
                              },
                              h1: ({ children }) => <h1 className="text-2xl font-bold mt-4 mb-2 text-gray-900">{children}</h1>,
                              h2: ({ children }) => <h2 className="text-xl font-bold mt-3 mb-2 text-gray-900">{children}</h2>,
                              h3: ({ children }) => <h3 className="text-lg font-bold mt-2 mb-1 text-gray-900">{children}</h3>,
                              p: ({ children }) => <p className="mb-2 leading-relaxed">{children}</p>,
                              ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                              ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                              li: ({ children }) => <li className="ml-4">{children}</li>,
                              blockquote: ({ children }) => (
                                <blockquote className="border-l-4 border-gray-300 pl-4 italic my-2 text-gray-600">
                                  {children}
                                </blockquote>
                              ),
                              a: ({ href, children }) => (
                                <a href={href} className="text-blue-600 hover:text-blue-800 underline" target="_blank" rel="noopener noreferrer">
                                  {children}
                                </a>
                              ),
                              table: ({ children }) => (
                                <div className="overflow-x-auto my-2">
                                  <table className="min-w-full border-collapse border border-gray-300">
                                    {children}
                                  </table>
                                </div>
                              ),
                              thead: ({ children }) => <thead className="bg-gray-100">{children}</thead>,
                              tbody: ({ children }) => <tbody>{children}</tbody>,
                              tr: ({ children }) => <tr className="border-b border-gray-200">{children}</tr>,
                              th: ({ children }) => <th className="border border-gray-300 px-4 py-2 text-left font-semibold">{children}</th>,
                              td: ({ children }) => <td className="border border-gray-300 px-4 py-2">{children}</td>,
                              hr: () => <hr className="my-4 border-gray-300" />,
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                        </div>
                        <div className="text-xs text-gray-500 mt-2">
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* 输入框 */}
      <div className="border-t border-gray-200 bg-white p-4">
        {!isConnected && (
          <div className="mb-2 text-sm text-red-500">
            ⚠️ 未连接到服务器，请检查连接状态
          </div>
        )}
        <MessageInput
          value={inputValue}
          onChange={setInputValue}
          onSend={handleSend}
          onKeyPress={handleKeyPress}
          disabled={!isConnected}
        />
      </div>
    </div>
  );
}

