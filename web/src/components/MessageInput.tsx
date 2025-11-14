interface MessageInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onKeyPress: (e: React.KeyboardEvent) => void;
  disabled?: boolean;
}

export default function MessageInput({
  value,
  onChange,
  onSend,
  onKeyPress,
  disabled = false,
}: MessageInputProps) {
  return (
    <div className="flex items-end space-x-2">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyPress={onKeyPress}
        placeholder={disabled ? '连接中...' : '输入您的问题...'}
        disabled={disabled}
        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none disabled:bg-gray-100 disabled:cursor-not-allowed"
        rows={1}
        style={{ minHeight: '44px', maxHeight: '200px' }}
      />
      <button
        onClick={onSend}
        disabled={disabled || !value.trim()}
        className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
      >
        发送
      </button>
    </div>
  );
}

