# Frontend (Next.js) Guide

This guide explains the frontend user interface of the Climate Multilingual Chatbot.

---

## What is the Frontend?

The **frontend** is what users see and interact with in their browser. It:
- Displays the chat interface
- Sends messages to the backend
- Shows responses with citations
- Handles language selection

**Technology**: [Next.js 14](https://nextjs.org/) with React 18 and TypeScript

**Location**: [`src/webui/app/`](../../src/webui/app/)

---

## Project Structure

```
src/webui/app/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── page.tsx           # Main chat page
│   │   ├── layout.tsx         # Root layout
│   │   ├── globals.css        # Global styles
│   │   └── languages.json     # Language list
│   │
│   ├── components/
│   │   ├── chat/              # Chat-specific components
│   │   │   ├── app-header.tsx
│   │   │   ├── chat-message.tsx
│   │   │   ├── chat-window.tsx
│   │   │   ├── citations-popover.tsx
│   │   │   ├── consent-dialog.tsx
│   │   │   └── export-button.tsx
│   │   │
│   │   └── ui/                # Reusable UI components
│   │       ├── button.tsx
│   │       ├── input.tsx
│   │       ├── dialog.tsx
│   │       └── ... (30+ components)
│   │
│   ├── hooks/                 # Custom React hooks
│   │   ├── use-toast.ts
│   │   └── use-mobile.tsx
│   │
│   └── lib/                   # Utilities
│       ├── api.ts             # API client
│       └── utils.ts           # Helper functions
│
├── public/                    # Static assets
├── package.json               # Dependencies
├── tailwind.config.ts         # Styling config
└── next.config.ts             # Next.js config
```

---

## Main Page Component

### page.tsx

**File**: [`src/webui/app/src/app/page.tsx`](../../src/webui/app/src/app/page.tsx)

This is the main chat interface. It manages:

1. **Message State**
```typescript
const [messages, setMessages] = useState<Message[]>([])
const [input, setInput] = useState('')
const [isLoading, setIsLoading] = useState(false)
```

2. **Language Selection**
```typescript
const [selectedLanguage, setSelectedLanguage] = useState('en')
```

3. **Sending Messages**
```typescript
const handleSendMessage = async () => {
  // 1. Add user message to UI
  // 2. Call API
  // 3. Add response to UI
  // 4. Handle citations
}
```

4. **Streaming Responses**
```typescript
const handleStreamingResponse = async () => {
  // Use EventSource for real-time updates
  // Update message as tokens arrive
}
```

---

## Key Components

### AppHeader

**File**: [`src/components/chat/app-header.tsx`](../../src/webui/app/src/components/chat/app-header.tsx)

The top bar with:
- Logo and title
- Language selector dropdown (180+ languages)
- New chat button
- Export button

```
┌────────────────────────────────────────────────────────────┐
│  🌍 Climate Chatbot    [English ▼]  [New Chat]  [Export]  │
└────────────────────────────────────────────────────────────┘
```

### ChatWindow

**File**: [`src/components/chat/chat-window.tsx`](../../src/webui/app/src/components/chat/chat-window.tsx)

Container for all messages with:
- Auto-scroll to latest message
- Loading indicators
- Empty state when no messages

### ChatMessage

**File**: [`src/components/chat/chat-message.tsx`](../../src/webui/app/src/components/chat/chat-message.tsx)

Individual message bubble showing:
- User or assistant role
- Message content (with Markdown support)
- Citations (if assistant)
- Feedback buttons (thumbs up/down)

```
┌──────────────────────────────────────────────────┐
│ 👤 You                                           │
│ What causes climate change?                      │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ 🤖 Climate Assistant                             │
│                                                  │
│ Climate change is primarily caused by...         │
│                                                  │
│ [1] IPCC Report  [2] NASA Climate               │
│                                                  │
│ [👍 Helpful]  [👎 Not Helpful]                  │
└──────────────────────────────────────────────────┘
```

### CitationsPopover / CitationsSheet

**Files**:
- [`src/components/chat/citations-popover.tsx`](../../src/webui/app/src/components/chat/citations-popover.tsx)
- [`src/components/chat/citations-sheet.tsx`](../../src/webui/app/src/components/chat/citations-sheet.tsx)

Shows citation details:
- Source title and URL
- Content snippet
- Click to open in new tab

### ConsentDialog

**File**: [`src/components/chat/consent-dialog.tsx`](../../src/webui/app/src/components/chat/consent-dialog.tsx)

Terms of service dialog that appears on first visit:
- Must accept before using chatbot
- Stored in cookies (30 days)

---

## API Client

**File**: [`src/webui/app/src/lib/api.ts`](../../src/webui/app/src/lib/api.ts)

Handles all communication with the backend:

```typescript
class ApiClient {
  // Send a chat message
  async sendChatQuery(
    query: string,
    language: string,
    history: ConversationMessage[]
  ): Promise<ChatResponse>

  // Stream a chat response (real-time)
  async streamChatQuery(
    query: string,
    language: string,
    history: ConversationMessage[],
    onToken: (token: string) => void
  ): Promise<void>

  // Submit feedback
  async submitFeedback(
    messageId: string,
    type: 'thumbs_up' | 'thumbs_down',
    categories: string[]
  ): Promise<FeedbackResponse>

  // Get supported languages
  async getSupportedLanguages(): Promise<SupportedLanguagesResponse>

  // Check/accept consent
  async checkConsent(): Promise<ConsentCheckResponse>
  async acceptConsent(): Promise<void>
}
```

---

## UI Component Library

We use [shadcn/ui](https://ui.shadcn.com/) components built on [Radix UI](https://www.radix-ui.com/):

| Component | File | Purpose |
|-----------|------|---------|
| Button | `ui/button.tsx` | Clickable actions |
| Input | `ui/input.tsx` | Text input |
| Textarea | `ui/textarea.tsx` | Multi-line input |
| Dialog | `ui/dialog.tsx` | Modal windows |
| Sheet | `ui/sheet.tsx` | Slide-out panels |
| Popover | `ui/popover.tsx` | Floating content |
| Select | `ui/select.tsx` | Dropdown selection |
| Toast | `ui/toast.tsx` | Notifications |

---

## Styling

We use [Tailwind CSS](https://tailwindcss.com/) for styling:

```tsx
<button className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded">
  Send Message
</button>
```

**Configuration**: [`tailwind.config.ts`](../../src/webui/app/tailwind.config.ts)

Key features:
- Dark mode support
- Custom color palette
- Responsive breakpoints
- Animation utilities

---

## State Management

The frontend uses React's built-in state management:

### Local State (useState)
```typescript
const [messages, setMessages] = useState<Message[]>([])
const [isLoading, setIsLoading] = useState(false)
```

### Message Type
```typescript
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  timestamp: Date
}
```

### Citation Type
```typescript
interface Citation {
  title: string
  url: string
  snippet: string
}
```

---

## Building for Production

### Development
```bash
cd src/webui/app
npm run dev      # Runs on port 9002
```

### Production Build
```bash
cd src/webui/app
npm run build    # Outputs to 'out/' directory
```

The production build creates static files that FastAPI serves.

---

## Key Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 15.3.3 | React framework |
| React | 18.3.1 | UI library |
| TypeScript | 5 | Type safety |
| Tailwind CSS | 3.4.1 | Styling |
| shadcn/ui | - | Component library |
| Radix UI | 1.2.x | Accessible primitives |
| React Markdown | 10.1.0 | Markdown rendering |

---

## Key Files Summary

| File | Purpose |
|------|---------|
| [`page.tsx`](../../src/webui/app/src/app/page.tsx) | Main chat interface |
| [`layout.tsx`](../../src/webui/app/src/app/layout.tsx) | Root HTML layout |
| [`api.ts`](../../src/webui/app/src/lib/api.ts) | Backend communication |
| [`globals.css`](../../src/webui/app/src/app/globals.css) | Global styles |
| [`languages.json`](../../src/webui/app/src/app/languages.json) | 183 language definitions |

---

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [shadcn/ui Documentation](https://ui.shadcn.com/)
