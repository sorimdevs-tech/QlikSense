# 🤖 Hugging Face Chat Integration - Complete Guide

## Overview

Your table data can now be analyzed using AI-powered Hugging Face models. Ask questions about your data, get intelligent summaries, and have multi-turn conversations.

---

## 4️⃣ New Chat Endpoints

### 1. POST /chat/analyze
**Single Question Analysis**

Ask one question about your table data.

**Request:**
```json
{
  "table_name": "Sales Data",
  "data": [
    {"product": "Laptop", "sales": 5000, "region": "North"},
    {"product": "Mouse", "sales": 500, "region": "South"},
    {"product": "Monitor", "sales": 2000, "region": "East"}
  ],
  "question": "What is the total sales amount?"
}
```

**Response:**
```json
{
  "success": true,
  "table_name": "Sales Data",
  "question": "What is the total sales amount?",
  "response": "The total sales amount across all products is 7500.",
  "metrics_context": {
    "Total Records": 3,
    "Total Value": 7500,
    "Average Value": 2500,
    "Min Value": 500,
    "Max Value": 5000
  }
}
```

**Best for:** Quick questions about your data

---

### 2. POST /chat/summary-hf
**AI-Powered Summary Generation**

Generate intelligent summaries using Hugging Face models.

**Request:**
```json
{
  "table_name": "Sales Data",
  "data": [...]
}
```

**Response:**
```json
{
  "success": true,
  "table_name": "Sales Data",
  "summary": "This dataset contains sales information across three regions. The highest performing product is Laptop with 5000 units sold in the North region...",
  "metrics": {
    "Total Records": 3,
    "Total Value": 7500,
    "Average Value": 2500,
    "Top Categories": {
      "Laptop": 5000,
      "Monitor": 2000,
      "Mouse": 500
    }
  },
  "quality_score": 100.0
}
```

**Best for:** Getting intelligent narrative summaries

---

### 3. POST /chat/multi-turn
**Multi-Turn Conversation**

Have ongoing conversations with context memory.

**Request:**
```json
{
  "table_name": "Sales Data",
  "data": [...],
  "conversation": [
    {
      "role": "user",
      "content": "What's the total sales?"
    },
    {
      "role": "assistant",
      "content": "The total sales amount is 7500."
    },
    {
      "role": "user",
      "content": "What's the highest selling product?"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "table_name": "Sales Data",
  "conversation": [
    {"role": "user", "content": "What's the total sales?"},
    {"role": "assistant", "content": "The total sales amount is 7500."},
    {"role": "user", "content": "What's the highest selling product?"},
    {"role": "assistant", "content": "The highest selling product is Laptop with 5000 units."}
  ],
  "last_response": "The highest selling product is Laptop with 5000 units.",
  "metrics_context": {...}
}
```

**Best for:** Extended analysis and follow-up questions

---

### 4. GET /chat/help
**Get Help and Examples**

Learn what questions you can ask.

**Response:**
```json
{
  "success": true,
  "endpoints": {
    "/chat/analyze": "Ask a single question about your data",
    "/chat/summary-hf": "Generate AI-powered summary",
    "/chat/multi-turn": "Multi-turn conversation with context"
  },
  "example_questions": [
    "What is the total sales amount?",
    "What's the average value?",
    "Which category has the highest value?",
    "What are the key insights?",
    "Tell me about the data distribution"
  ]
}
```

---

## 🎯 Example Questions You Can Ask

### Data Metrics
- "What is the total sales amount?"
- "What's the average value in this dataset?"
- "What is the highest/lowest value?"
- "How many records are in this dataset?"

### Category Analysis
- "Which category has the highest value?"
- "What are the top categories?"
- "How are the values distributed across categories?"
- "Which region/product/category performs best?"

### Insights
- "What are the key insights from this data?"
- "Summarize the main findings"
- "What patterns do you see?"
- "Tell me about the data distribution"

### Quality & Completeness
- "Are there any missing values?"
- "What is the data quality?"
- "Is the data complete?"

### Comparisons
- "Compare products A and B"
- "How does North region compare to South?"
- "What's the relationship between categories?"

---

## 💻 Frontend Integration

### React Example with Single Question

```typescript
import { useState } from 'react';

export function ChatAnalyzer({ tableData }) {
  const [question, setQuestion] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleAsk = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/chat/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table_name: 'My Data',
          data: tableData,
          question: question
        })
      });
      
      const data = await res.json();
      setResponse(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask a question about your data..."
      />
      <button onClick={handleAsk} disabled={loading}>
        {loading ? 'Analyzing...' : 'Ask'}
      </button>
      
      {response && (
        <div>
          <h3>Response</h3>
          <p>{response.response}</p>
          <details>
            <summary>Metrics Context</summary>
            <pre>{JSON.stringify(response.metrics_context, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  );
}
```

### React Example with Multi-Turn Chat

```typescript
import { useState } from 'react';

export function MultiTurnChat({ tableData }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;

    // Add user message
    const updatedMessages = [
      ...messages,
      { role: 'user', content: input }
    ];
    setMessages(updatedMessages);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat/multi-turn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table_name: 'My Data',
          data: tableData,
          conversation: updatedMessages
        })
      });

      const data = await response.json();
      setMessages(data.conversation);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto' }}>
      <div style={{ height: '400px', overflow: 'auto', border: '1px solid #ccc', padding: '10px', marginBottom: '10px' }}>
        {messages.map((msg, idx) => (
          <div key={idx} style={{ marginBottom: '10px' }}>
            <strong>{msg.role === 'user' ? 'You' : 'AI'}:</strong>
            <p>{msg.content}</p>
          </div>
        ))}
      </div>

      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && handleSend()}
        placeholder="Ask a question..."
        style={{ width: '100%', padding: '10px', marginBottom: '10px' }}
      />
      <button onClick={handleSend} disabled={loading}>
        {loading ? 'Thinking...' : 'Send'}
      </button>
    </div>
  );
}
```

