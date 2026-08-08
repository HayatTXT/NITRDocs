# NIT Rourkela AI Assistant

RAG-based chatbot for NIT Rourkela students, built with LangChain, ChromaDB, and Gemini.

## Architecture
Sitemap -> Scrape pages -> Download PDFs -> Extract text -> Chunk -> Embed -> ChromaDB
-> LangChain agent (RAG tool + web search tool) -> Streamlit UI

## Setup
1. pip install -r requirements.txt
2. cp .env.example .env  (fill in your API keys)
3. python scrape_and_download.py
4. python build_index.py
5. streamlit run app.py

## Notes
- 1428 PDFs scraped, 1165 successfully text-extracted (263 were scanned images, no OCR yet)
- 27,734 chunks embedded using local sentence-transformers model