'use client'

import { useEffect, useState } from 'react'
import { Mic, MicOff } from 'lucide-react'

interface VoiceInputProps {
  onTranscript: (transcript: string) => void
  onStop: () => void
}

export default function VoiceInput({ onTranscript, onStop }: VoiceInputProps) {
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')

  useEffect(() => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      console.error('Speech recognition not supported')
      onStop()
      return
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    const recognition = new SpeechRecognition()

    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'de-DE'

    recognition.onstart = () => {
      setIsListening(true)
    }

    recognition.onresult = (event: any) => {
      let interimTranscript = ''
      let finalTranscript = ''

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          finalTranscript += result[0].transcript + ' '
        } else {
          interimTranscript += result[0].transcript
        }
      }

      setTranscript(finalTranscript + interimTranscript)
    }

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error)
      setIsListening(false)
      onStop()
    }

    recognition.onend = () => {
      setIsListening(false)
      if (transcript) {
        onTranscript(transcript)
      }
    }

    recognition.start()

    return () => {
      recognition.stop()
    }
  }, [])

  return (
    <div className="mt-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
      <div className="flex items-center space-x-2">
        {isListening ? (
          <Mic className="w-4 h-4 text-red-600 animate-pulse" />
        ) : (
          <MicOff className="w-4 h-4 text-red-600" />
        )}
        <p className="text-sm text-red-600 dark:text-red-400">
          {isListening ? 'Höre zu...' : 'Mikrofon wird vorbereitet...'}
        </p>
      </div>
      {transcript && (
        <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">{transcript}</p>
      )}
    </div>
  )
}