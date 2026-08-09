"""Browser end-to-end QA: drive the real built frontend in Chromium against the
QA server (which serves both the static Next.js export and the API).

Usage:  python -m tests.qa.run_browser_qa [base_url] [screenshot_dir]
"""

import os
import re
import sys
import time

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
SHOTS = sys.argv[2] if len(sys.argv) > 2 else "/tmp/qa_shots"

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail and not ok else ""))


def main():
    from playwright.sync_api import sync_playwright

    os.makedirs(SHOTS, exist_ok=True)
    # Prefer a pre-installed Chromium (e.g. /opt/pw-browsers/chromium in CI
    # sandboxes) over downloading a matching browser build.
    exe = None
    candidate = os.getenv("QA_CHROMIUM", "/opt/pw-browsers/chromium")
    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        exe = candidate
    elif os.path.isdir(candidate):
        for sub in ("chrome-linux/chrome", "chrome"):
            p = os.path.join(candidate, sub)
            if os.path.isfile(p):
                exe = p
                break

    with sync_playwright() as pw:
        launch_kwargs = {"headless": True}
        if exe:
            launch_kwargs["executable_path"] = exe
        browser = pw.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        # Block external CDNs (fonts etc.): sandboxed QA environments have no
        # outbound internet, and those requests are not part of the app under test.
        page.route(re.compile(r"https?://(?!localhost|127\.0\.0\.1).*"), lambda route: route.abort())
        console_errors = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        # --- Load app ---
        page.goto(BASE, wait_until="networkidle", timeout=30000)
        page.screenshot(path=f"{SHOTS}/01-landing.png")

        # --- Consent dialog: tick the agreement checkbox, then start ---
        checkbox = page.get_by_role("checkbox")
        if checkbox.count():
            checkbox.first.click()
            page.wait_for_timeout(300)
        consent_btn = page.get_by_role("button",
                                       name=re.compile("start chatting|accept|agree|continue", re.I))
        if consent_btn.count():
            consent_btn.first.click()
            page.wait_for_timeout(800)
        check("app loads past consent", page.get_by_text("Welcome to Multilingual Climate chatbot!").count() > 0,
              "welcome header not found")
        page.screenshot(path=f"{SHOTS}/02-welcome.png")

        # --- Sample questions are the general set (not Thorncliffe) ---
        body_text = page.inner_text("body")
        check("sample questions are general (no Thorncliffe)",
              "Thorncliffe" not in body_text and "What are the local impacts of climate change in Toronto?" in body_text,
              f"body head: {body_text[:300]!r}")

        def send(msg, wait_ms=25000):
            box = page.get_by_placeholder("Ask about climate change...")
            box.fill(msg)
            box.press("Enter")
            # wait until loading spinner gone and a new assistant bubble appears
            page.wait_for_timeout(800)
            deadline = time.time() + wait_ms / 1000
            while time.time() < deadline:
                if page.locator("text=Thinking…").count() == 0 and page.locator(".message-bubble, [class*=message]").count():
                    break
                page.wait_for_timeout(300)
            page.wait_for_timeout(600)

        # --- Scenario 1: English question via sample chip ---
        page.get_by_role("button", name="What are the local impacts of climate change in Toronto?").click()
        page.wait_for_timeout(1000)
        for _ in range(60):
            if "Climate Guidance" in page.inner_text("body"):
                break
            page.wait_for_timeout(500)
        body_text = page.inner_text("body")
        check("English question renders a real answer",
              "Climate Guidance" in body_text and "What you can do" in body_text,
              f"body: {body_text[-400:]!r}")
        check("answer is not digits-only",
              bool(re.search(r"[A-Za-z]{20}", body_text.replace("\n", ""))) and not re.search(r"^\s*[\d\s.,:%\-]+\s*$", body_text))
        page.screenshot(path=f"{SHOTS}/03-english-answer.png", full_page=True)

        # --- Scenario 2: explicit Spanish request ---
        send("Write me a message in Spanish about flooding preparedness")
        for _ in range(60):
            if "Respuesta en español" in page.inner_text("body"):
                break
            page.wait_for_timeout(500)
        body_text = page.inner_text("body")
        check("'write me a message in Spanish' renders Spanish response",
              "[Respuesta en español]" in body_text, f"tail: {body_text[-400:]!r}")
        page.screenshot(path=f"{SHOTS}/04-spanish-request.png", full_page=True)

        # --- Scenario 3: greeting stays canned ---
        send("hello!")
        page.wait_for_timeout(1500)
        body_text = page.inner_text("body")
        check("greeting gets canned reply",
              "multilingual climate chatbot" in body_text.lower() or "climate questions" in body_text.lower(),
              f"tail: {body_text[-300:]!r}")
        page.screenshot(path=f"{SHOTS}/05-greeting.png", full_page=True)

        # --- Scenario 4: agentic location clarification. Fresh chat (the user
        # mentioned Toronto earlier in this session, which would legitimately
        # count as their location). "local flooding" is sent even with language
        # detection unavailable (the old client-side dead-end), and the bot
        # ASKS which community instead of guessing one; answering with a
        # community then yields a localized answer. ---
        new_chat = page.get_by_role("button", name=re.compile("new chat", re.I))
        if new_chat.count():
            new_chat.first.click()
            page.wait_for_timeout(600)
        page.route("**/api/v1/languages/validate", lambda route: route.abort())
        send("local flooding")
        for _ in range(60):
            t = page.inner_text("body")
            if "which city or neighbourhood" in t.lower() or "Climate Guidance" in t:
                break
            page.wait_for_timeout(500)
        page.unroute("**/api/v1/languages/validate")
        body_text = page.inner_text("body")
        check("'local flooding' reaches the bot and asks for the user's community",
              "can't detect your language" not in body_text
              and "which city or neighbourhood" in body_text.lower(),
              f"tail: {body_text[-300:]!r}")
        page.screenshot(path=f"{SHOTS}/06-clarify-location.png", full_page=True)

        send("I'm in Thorncliffe Park")
        for _ in range(60):
            t = page.inner_text("body")
            if "Thorncliffe Park Flood" in t or "Climate Guidance" in t:
                break
            page.wait_for_timeout(500)
        body_text = page.inner_text("body")
        check("community answer follows once the user says where they are",
              "Climate Guidance" in body_text and "Thorncliffe" in body_text,
              f"tail: {body_text[-300:]!r}")
        page.screenshot(path=f"{SHOTS}/07-localized-answer.png", full_page=True)

        # --- Scenario 5: citations UI present for RAG answers ---
        sources_btns = page.get_by_role("button", name=re.compile("source|citation", re.I))
        check("citations control appears for RAG answers", sources_btns.count() > 0 or "Sources" in body_text,
              "no sources/citations control found")

        # --- Console health (ignore blocked external CDN fetches) ---
        benign = [e for e in console_errors
                  if "favicon" not in e.lower() and "manifest" not in e.lower()
                  and "err_failed" not in e.lower() and "err_tunnel" not in e.lower()
                  and "failed to load resource: net::" not in e.lower()]
        check("no console/page errors during flows", not benign, "; ".join(benign[:5]))

        browser.close()

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\n=== Browser QA: {passed}/{len(RESULTS)} checks passed — screenshots in {SHOTS} ===")
    sys.exit(0 if passed == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
