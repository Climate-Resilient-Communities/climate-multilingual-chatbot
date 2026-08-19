# Embedding Dunia on the Ghost website

This folder contains the drop-in snippet that puts a Dunia chat bubble on the
Sprout (Climate Resilient Communities) Ghost site. Clicking the bubble opens
the full chat app — served by the Azure App Service deployment — inside an
iframe panel, so the website chat reuses everything that is already deployed
and tested.

```
Visitor on the Ghost site
        │  clicks the chat bubble
        ▼
Iframe loads https://climatechat-to.ca/   (Azure App Service)
        │  the app calls its own API on the same domain
        ▼
FastAPI backend → Bedrock / Cohere / Pinecone / Redis
```

Because the iframe loads the whole app from Azure, every API call happens
inside the iframe on the app's own domain. That means:

- **No CORS changes** — nothing to add to `CORS_ORIGINS`.
- **No secrets in the website** — all API keys stay on the server.
- **One deployment to maintain** — the widget always shows whatever is live.

## Two embed styles

| Style | File | Where it goes | What visitors see |
|---|---|---|---|
| **Floating bubble** (site-wide) | [`ghost-code-injection.html`](ghost-code-injection.html) | Ghost Admin → Settings → Code injection → **Site footer** | A "Chat with Dunia" pill + bubble in the corner of every page; clicking opens the chat panel |
| **Inline** (one page) | [`ghost-inline-embed.html`](ghost-inline-embed.html) | An **HTML card** inside a specific page or post | The full chat visible immediately on that page — no clicking. Ideal for a dedicated "Chat" page in the site menu |

They can be combined: the bubble site-wide plus a dedicated chat page.

## Installation — floating bubble

1. Open **Ghost Admin → Settings → Code injection**.
2. Paste the entire contents of [`ghost-code-injection.html`](ghost-code-injection.html)
   into the **Site footer** box.
3. Click **Save**. The bubble appears in the bottom-right corner of every page,
   with a "Chat with Dunia" label that hides after the chat is first opened
   (per browsing session).

## Installation — inline page

1. In Ghost Admin, edit the page (or create one, e.g. "Chat with Dunia").
2. Add an **HTML card** where the chat should appear and paste the contents of
   [`ghost-inline-embed.html`](ghost-inline-embed.html) into it.
3. Publish. The full chat renders right on the page.

The snippet is origin-agnostic: it works the same on
`climate-resilient-communities.ghost.io` and on any custom domain the site
uses, with no per-domain configuration.

To show the chat only on specific pages instead of site-wide, paste the
snippet into that page's own **Code injection** box (page settings → Code
injection) rather than the site-wide one.

## Configuration

Everything tweakable sits in the `Configuration` block at the top of the
script:

| Setting | Default | Purpose |
|---|---|---|
| `CHAT_URL` | `https://climatechat-to.ca/` | The deployed chat app the iframe loads. Switch to `https://climatereslianceapp.azurewebsites.net/` if the custom domain has DNS/binding issues. |
| `PANEL_TITLE` | `Dunia · Climate Chat` | Header text on the chat panel and the iframe's accessible title. |
| `BUTTON_LABEL` | `Chat with Dunia` | Screen-reader label and hover tooltip for the bubble. |
| `BRAND` / `BRAND_DARK` | `#099077` / `#077e69` | Bubble and header colors — matches the app's primary `hsl(169 88% 30%)`. |

## Behavior notes

- **Lazy loading.** The iframe is only created when a visitor hovers, focuses,
  or taps the bubble, so normal page views send zero traffic to the App
  Service. Hover also acts as a warm-up, so the chat is usually loaded by the
  time it is clicked. A spinner covers the panel until the app finishes
  loading (App Service cold starts can take a moment).
- **Responsive.** Desktop gets a 400×640 floating panel above the bubble;
  screens ≤640px wide get a full-screen chat with a close button in the
  header and safe-area padding for iOS.
- **Accessible.** The bubble is a real button with `aria-expanded`/
  `aria-controls`, the panel is a labeled dialog, Escape closes it, and focus
  returns to the bubble on close. Animations are disabled for
  `prefers-reduced-motion` users.
- **Theme-proof.** All ids are prefixed `dunia-chat-`, styles are injected
  under those ids only, and the widget sits at a very high `z-index`, so it
  neither inherits from nor leaks into the Ghost theme.

## Requirements on the app side (already true today)

- The backend must not send `X-Frame-Options` or a
  `Content-Security-Policy: frame-ancestors` header that excludes the website
  origin. The FastAPI app currently sends neither, so framing works as-is. If
  security headers are ever added, use
  `Content-Security-Policy: frame-ancestors 'self' https://climate-resilient-communities.ghost.io <custom website domain>`
  instead of `X-Frame-Options: DENY/SAMEORIGIN`.
- Leave the App Service **portal** CORS settings empty. They are not needed
  for the iframe approach, and enabling portal CORS would override the app's
  own environment-driven CORS middleware.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Panel stays on the spinner | App Service cold start (wait ~30s), or `CHAT_URL` is unreachable — check `https://climatechat-to.ca/health`, and fall back to the `azurewebsites.net` URL if DNS/binding is the issue. |
| Panel is blank/refused to connect | A frame-blocking header was added to the app — see the requirements section above. |
| Bubble doesn't appear | Snippet not saved in **Site footer** code injection, or an ad blocker stripped it; confirm the `<script>` shows up in the page source. |
| Chat errors under heavy shared traffic | Production rate limit is 20 chat requests/min per IP (`src/webui/api/main.py`); large NAT'd audiences (e.g. one office) can hit it. Raise the limit if this becomes real. |
