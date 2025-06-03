Promptiv – README
=================

Promptiv is a SaaS prompt refinement tool that helps users unlock the full potential of AI by analyzing their input, rewriting it from multiple expert perspectives, and recommending the best large language model (LLM) for each task. Promptiv’s premium rewrites help users save time, increase clarity, and discover breakthrough solutions for both creative and analytical work.

---

Table of Contents
-----------------
1. Features
2. How It Works
3. Demo / Screenshot
4. Project Structure
5. Quickstart & Installation
6. Environment Variables
7. API Endpoints
8. Pricing Model
9. Contributing
10. License

---

1. Features
-----------
- **Intent Analysis:** Determines the user's real goal and clarifies ambiguous requests.
- **Three Expert Rewrites:** Each prompt is rebuilt as Concise, Analytical, and Creative.
- **Model Recommendation:** Suggests and links directly to the best LLM for your task (GPT-4o, Claude, Gemini, etc.).
- **Usage Logging:** Tracks prompt history, variants, tokens, and cost per use.
- **Dark Mode:** Built-in dark mode toggle for comfortable use.
- **No Ads, No Upsells:** Clean, focused UI for productivity.
- **Privacy-Focused:** No prompt data is shared with third parties outside LLM APIs.

---

2. How It Works
---------------
1. User enters a prompt on the main page.
2. Promptiv analyzes the intent and classifies the optimal task type.
3. The system generates three premium rewrites:
   - **Concise:** Direct, unambiguous, action-ready.
   - **Analytical:** Structured, step-by-step for clarity.
   - **Creative:** Unique perspectives, often unlocking new solutions.
4. For each variant, Promptiv recommends the best LLM and provides a direct link.
5. User can copy or open the new prompt in the recommended AI tool.

---

3. Demo / Screenshot
--------------------
*(Add screenshots of your UI here, e.g. `frontend/logo.png`, `frontend/index.html`)*

---

4. Project Structure
--------------------
prompt-fine-tuner/
│
├── backend/ # FastAPI server, API endpoints, prompt logic
│ ├── services/
│ ├── routers/
│ └── ...
├── frontend/ # HTML, CSS, JS, and static assets
│
├── static/ # Additional scripts, shared files
├── shared/ # Configs, shared code
├── tests/ # Test scripts
├── requirements.txt # Python dependencies
├── Dockerfile
├── .env.example
├── README.txt

---

5. Quickstart & Installation
----------------------------
1. **Clone the Repo:**
```
git clone https://github.com/YOUR_GITHUB_USERNAME/promptiv.git
cd promptiv
```

2. **Create a Python Virtual Environment:**
```
python3 -m venv venv
source venv/bin/activate
```

3. **Install Python Dependencies:**
```
pip install -r backend/requirements.txt
```

4. **Copy and Configure Environment Variables:**
```
cp .env.example .env
```

Edit `.env` and set your OpenAI/Supabase credentials

5. **Run the FastAPI Server:**
```
uvicorn backend.main:app --reload
```
By default runs at http://127.0.0.1:8000/

---

6. Environment Variables
------------------------
Edit your `.env` file with these values:

```
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=...
PREMIUM_FALLBACK_MODELS=gpt-4,gpt-3.5-turbo
USE_DUMMY_USER=true
PREMIUM_ENABLED=true
```

---

7. API Endpoints
-----------------
- `POST /api/rewrite` – Accepts a JSON body `{ "prompt": "Your text" }` and returns prompt variants.
- `GET /api/llm_count` – Returns count and list of supported LLMs.
- (Web frontend available at `/`)

---

8. Pricing Model
-----------------
- **Free Trial:** 1 use per visitor (not advertised on page)
- **Premium:** $4.99/month for 30 rewrites per month (see Pricing page for details)
- **Payment Processing:** Paddle (handles taxes, affiliates, and compliance)

---

9. Contributing
---------------
Pull requests and issues are welcome! Please:
- Open an issue to discuss changes or feature requests
- Fork the repository and submit a pull request
- Keep code style consistent with PEP8 and project structure

---

10. License
-----------
MIT License

---

Created by Adam Shonting  
[https://promptiv.io](https://promptiv.io)  
For support or questions: support@promptiv.io

