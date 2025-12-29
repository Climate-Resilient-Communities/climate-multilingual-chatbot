# Presentation Slides

This folder contains presentation materials for onboarding new team members.

---

## Available Presentations

### 1. Technical Overview
**File**: [01-overview-presentation.md](./01-overview-presentation.md)

**Audience**: All new team members

**Duration**: ~30 minutes

**Topics Covered**:
- Project overview and problem statement
- High-level architecture
- Technology stack
- RAG pipeline explanation
- Key components and files
- Getting started checklist

---

### 2. AI Concepts for Beginners
**File**: [02-ai-concepts-for-beginners.md](./02-ai-concepts-for-beginners.md)

**Audience**: Team members new to AI/ML

**Duration**: ~25 minutes

**Topics Covered**:
- What is AI and Machine Learning?
- What are Large Language Models (LLMs)?
- What is RAG?
- Embeddings and vector databases
- Semantic search and reranking
- Hallucination detection
- Complete pipeline walkthrough

---

## How to Use These Slides

### Option 1: Read as Markdown
Open the `.md` files directly in any text editor or GitHub.

### Option 2: Present with a Markdown Presenter
Use tools like:
- [Marp](https://marp.app/) - Markdown to slides
- [Slidev](https://sli.dev/) - Developer-friendly slides
- [reveal.js](https://revealjs.com/) - HTML presentation framework
- [Obsidian](https://obsidian.md/) - With slides plugin

### Option 3: Convert to PowerPoint/Google Slides
1. Copy each "Slide X" section
2. Paste into your presentation tool
3. Format as needed

---

## Slide Format

Each slide in our presentations follows this structure:

```markdown
# Slide N: Title

## Subtitle or Key Point

[Content - text, diagrams, or tables]

---
```

The `---` separator indicates a slide break.

---

## Recommended Presentation Order

### For Technical Onboarding (1 hour)

1. **Overview Presentation** (30 min)
   - Covers architecture, tech stack, key components

2. **AI Concepts for Beginners** (25 min)
   - If audience is new to AI/ML

3. **Live Demo** (5-10 min)
   - Show the chatbot in action
   - Walk through a query

### For Quick Intro (15 min)

Use just the following slides from **Overview Presentation**:
- Slide 1: Welcome
- Slide 2: Problem/Solution
- Slide 3: Architecture
- Slide 6: RAG Pipeline
- Slide 15: Key Files
- Slide 16: Getting Started

---

## Creating New Presentations

When adding new slides:

1. Follow the existing format:
```markdown
# Slide N: Title

## Subtitle

Content...

---
```

2. Use ASCII diagrams for architecture:
```
┌─────────┐     ┌─────────┐
│ Step 1  │────▶│ Step 2  │
└─────────┘     └─────────┘
```

3. Use tables for comparisons:
```markdown
| Feature | Description |
|---------|-------------|
| RAG | Retrieval-Augmented Generation |
```

4. Keep slides focused - one main idea per slide

5. Include practical examples and code references

---

## Additional Resources

- [Onboarding README](../README.md) - Complete onboarding guide
- [Architecture Diagrams](../diagrams/) - Visual system documentation
- [Component Guides](../components/) - Detailed component documentation

---

*These slides are part of the Climate Multilingual Chatbot onboarding materials.*
