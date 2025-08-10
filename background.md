# Background image for Streamlit chat apps that works in light and dark mode

## TL;DR
- Use **AVIF** or **WebP** for the background image, with an automatic **JPEG fallback**. Serve from `./static` so the browser can cache it.
- Paint the image with a **fixed, non-interactive pseudo-element** and add a **theme-aware scrim**. This avoids layout quirks and keeps text readable.
- Detect the user’s theme with CSS media queries and adjust overlay strength. Keep contrast to **WCAG AA (4.5:1)** for body text.
- Avoid `background-attachment: fixed` on iOS Safari. Use a **fixed-position ::before layer** instead.

---
## 1) Image format and delivery
**Goal:** high quality, small bytes, broad compatibility.

- Preferred formats: **AVIF** first, **WebP** second, then **JPEG** as the last fallback.
- If you need transparency, use **PNG** sparingly.
- Serve files via Streamlit **static file serving** so they’re cacheable by the browser.

**Enable static files**  
`.streamlit/config.toml`:
```toml
[server]
enableStaticServing = true
```

**Put images here**  
```
your_app/
├─ app.py
├─ static/
│  ├─ bg.avif
│  ├─ bg.webp
│  └─ bg.jpg
└─ .streamlit/
   └─ config.toml
```

---
## 2) Safe background layer (no theme collisions)
Attach a read-only, fixed background using `::before` on `.stApp`. This avoids z-index and scrolling issues inside Streamlit widgets.

```python
import streamlit as st


def set_background():
    st.markdown(
        """
        <style>
        /* Root theme variables you can reuse across components */
        :root {
          --mlcc-scrim-light: rgba(255,255,255,0.70);
          --mlcc-scrim-dark:  rgba(0,0,0,0.45);
        }

        /* 1) Paint an image-only layer that never intercepts clicks */
        .stApp::before {
          content: "";
          position: fixed;
          inset: 0;
          pointer-events: none;
          z-index: 0;

          /* Prefer modern formats with fallback via image-set; center + cover */
          background-image: image-set(
            url("app/static/bg.avif") type("image/avif"),
            url("app/static/bg.webp") type("image/webp"),
            url("app/static/bg.jpg") type("image/jpeg")
          );
          background-position: center center;
          background-repeat: no-repeat;
          background-size: cover;
        }

        /* 2) Add a theme-aware scrim so foreground text remains readable */
        /* Default to light */
        .stApp::after {
          content: "";
          position: fixed;
          inset: 0;
          pointer-events: none;
          z-index: 0;
          background: var(--mlcc-scrim-light);
        }

        /* Respect the user's theme */
        @media (prefers-color-scheme: dark) {
          .stApp::after { background: var(--mlcc-scrim-dark); }
        }

        /* Streamlit content should be above the background layers */
        .stApp > div, .main, .block-container { position: relative; z-index: 1; }
        </style>
        """,
        unsafe_allow_html=True,
    )
```

Notes:
- `image-set()` lets the browser pick the best supported format. The path prefix `app/static/...` is how Streamlit exposes files from `./static` when static serving is enabled.
- We avoid `background-attachment: fixed` since iOS Safari has known issues. The fixed `::before` layer gives the same visual effect without the bug.

---
## 3) Theme-aware readability
Even with a scrim, keep a high contrast ratio between text and the composite background. Practical rules:
- Body text contrast should meet **WCAG 2.1 AA**: **4.5:1**.
- Increase the scrim opacity when your background is busy. Typical starting points:
  - Light theme: `rgba(255,255,255,0.70)`
  - Dark theme:  `rgba(0,0,0,0.45)`

If you want slightly stronger dark-mode protection:
```css
@media (prefers-color-scheme: dark) {
  .stApp::after { background: rgba(0,0,0,0.55); }
}
```

---
## 4) Keep chat text readable
If your chat bubbles are fully transparent, text can lose contrast over photos. Give bubbles a minimal surface color that adapts to theme.

```python
st.markdown(
    """
    <style>
    /* Assistant bubble */
    [data-testid="stChatMessage"]:not(:has([data-testid="user-avatar"])) > div {
      background: rgba(255,255,255,0.82);
      color: #111;
      border-radius: 12px;
    }
    @media (prefers-color-scheme: dark) {
      [data-testid="stChatMessage"]:not(:has([data-testid="user-avatar"])) > div {
        background: rgba(0,0,0,0.35);
        color: #f5f5f5;
      }
    }

    /* User bubble example */
    [data-testid="stChatMessage"]:has([data-testid="user-avatar"]) > div {
      background: rgba(0,147,118,0.12);
      color: #111;
    }
    @media (prefers-color-scheme: dark) {
      [data-testid="stChatMessage"]:has([data-testid="user-avatar"]) > div {
        background: rgba(10,143,121,0.20);
        color: #eaeaea;
      }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
```

If you prefer to keep bubbles transparent, bump the scrim opacity in §3 until contrast passes AA.

---
## 5) iOS Safari specifics
- Avoid `background-attachment: fixed`. It is unreliable on iOS Safari.
- The `::before` fixed layer above works across browsers without those issues.
- If you still see jank on mobile, try `background-attachment: scroll` on very old devices and rely on the fixed `::before` position for stability.

```css
/* Only if you ever fall back to background-attachment */
.stApp { background-attachment: scroll; }
```

---
## 6) File sizes that feel snappy
- Export the background at **1920×1080** or **2560×1440** depending on your audience. Use a separate **mobile-optimized** version if needed.
- Target sizes:
  - AVIF: 150–350 KB
  - WebP: 250–500 KB
  - JPEG: 400–900 KB
- Avoid base64-embedding large images. Inline data URIs are not cache-friendly and bloat HTML. Serve static files instead.

Optional: If you have a huge image, consider a tiny blurred placeholder first, then swap to the full image once the app renders.

---
## 7) Drop-in helper for your app
```python
def install_background():
    set_background()  # from §2
    # Add any bubble styles from §4 here as well
```

Call `install_background()` once after `st.set_page_config(...)`.

---
## 8) Quick checklist
- [ ] Place images in `./static` and enable static serving.
- [ ] Provide AVIF, WebP, and JPEG in `image-set()` order.
- [ ] Paint the image with `.stApp::before`, scrim with `.stApp::after`.
- [ ] Use `@media (prefers-color-scheme: dark)` to flip scrim.
- [ ] Verify AA contrast. If low, increase scrim or bubble background.
- [ ] Test on iOS Safari, Android Chrome, desktop Safari, Chrome, Firefox, Edge.

---
## Notes for your current code
- You already have a helper to base64-embed an image. Keep it for small icons and favicons. For the full-page background, prefer the static file path and `image-set()` so browsers can cache and choose the best format.
- Your current background uses `opacity: 0.1` on a tiled PNG. Replace it with the layered approach above. It is more robust with dark and light themes and reads better in all browsers.

---
## References used for these choices
- Streamlit static file serving and configuration
- Streamlit theming overview and theme keys
- CSS `prefers-color-scheme`, `image-set()`, and background properties
- WCAG 2.1 contrast ratios and AA guidelines


---

## 9) Optional: read the theme in Python (Streamlit 1.46+)
If you prefer to branch styles from Python instead of pure CSS, Streamlit 1.46+ exposes the active theme via `st.context.theme`.

```python
import streamlit as st

def current_theme_type(default="light"):
    # Returns "light" or "dark" on 1.46+, else the default
    try:
        return getattr(getattr(st, "context", None), "theme", {}).get("type", default)
    except Exception:
        return default

theme_type = current_theme_type()
st.write(f"Current theme: {theme_type}")
```
