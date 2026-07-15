# EthicAds Engine 
**Privacy-First Contextual Advertising Engine**

EthicAds is a privacy-safe, context-aware advertising alternative built for the modern web. Instead of tracking users across the internet with intrusive cookies and capturing personal identifiers, EthicAds relies entirely on the **immediate semantic context** of the active browser viewport. By matching webpage intent directly with sustainable product alternatives in real time, EthicAds aligns monetization with corporate sustainability and absolute user privacy.

---

##  Key Features

*   **Zero-Tracking Privacy:** Operates with absolute anonymity—no third-party tracking cookies, no cross-site profiling, and zero storage of behavioral history.
*   **Groq AI Intent Extraction:** Leverages `llama-3.1-8b-instant` via the Groq API to evaluate webpage text dynamically and classify content into broad, clean e-commerce intent categories within milliseconds.
*   **Dynamic Live Product Sync:** Queries live Amazon inventory via a secure RapidAPI integration to surface real, matching eco-friendly and sustainable products.
*   **Intelligent Semantic Cache:** Implements a thread-safe, in-memory SHA-256 caching layer to prevent duplicate external API calls, safeguarding API limits and maximizing response speed.
*   **Premium "Peek-a-boo" UI/UX:** Features a sleek Chrome Extension frontend with glassmorphic styling, non-intrusive slide animations, and a collapsible Floating Action Button (FAB) workflow that allows users to seamlessly show or minimize ad widgets.

---

## Tech Stack

*   **Frontend:** Vanilla JavaScript (Chrome Extension Architecture), HTML5, Tailwind-inspired inline CSS with frosted-glass filter effects.
*   **Backend Framework:** FastAPI (Asynchronous Python 3.11+)
*   **AI Inference:** Groq Cloud API (`Llama 3.1 8B`)
*   **Data Aggregation:** RapidAPI (Real-Time Amazon Product Data Engine)
*   **Resiliency & Security:** `Tenacity` (smart exponential retry back-offs) & `SlowAPI` (token-bucket rate limiting).
*   **Cloud Hosting:** Render (Automated Continuous Integration/Continuous Deployment from GitHub).

---

##  Project Architecture

```text
├── backend/
│   ├── main.py            # FastAPI Application initialization, routing, & WebSocket streams
│   ├── services.py        # Groq NLP processing, Semantic Cache, & RapidAPI integrations
│   ├── config.py          # Environment settings, telemetry levels, and logger config
│   ├── security.py        # Sanitization filters and API rate-limiting guardrails
│   └── requirements.txt   # Python core dependencies
└── extension/
    ├── manifest.json      # Chrome Extension configuration mapping
    └── content.js         # DOM viewport parsing, API transmission, and Peek-a-boo UI engine
🛠️ Local Setup & Installation
1. Backend Configuration
Navigate to your backend working directory, configure your virtual environment, and install dependencies:

Bash
# Clone the repository
git clone [https://github.com/yourusername/ethicads-engine.git](https://github.com/yourusername/ethicads-engine.git)
cd ethicads-engine/backend

# Install dependencies
pip install -r requirements.txt
Create a local environment profile or configure your hosting platform (e.g., Render) with the following environment variables:

Code snippet
GROQ_API_KEY=your_groq_api_token_here
RAPIDAPI_KEY=your_rapidapi_token_here
RAPIDAPI_HOST=real-time-amazon-data.p.rapidapi.com
Run the local development server:

Bash
uvicorn main:app --reload
2. Chrome Extension Installation
Open Google Chrome and navigate to chrome://extensions/.

Enable Developer mode using the toggle switch in the top-right corner.

Click the Load unpacked button in the top-left corner.

Select the extension/ directory containing your manifest.json and content.js files.

Ensure the WORKFLOW_URL within content.js points to your active server endpoint (Localhost or live Render instance).

🔄 Core Pipeline Workflow
Context Scraping: The content.js script safe-scrapes the text inside the user's active viewport and sends a sanitized, secure payload to the backend server.

Semantic Classification: The backend coordinates with the Groq intelligence layer to reduce raw web text down to a highly relevant, 1-to-2 word broad product segment.

Inventory Querying: The intent query passes through a thread-safe SemanticCache. If it's a new intent, it hits the live Amazon Product search framework to gather 3 matching sustainable items; otherwise, it returns the cached entries instantly.
<img width="1010" height="347" alt="image" src="https://github.com/user-attachments/assets/39c46a8b-1bb6-47b4-b003-5376db7afb2a" />

Interactive Rendering: The extension receives the product matches and injects a glassmorphic layout. The user retains absolute control to hide the widget down into a floating action button or open it back up at will.
