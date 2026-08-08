# NIT Rourkela AI Assistant

A Retrieval-Augmented Generation (RAG) chatbot that answers student queries about NIT Rourkela using official college documents, with a live web search fallback for anything outside those documents.

## Why this exists

NIT Rourkela's information is scattered across 500+ webpages and over a thousand PDFs (circulars, fee structures, academic regulations, faculty pages, etc). Finding a specific answer means digging through the website manually. This project scrapes that content once, indexes it into a searchable vector database, and exposes it through a simple chat interface so students can just ask a question directly.

## Architecture

```
Sitemap.xml
    ↓
Scrape all pages (BeautifulSoup) → extract text + find document links
    ↓
Download all PDFs (filtered to nitrkl.ac.in domains only)
    ↓
Extract text from PDFs (PyPDFLoader)
    ↓
Chunk text (RecursiveCharacterTextSplitter, ~1000 chars, 150 overlap)
    ↓
Generate embeddings (local sentence-transformers model)
    ↓
Store in ChromaDB (vector database)
    ↓
LangChain agent with two tools:
  - search_college_docs → searches the vector database
  - web_search (Tavily) → searches the internet for anything not in the docs
    ↓
Streamlit chat interface
```

## Tech stack

- **LangChain** — agent orchestration and tool-calling
- **ChromaDB** — vector database
- **HuggingFace sentence-transformers** — local embeddings (`all-MiniLM-L6-v2`)
- **Google Gemini 2.5 Flash** — LLM for answer generation and tool selection
- **Tavily** — web search API for real-time/general queries
- **Streamlit** — chat UI
- **BeautifulSoup / Requests** — web scraping

## Project stats

- 520 pages scraped from the official sitemap
- 1,428 PDF documents discovered and downloaded
- 1,165 PDFs successfully parsed for text (263 were scanned images with no text layer — OCR not yet implemented)
- 27,734 text chunks generated and embedded

## Project structure

```
├── scrape_and_download.py   # scrapes sitemap pages, extracts doc links, downloads all PDFs
├── build_index.py           # loads PDFs, chunks text, generates embeddings, builds ChromaDB
├── app.py                   # Streamlit chat UI + LangChain agent
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

1. Clone the repo and install dependencies
```bash
git clone https://github.com/HayatTXT/NITRDocs.git
cd NITRDocs
pip install -r requirements.txt
```

2. Set up API keys
```bash
cp .env.example .env
```
Fill in your keys:
- `GOOGLE_API_KEY` — from [Google AI Studio](https://aistudio.google.com/apikey) (free tier)
- `TAVILY_API_KEY` — from [Tavily](https://tavily.com) (free tier)

3. Scrape and download source data
```bash
python scrape_and_download.py
```
This crawls the sitemap, scrapes every page, and downloads all discovered PDFs into `downloads/`. Takes roughly 30–45 minutes due to rate-limiting requests to be respectful to the server.

4. Build the vector index
```bash
python build_index.py
```
Extracts text from every PDF, chunks it, generates embeddings locally, and stores everything in `chroma_db/`. This step is CPU-bound and can take 20–30+ minutes depending on hardware.

5. Run the app
```bash
streamlit run app.py
```

## How the agent decides what to use

The agent is given two tools and a system prompt instructing it to always try the college document search first, and fall back to web search only when the answer isn't in the indexed documents (e.g. real-time information that are not yet updated on NIT Rourkela official website or any information related to NIT Rourkela but not listed in documents).

## Future improvements

- OCR fallback for scanned PDFs (pytesseract)
- Source citations shown in the UI alongside answers
- Multi-turn conversation memory
- Scheduled re-scraping to keep the index up to date
