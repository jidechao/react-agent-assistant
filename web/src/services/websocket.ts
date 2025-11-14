import { WebSocketMessage } from '../types';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private messageHandlers: Map<string, Set<(data: any) => void>> = new Map();
  private onConnectHandlers: Set<() => void> = new Set();
  private onDisconnectHandlers: Set<() => void> = new Set();

  connect(): void {
    // 如果正在连接或已连接，不重复连接
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      return;
    }

    // 如果之前的连接还在关闭中，等待关闭完成
    if (this.ws?.readyState === WebSocket.CLOSING) {
      // 等待关闭完成后再连接
      const checkClose = setInterval(() => {
        if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
          clearInterval(checkClose);
          setTimeout(() => this.connect(), 100);
        }
      }, 50);
      return;
    }

    // 如果存在旧连接，先清理
    if (this.ws) {
      try {
        // 移除事件监听器，避免触发错误日志
        this.ws.onerror = null;
        this.ws.onclose = null;
        // 如果连接已打开，正常关闭（code 1000）
        if (this.ws.readyState === WebSocket.OPEN) {
          this.ws.close(1000, 'Reconnecting');
          // 等待关闭完成
          setTimeout(() => {
            this.ws = null;
            this._createConnection();
          }, 100);
          return;
        } else if (this.ws.readyState === WebSocket.CONNECTING) {
          // 如果正在连接，等待连接建立或失败后再处理
          const timeout = setTimeout(() => {
            if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
              this.ws.close();
              this.ws = null;
              this._createConnection();
            }
          }, 500);
          
          const originalOnOpen = this.ws.onopen;
          const originalOnClose = this.ws.onclose;
          
          this.ws.onopen = () => {
            clearTimeout(timeout);
            if (originalOnOpen) originalOnOpen.call(this.ws);
          };
          
          this.ws.onclose = () => {
            clearTimeout(timeout);
            this.ws = null;
            if (originalOnClose) originalOnClose.call(this.ws);
            this._createConnection();
          };
          
          return;
        } else {
          // 已关闭或正在关闭，直接清理
          this.ws = null;
        }
      } catch (e) {
        // 忽略清理错误
        this.ws = null;
      }
    }

    this._createConnection();
  }

  private _createConnection(): void {
    try {
      this.ws = new WebSocket(WS_URL);

      this.ws.onopen = () => {
        console.log('WebSocket 连接已建立');
        this.reconnectAttempts = 0;
        this.onConnectHandlers.forEach(handler => handler());
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('解析 WebSocket 消息失败:', error);
        }
      };

      this.ws.onerror = () => {
        // WebSocket 错误事件不提供详细的错误信息
        // 错误详情通常在 onclose 事件中
        // 静默处理错误，让 onclose 处理重连逻辑
        // 不输出错误日志，避免控制台噪音
      };

      this.ws.onclose = (event) => {
        // 只在非正常关闭时输出日志
        if (event.code !== 1000 && event.code !== 1005) {
          // 1005 是浏览器内部错误码，通常表示连接异常关闭，但不一定是严重问题
          if (import.meta.env.DEV) {
            console.log('WebSocket 连接已关闭', event.code, event.reason || '无原因');
          }
        }
        this.onDisconnectHandlers.forEach(handler => handler());
        // 只有在非正常关闭时才重连（code !== 1000 表示非正常关闭）
        // 避免在正常关闭时重连
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.attemptReconnect();
        }
      };
    } catch (error) {
      console.error('创建 WebSocket 连接失败:', error);
      this.attemptReconnect();
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.reconnectAttempts = this.maxReconnectAttempts; // 阻止自动重连
  }

  send(message: WebSocketMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket 未连接，无法发送消息');
    }
  }

  onMessage(type: string, handler: (data: any) => void): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, new Set());
    }
    this.messageHandlers.get(type)!.add(handler);

    // 返回取消订阅函数
    return () => {
      this.messageHandlers.get(type)?.delete(handler);
    };
  }

  onConnect(handler: () => void): () => void {
    this.onConnectHandlers.add(handler);
    return () => {
      this.onConnectHandlers.delete(handler);
    };
  }

  onDisconnect(handler: () => void): () => void {
    this.onDisconnectHandlers.add(handler);
    return () => {
      this.onDisconnectHandlers.delete(handler);
    };
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private handleMessage(message: WebSocketMessage): void {
    // 调试：记录所有收到的消息（特别是工具相关消息）
    if (message.type === 'tool_call' || message.type === 'tool_output' || message.type === 'think') {
      console.log('🔧 WebSocket收到工具相关消息:', JSON.stringify(message, null, 2));
    }
    
    const handlers = this.messageHandlers.get(message.type);
    if (handlers) {
      console.log(`✓ 找到 ${message.type} 的处理器，数量: ${handlers.size}`);
      handlers.forEach(handler => {
        try {
          handler(message);
        } catch (error) {
          console.error(`处理 ${message.type} 消息时出错:`, error);
        }
      });
    } else {
      // 调试：记录未处理的消息类型
      if (message.type !== 'text_delta' && message.type !== 'complete' && message.type !== 'connected' && message.type !== 'session_created') {
        console.warn('⚠️ 未注册的消息类型:', message.type, JSON.stringify(message, null, 2));
      }
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('达到最大重连次数，停止重连');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    console.log(`将在 ${delay}ms 后尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    setTimeout(() => {
      this.connect();
    }, delay);
  }
}

export const wsService = new WebSocketService();

