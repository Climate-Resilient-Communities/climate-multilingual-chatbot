# **App Name**: ClimateTalk

## Core Features:

- Language Selection: Language selection dropdown in the header for multilingual support.
- Chat Interface: Main chat window for sending and receiving messages.
- New Conversation: A button to initiate new conversations
- User Settings: Settings/profile icon for user customization.
- Intelligent Responses: AI chatbot assistant which is tooled to provide climate change-related information and resources based on user queries, providing local resources links

## Style Guidelines:

- Primary green: #009376, evoking trust and stability. When hovering: #007e65
- Secondary green: #0a8f79 When hovering: #077966
- White: #ffffff
- Load Inter via a font link and set it globally.
- Replace emojis with a consistent icon set (e.g., Remix/Material or SVGs).
- Header containing a top bar with: “Multilingual Chatbot • Made by Climate Resilient Communities”, language select, “New chat” (clears chat_history), and “Settings” (opens a dialog)
- Subtle loader/progress component (spinner + progress bar).
- Add light CSS transitions for message bubbles on send/receive.
- Popup: Full-screen dialog gate shown before chat. Title “MLCC Climate Chatbot” with subtitle. One consent checkbox (“By checking this box, you agree to the following…”) that enables the “Start Chatting Now” button. Inside dropdowns (expanders):Privacy Policy: What’s (not) collected, data usage, protection, third‑party services, contact.Terms of Use: Acceptable use, MIT license note, IP, liability.Disclaimer: Informational purpose, accuracy caveats, third‑party content note.