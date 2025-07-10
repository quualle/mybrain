'use client'

import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { User, Bot, FileText, Calendar } from 'lucide-react'
import type { Message } from '@/frontend/lib/types'

interface MessageListProps {
  messages: Message[]
  isLoading: boolean
}

export default function MessageList({ messages, isLoading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="h-full overflow-y-auto scrollbar-thin p-4 space-y-6">
      {messages.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
          <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mb-4">
            <Bot className="w-8 h-8 text-gray-600 dark:text-gray-300" />
          </div>
          <p className="text-lg text-gray-700 dark:text-white">Stelle eine Frage zu deinem Wissen</p>
          <p className="text-sm mt-2 text-gray-600 dark:text-gray-300">Ich durchsuche alle deine Gespräche, Videos und Notizen</p>
        </div>
      )}

      {messages.map((message) => (
        <div
          key={message.id}
          className={`chat-message flex ${
            message.role === 'user' ? 'justify-end' : 'justify-start'
          }`}
        >
          <div
            className={`max-w-3xl ${
              message.role === 'user'
                ? 'bg-primary-600 text-white rounded-lg px-4 py-3'
                : 'bg-gray-100 dark:bg-gray-700 rounded-lg'
            }`}
          >
            {message.role === 'assistant' && (
              <div className="flex items-center space-x-2 px-4 pt-3 pb-2 border-b border-gray-200 dark:border-gray-600">
                <Bot className="w-5 h-5 text-primary-600" />
                <span className="font-medium text-gray-900 dark:text-white">MyBrain</span>
                {message.model && (
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {message.model}
                  </span>
                )}
              </div>
            )}

            <div
              className={`${
                message.role === 'user' 
                  ? '' 
                  : 'px-4 py-3 markdown-content text-gray-900 dark:text-white'
              }`}
            >
              {message.role === 'user' ? (
                <div className="flex items-start space-x-2">
                  <User className="w-5 h-5 mt-0.5 flex-shrink-0" />
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </div>
              ) : (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({ node, inline, className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || '')
                      return !inline && match ? (
                        <SyntaxHighlighter
                          style={vscDarkPlus}
                          language={match[1]}
                          PreTag="div"
                          className="rounded-md my-2"
                          {...props}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      )
                    },
                    table({ children }) {
                      return (
                        <div className="overflow-x-auto my-4">
                          <table className="min-w-full">{children}</table>
                        </div>
                      )
                    },
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              )}
            </div>

            {message.sources && message.sources.length > 0 && (
              <div className="px-4 pb-3 pt-2 border-t border-gray-200 dark:border-gray-600">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Quellen:</p>
                <div className="space-y-1">
                  {message.sources.map((source, idx) => (
                    <div
                      key={idx}
                      className="flex items-center space-x-2 text-xs text-gray-600 dark:text-gray-300"
                    >
                      <FileText className="w-3 h-3" />
                      <span className="font-medium">{source.title}</span>
                      {source.date && (
                        <>
                          <Calendar className="w-3 h-3" />
                          <span>{new Date(source.date).toLocaleDateString('de-DE')}</span>
                        </>
                      )}
                      {source.speaker && (
                        <span className="text-primary-600">• {source.speaker}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ))}

      {isLoading && (
        <div className="flex justify-start">
          <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-3">
            <div className="flex items-center space-x-2">
              <Bot className="w-5 h-5 text-primary-600" />
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}