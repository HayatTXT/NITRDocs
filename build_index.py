import os
import json
import time
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

downloads_dir = "downloads"
chunk_size = 1000
chunk_overlap = 150
batch_size = 500
persist_dir = "chroma_db"


def load_pdfs():
    all_docs = []
    failed_docs = []

    pdf_files = [f for f in os.listdir(downloads_dir) if f.lower().endswith(".pdf")]
    print("total pdfs:", len(pdf_files))

    start_time = time.time()

    for i, filesname in enumerate(pdf_files):
        filepath = os.path.join(downloads_dir, filesname)
        try:
            loader = PyPDFLoader(filepath)
            pages = loader.load()
            text = "\n".join(p.page_content for p in pages)

            if len(text.strip()) < 20:
                failed_docs.append(filesname)
                continue

            all_docs.append({"source": filesname, "text": text})

        except Exception:
            failed_docs.append(filesname)

        if i % 20 == 0:
            elapsed = time.time() - start_time
            print(f"progress: {i}/{len(pdf_files)} | elapsed: {elapsed:.1f}s | current file: {filesname}")

    print("done. loaded:", len(all_docs), "failed/empty:", len(failed_docs))

    with open("all_docs.json", "w", encoding="utf-8") as f:
        json.dump(all_docs, f, indent=2, ensure_ascii=False)

    with open("failed_docs.json", "w", encoding="utf-8") as f:
        json.dump(failed_docs, f, indent=2, ensure_ascii=False)

    return all_docs


def chunk_docs(all_docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    all_chunks = []
    chunk_id = 0

    for doc in all_docs:
        pieces = splitter.split_text(doc['text'])

        for piece in pieces:
            all_chunks.append({
                "chunk_id": chunk_id,
                "source": doc['source'],
                "text": piece
            })
            chunk_id += 1

    print("total chunks created:", len(all_chunks))

    with open("chunks.json", "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    return all_chunks


def embed_and_store(all_chunks):
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    all_documents = [
        Document(
            page_content=chunk['text'],
            metadata={"source": chunk['source'], "chunk_id": chunk['chunk_id']}
        )
        for chunk in all_chunks
    ]

    print("prepared", len(all_documents), "documents for embedding")

    start_time = time.time()

    vectorstore = Chroma.from_documents(
        documents=all_documents[:batch_size],
        embedding=embedding,
        persist_directory=persist_dir
    )

    print(f"batch 1 done. {batch_size}/{len(all_documents)} embedded. time: {time.time()-start_time:.1f}s")

    for i in range(batch_size, len(all_documents), batch_size):
        batch = all_documents[i:i + batch_size]
        vectorstore.add_documents(batch)

        elapsed = time.time() - start_time
        print(f"progress: {min(i+batch_size, len(all_documents))}/{len(all_documents)} | elapsed: {elapsed:.1f}s")

    print("all documents embedded and stored in chroma")
    return vectorstore


if __name__ == "__main__":
    docs = load_pdfs()
    chunks = chunk_docs(docs)
    embed_and_store(chunks)