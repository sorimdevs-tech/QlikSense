# 🤖 Hugging Face Chat - Quick Start

## What You Can Do Now

**Send your table data + ask questions → Get AI-powered answers**

---

## 3 Chat Endpoints

### 1. Single Question
```bash
curl -X POST "http://localhost:8000/chat/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "Sales",
    "data": [{"product":"A","sales":1000},{"product":"B","sales":2000}],
    "question": "What is the total sales?"
  }'
```

### 2. AI Summary
```bash
curl -X POST "http://localhost:8000/chat/summary-hf" \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "Sales",
    "data": [{"product":"A","sales":1000},{"product":"B","sales":2000}]
  }'
```

### 3. Conversation
```bash
curl -X POST "http://localhost:8000/chat/multi-turn" \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "Sales",
    "data": [...],
    "conversation": [
      {"role":"user","content":"What is total?"},
      {"role":"assistant","content":"The total is 3000."},
      {"role":"user","content":"Highest product?"}
    ]
  }'
```

---

## React Example (Multi-Turn Chat)

```typescript
import { useState } from 'react';

export function ChatBot({ tableData }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  const handleSend = async () => {
    const updatedMessages = [...messages, { role: 'user', content: input }];
    setMessages(updatedMessages);
    setInput('');

    const res = await fetch('http://localhost:8000/chat/multi-turn', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        table_name: 'My Data',
        data: tableData,
        conversation: updatedMessages
      })
    });

    const data = await res.json();
    setMessages(data.conversation);
  };

  return (
    <div>
      <div>
        {messages.map((msg, i) => (
          <div key={i}>
            <strong>{msg.role === 'user' ? 'You' : 'AI'}:</strong> {msg.content}
          </div>
        ))}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask about your data..."
      />
      <button onClick={handleSend}>Send</button>
    </div>
  );
}
```

---

## Example Questions

- "What is the total sales?"
- "What's the average value?"
- "Which product has highest sales?"
- "What are the key insights?"
- "Tell me about top categories"
- "Summarize this data"

---

## Install Requirements

```bash
pip install transformers torch
```

---

## Test It

```bash
# Start server
python -m uvicorn main:app --reload

# In browser: http://localhost:8000/docs
# Try /chat/analyze endpoint
```

---

## Features

✅ AI-powered Q&A
✅ Multi-turn conversations
✅ Intelligent summaries
✅ Context-aware responses
✅ Fallback to rule-based answers

---

**See [HUGGINGFACE_CHAT.md](HUGGINGFACE_CHAT.md) for complete documentation**