---

## 🔧 How It Works

### Flow Diagram

```
User Data (JSON)
    ↓
Parse & Convert to DataFrame
    ↓
Extract Metrics (totals, averages, etc.)
    ↓
Combine with User Question
    ↓
Send to Hugging Face Model
    ↓
Generate Intelligent Response
    ↓
Return to Frontend
    ↓
Display to User
```

### Models Used

1. **Text Summarization:** `facebook/bart-large-cnn`
   - Creates intelligent summaries
   - Fallback: `google/flan-t5-small`

2. **Text Generation:** `gpt2`
   - Answers questions
   - Falls back to rule-based if needed

3. **Fallback Logic:** Rule-based responses
   - When models aren't available
   - Pattern matching on questions

---

## 📊 Response Types

### Metric-Based Response
When asking about numbers:
```
Question: "What is the total sales?"
Response: "The total sales amount is 7500."
```

### Category-Based Response
When asking about categories:
```
Question: "Which product has the highest sales?"
Response: "Laptop is the top performing product with 5000 units in sales."
```

### Insight-Based Response
When asking for analysis:
```
Question: "What are the key insights?"
Response: "The dataset shows strong performance in electronics category, 
with Laptop being the leading product across all regions..."
```

### Fallback Response
When question doesn't match patterns:
```
Question: "Some random question?"
Response: "I analyzed the data. Could you be more specific? 
You can ask about total records, averages, top values, or categories."
```

---

## 🛠️ Setup Requirements

### Install Hugging Face
```bash
pip install transformers torch
```

### Update requirements.txt
```
transformers>=4.30.0
torch>=2.0.0
```

### Check Installation
```bash
python -c "from transformers import pipeline; print('✅ Hugging Face installed')"
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install transformers torch
```

### 2. Start Server
```bash
python -m uvicorn main:app --reload
```

### 3. Try in Browser
Open: `http://localhost:8000/docs`

Click "Try it out" on `/chat/analyze` endpoint.

### 4. Example Request
```json
{
  "table_name": "Test Data",
  "data": [
    {"item": "A", "value": 100},
    {"item": "B", "value": 200}
  ],
  "question": "What is the total value?"
}
```

---

## ⚙️ Configuration

### Model Selection (Advanced)

Edit `summary_utils.py` to use different models:

```python
# For better summarization (larger model)
cls._summarizer = pipeline(
    "summarization",
    model="facebook/bart-large-cnn"  # Better quality, slower
)

# For faster responses (lighter model)
cls._summarizer = pipeline(
    "text2text-generation",
    model="google/flan-t5-small"  # Faster, lighter
)
```

### GPU Support

If you have a GPU, Hugging Face will automatically use it:
```bash
# Check GPU usage
python -c "import torch; print(torch.cuda.is_available())"
```

---

## 🐛 Troubleshooting

### Issue: ModuleNotFoundError for transformers
**Solution:**
```bash
pip install transformers torch
```

### Issue: CUDA out of memory
**Solution:** Use smaller models:
```python
model="google/flan-t5-small"  # Instead of large models
```

### Issue: Slow responses
**Solution:** 
- First request loads the model (slow)
- Subsequent requests are faster
- Consider using lighter models

### Issue: No response generated
**Solution:** Falls back to rule-based response (still works!)

---

## 📈 Performance Tips

1. **First Call is Slower:** Models are loaded on first use
2. **Reuse Models:** Subsequent calls are much faster
3. **Batch Questions:** Group multiple questions for efficiency
4. **Use Multi-Turn:** Better context reuse in conversations

---

## 🎓 Examples

### Example 1: Sales Analysis
```json
{
  "table_name": "Q4 Sales",
  "data": [
    {"region": "North", "sales": 50000},
    {"region": "South", "sales": 35000},
    {"region": "East", "sales": 45000}
  ],
  "question": "Which region performed best?"
}
```

### Example 2: Product Performance
```json
{
  "table_name": "Products",
  "data": [
    {"name": "Laptop", "units": 500, "price": 1000},
    {"name": "Mouse", "units": 5000, "price": 50},
    {"name": "Monitor", "units": 1000, "price": 300}
  ],
  "question": "What is the total revenue?"
}
```

### Example 3: Multi-Turn Analysis
```json
{
  "table_name": "Inventory",
  "data": [...],
  "conversation": [
    {"role": "user", "content": "What's our inventory status?"},
    {"role": "assistant", "content": "You have 5000 units in stock."},
    {"role": "user", "content": "Is that enough for this month?"}
  ]
}
```

---

## 📚 API Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat/analyze` | POST | Single question analysis |
| `/chat/summary-hf` | POST | AI-powered summary |
| `/chat/multi-turn` | POST | Multi-turn conversation |
| `/chat/help` | GET | Get help and examples |

---

## ✨ Features

✅ AI-powered question answering
✅ Intelligent summary generation
✅ Multi-turn conversation support
✅ Context-aware responses
✅ Graceful fallback to rule-based responses
✅ GPU acceleration (if available)
✅ Lightweight model options
✅ Easy frontend integration

---

## 🔗 Related Documentation

- [SUMMARY_ENDPOINTS.md](SUMMARY_ENDPOINTS.md) - Summary generation
- [SUMMARY_INTEGRATION.md](SUMMARY_INTEGRATION.md) - Setup guide
- [QUICK_START.md](QUICK_START.md) - Quick reference

---

**Status: ✅ Ready to Use**

Start chatting with your data!
