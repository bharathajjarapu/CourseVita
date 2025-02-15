
import { useState, useRef, useEffect } from "react";
import { MessageSquare, ArrowRight, Mic } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import ReactMarkdown from 'react-markdown';

interface Message {
  text: string;
  isBot: boolean;
}

const ThinkingDots = () => (
  <div className="flex space-x-2 items-center p-4 bg-secondary rounded-2xl message-animation">
    <MessageSquare className="w-5 h-5 shrink-0" />
    <div className="flex space-x-2">
      <div className="w-2 h-2 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
      <div className="w-2 h-2 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
      <div className="w-2 h-2 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
    </div>
  </div>
);

const Index = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      text: "Hello! I'm your FAQ assistant. How can I help you today?",
      isBot: true,
    },
  ]);
  const [input, setInput] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const { toast } = useToast();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
      const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognitionAPI();
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;

      recognitionRef.current.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map(result => result[0].transcript)
          .join('');

        setInput(transcript);

        if (event.results[event.results.length - 1].isFinal) {
          setInput(transcript);
        }
      };

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      console.error('Speech recognition not supported');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = { text: input, isBot: false };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch('http://192.168.0.225:8000/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ question: userMessage.text }),
      });

      if (response.status === 405) {
        throw new Error('Method not allowed. Please check the API endpoint configuration.');
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const botResponse = {
        text: data.answer,
        isBot: true,
      };
      setMessages((prev) => [...prev, botResponse]);
    } catch (error) {
      console.error('Error:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to get response from the assistant. Please try again.",
      });

      const errorMessage = {
        text: "I apologize, but I'm having trouble processing your request. Please try again.",
        isBot: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background p-4 md:p-6">
      <div className="max-w-4xl w-full text-center mb-8 space-y-2">
        <h1 className="text-4xl font-bold tracking-tight">FAQ Assistant</h1>
        <p className="text-muted-foreground">
          Get instant answers to your questions
        </p>
      </div>

      <div className="w-full max-w-4xl glass-morphism rounded-2xl overflow-hidden">
        <div className="h-[500px] overflow-y-auto p-6 space-y-4 scrollbar-hide">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${
                message.isBot ? "justify-start" : "justify-end"
              }`}
            >
              <div
                className={`flex items-start space-x-2 max-w-[80%] message-animation ${
                  message.isBot
                    ? "bg-secondary"
                    : "bg-white/10"
                } rounded-2xl p-4`}
              >
                {message.isBot && (
                  <MessageSquare className="w-5 h-5 mt-1 shrink-0" />
                )}
                <div className="prose prose-invert min-w-0 prose-p:leading-relaxed prose-pre:p-0">
                  <ReactMarkdown>{message.text}</ReactMarkdown>
                </div>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <ThinkingDots />
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form
          onSubmit={handleSubmit}
          className="border-t border-white/10 p-4 input-animation"
        >
          <div className="flex items-center space-x-4">
            <button
              type="button"
              onClick={toggleListening}
              disabled={isLoading}
              className={`transition-all duration-200 rounded-xl p-3 ${
                isListening
                  ? "bg-red-500/80 hover:bg-red-500"
                  : "bg-white/10 hover:bg-white/20"
              } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              <Mic className="w-5 h-5" />
            </button>
            <div className="flex-1 bg-secondary rounded-xl px-4 py-3 flex items-center">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your question here..."
                disabled={isLoading}
                className="flex-1 bg-transparent text-sm md:text-base focus:outline-none disabled:cursor-not-allowed"
              />
              <button
                type="submit"
                disabled={isLoading}
                className={`ml-2 text-white/70 hover:text-white transition-colors ${
                  isLoading ? "opacity-50 cursor-not-allowed" : ""
                }`}
              >
                <ArrowRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Index;
