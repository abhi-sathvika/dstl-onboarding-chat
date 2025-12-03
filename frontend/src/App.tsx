import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Message = {
  id?: number;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
};

type Conversation = {
  id: number;
  title?: string | null;
  messages?: Message[];
};

function App() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<
    number | null
  >(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");

  const API_BASE =
    (import.meta.env.VITE_API_BASE_URL as string) || "http://localhost:8000";

  const fetchConversations = async () => {
    try {
      const res = await fetch(`${API_BASE}/conversations/`);
      if (!res.ok) throw new Error("Failed to fetch conversations");
      const data = await res.json();
      setConversations(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadConversation = async (id: number) => {
    try {
      const res = await fetch(`${API_BASE}/conversations/${id}`);
      if (!res.ok) throw new Error("Failed to fetch conversation");
      const data: Conversation = await res.json();
      setActiveConversationId(id);
      setMessages(data.messages || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;

    setInput("");

    try {
      let convId = activeConversationId;

      // If no active conversation, create one first (title left null)
      if (!convId) {
        const createConvRes = await fetch(`${API_BASE}/conversations/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: null }),
        });
        if (!createConvRes.ok) throw new Error("Failed to create conversation");
        const newConv: Conversation = await createConvRes.json();
        convId = newConv.id;
        await fetchConversations();
        setActiveConversationId(convId);
      }

      // Create the message (role user)
      const createMsgRes = await fetch(`${API_BASE}/messages/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: convId,
          role: "user",
          content: text,
        }),
      });

      if (!createMsgRes.ok) {
        throw new Error("Failed to create message");
      }

      const resJson = await createMsgRes.json();

      // If backend returned both user and assistant messages, append both
      if (resJson.user && resJson.assistant) {
        setMessages((prev) => [
          ...prev,
          resJson.user as Message,
          resJson.assistant as Message,
        ]);
      } else if (resJson.message) {
        setMessages((prev) => [...prev, resJson.message as Message]);
      } else {
        // Fallback: append the user text locally
        setMessages((prev) => [...prev, { role: "user", content: text }]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-gray-900 text-white p-4 flex flex-col">
        <div className="mb-4">
          <h1 className="text-xl font-bold">DSTL Chat App</h1>
        </div>
        <button
          className="w-full py-2 px-4 border border-gray-600 rounded hover:bg-gray-800 text-left mb-4"
          onClick={() => {
            setActiveConversationId(null);
            setMessages([]);
          }}
        >
          + New Chat
        </button>
        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 && (
            <div className="text-sm text-gray-400">No conversations yet</div>
          )}
          <ul className="space-y-2">
            {conversations.map((conv) => (
              <li
                key={conv.id}
                className={`p-2 rounded cursor-pointer hover:bg-gray-800 ${
                  conv.id === activeConversationId ? "bg-gray-700" : ""
                }`}
                onClick={() => loadConversation(conv.id)}
              >
                {conv.title || `Conversation ${conv.id}`}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[70%] rounded-lg p-3 markdown-content ${
                  msg.role === "user"
                    ? "bg-blue-500 text-white"
                    : "bg-white border border-gray-200 text-gray-800"
                }`}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
              </div>
            </div>
          ))}
          {messages.length === 0 && (
            <div className="text-center text-gray-500 mt-20">
              <h2 className="text-2xl font-semibold">
                Welcome to the DSTL Chat App
              </h2>
              <p>Start a conversation!</p>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-gray-200 bg-white">
          <div className="flex gap-4 max-w-4xl mx-auto">
            <textarea
              className="flex-1 border border-gray-300 rounded-lg p-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={1}
              placeholder="Type a message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button
              className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50"
              onClick={handleSend}
              disabled={!input.trim()}
            >
              Send
            </button>
          </div>
          <div className="text-center text-xs text-gray-400 mt-2">
            Press Enter to send
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
