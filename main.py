import os
import sys
import webbrowser
import uvicorn
from dotenv import load_dotenv

# Ensure the root directory is on Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    load_dotenv()
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    browser_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    url = f"http://{browser_host}:{port}"
    print("=" * 65)
    print(" 🚀 PathPulse AI: Personalized Learning Roadmap Generator")
    print(f" 🌐 Web App URL : {url}")
    print(f" 📚 API Docs    : {url}/docs")
    print("=" * 65)

    # Automatically launch browser if not running in CI
    if not os.environ.get("NO_BROWSER"):
        try:
            webbrowser.open(url)
        except Exception:
            pass

    uvicorn.run("app.main:app", host=host, port=port, reload=False)
