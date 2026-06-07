interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface Props {
  message: Message
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'

  const formatContent = (text: string) => {
    return text.split('\n').map((line, i) => (
      <span key={i}>
        {line}
        {i < text.split('\n').length - 1 && <br />}
      </span>
    ))
  }

  if (isUser) {
    return (
      <div className="flex justify-end animate-fade-in">
        <div className="max-w-[80%]">
          <div className="bg-brown text-cream-dark rounded-2xl rounded-br-sm px-4 py-2.5 shadow-sm">
            <p className="text-sm font-sans leading-relaxed">{formatContent(message.content)}</p>
          </div>
          <p className="text-right text-xs text-brown-light opacity-40 mt-1 font-sans">
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-end gap-2 animate-fade-in">
      <div className="w-8 h-8 rounded-full bg-gold flex items-center justify-center text-white text-xs flex-shrink-0 shadow-sm">
        💍
      </div>
      <div className="max-w-[80%]">
        <div className="bg-cream rounded-2xl rounded-bl-sm px-4 py-2.5 border border-cream-dark shadow-sm">
          <p className="text-sm font-sans leading-relaxed text-brown">{formatContent(message.content)}</p>
        </div>
        <p className="text-xs text-brown-light opacity-40 mt-1 font-sans">
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  )
}
