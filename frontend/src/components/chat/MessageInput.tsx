import React, { useState, useRef, useEffect } from 'react';
import { apiService } from '@/services/api';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { Send, Paperclip, Mic, Square } from 'lucide-react';

interface MessageInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const MessageInput: React.FC<MessageInputProps> = ({
  onSendMessage,
  disabled = false,
  placeholder = "Type your message...",
}) => {
  const [message, setMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<any>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleFileUpload = () => {
    fileInputRef.current?.click();
  };

  const onFilesSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    try {
      setUploading(true);
      await apiService.uploadDocuments({ files: Array.from(files) });
      // Add a lightweight system hint into the textbox
      setMessage(prev => prev ? prev : 'Files uploaded. Ask a question to analyze them.');
    } catch (err) {
      console.error('Upload failed', err);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleVoiceRecording = () => {
    if (isRecording) {
      setIsRecording(false);
      try { recognitionRef.current?.stop?.(); } catch {}
      return;
    }
    try {
      const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
      if (!SpeechRecognition) {
        console.warn('Web Speech API not available in this browser');
        return;
      }
      const rec = new SpeechRecognition();
      recognitionRef.current = rec;
      rec.continuous = false;
      rec.interimResults = true;
      rec.lang = 'en-US';
      let finalText = '';
      rec.onresult = (event: any) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalText += transcript + ' ';
          } else {
            interim += transcript;
          }
        }
        setMessage((finalText + interim).trim());
      };
      rec.onend = () => setIsRecording(false);
      rec.start();
      setIsRecording(true);
    } catch (e) {
      console.warn('Speech recognition failed to start', e);
    }
  };

  return (
    <Card className="p-4">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="relative">
          <input ref={fileInputRef} type="file" multiple className="hidden" onChange={onFilesSelected} />
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            className="min-h-[60px] max-h-[200px] resize-none pr-12"
            rows={1}
          />
          
          <div className="absolute right-2 bottom-2 flex gap-1">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleFileUpload}
              disabled={disabled || uploading}
              className="h-8 w-8 p-0"
            >
              <Paperclip className="h-4 w-4" />
            </Button>
            
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleVoiceRecording}
              disabled={disabled}
              className={`h-8 w-8 p-0 ${isRecording ? 'text-red-500' : ''}`}
            >
              {isRecording ? (
                <Square className="h-4 w-4" />
              ) : (
                <Mic className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
        
        <div className="flex justify-between items-center">
          <div className="text-xs text-muted-foreground">
            Press Enter to send, Shift+Enter for new line {uploading ? '· Uploading…' : ''}
          </div>
          
          <Button
            type="submit"
            disabled={!message.trim() || disabled}
            size="sm"
            className="gap-2"
          >
            <Send className="h-4 w-4" />
            Send
          </Button>
        </div>
      </form>
    </Card>
  );
};
