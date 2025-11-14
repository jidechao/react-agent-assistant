export interface Message {
  id: string;
  type: 'user' | 'assistant' | 'think' | 'tool_call' | 'tool_output';
  content: string;
  timestamp: number;
  toolName?: string;
  toolArgs?: any;
  toolOutput?: any;
  status?: 'pending' | 'completed' | 'error'; // 工具调用状态
}

export interface Session {
  id: string;
  name: string;
  createdAt: number;
  lastMessageAt?: number;
}

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface AppState {
  sessions: Session[];
  currentSessionId: string | null;
  messages: Record<string, Message[]>;
  wsConnection: WebSocket | null;
  isConnected: boolean;
}

