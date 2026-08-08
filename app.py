import os
import streamlit as st
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

chroma_dir = "chroma_db"


def extract_text(content):
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)

    return str(content)


@st.cache_resource
def load_agent():
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    vectorstore = Chroma(
        persist_directory=chroma_dir,
        embedding_function=embedding
    )

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)

    web_search_tool = TavilySearch(max_results=3)

    @tool
    def search_college_docs(query: str) -> str:
        """Search NIT Rourkela official documents and website content for information
        about admissions, fees, hostel, library, academics, faculty, departments,
        circulars, and other college-specific matters. Use this FIRST for any
        question related to NIT Rourkela."""

        docs = vectorstore.similarity_search(query, k=4)
        if not docs:
            return "No relevant information found in college documents."

        formatted = []
        for doc in docs:
            formatted.append(f"[Source: {doc.metadata['source']}]\n{doc.page_content}")
        return "\n\n---\n\n".join(formatted)

    @tool
    def web_search(query: str) -> str:
        """Search the internet for real-time or general information NOT related
        to NIT Rourkela college documents - like current events, weather, general
        knowledge, or anything not found in college docs. Use this when
        search_college_docs doesn't have the answer."""

        results = web_search_tool.invoke(query)
        return str(results)

    tools = [search_college_docs, web_search]

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt="""You are a helpful assistant for NIT Rourkela students.
Use search_college_docs FIRST for any question about NIT Rourkela (admissions, fees, hostel,
library, academics, faculty, departments, circulars).
Use web_search only when you didn't find required information for the query from college documents or general/real-time information not related to college documents.
If a question has multiple parts, make sure to use all necessary tools to answer every part completely.
Answer clearly and concisely."""
    )

    return agent


st.set_page_config(page_title="NIT Rourkela Assistant", page_icon="🎓")

st.title("NIT Rourkela Assistant 🎓")
st.write("Ask me anything about NIT Rourkela - admission, hostel, library, academics, and more!")

with st.spinner("Loading assistant...."):
    agent = load_agent()

question = st.text_input("Your question:", placeholder="e.g. What are the library timings?")

if st.button("Ask") and question:
    with st.spinner("Thinking..."):
        answer = None
        last_error = None
        for attempt in range(2):
            try:
                response = agent.invoke({
                    "messages": [HumanMessage(content=question)]
                })
                answer = extract_text(response["messages"][-1].content)
                break
            except Exception as e:
                last_error = e

        if answer:
            st.markdown("### Answer")
            st.write(answer)
        else:
            st.error(f"Something went wrong, please try rephrasing your question. ({last_error})")

st.caption("Note: This assistant may occasionally provide incomplete or incorrect information. Always verify important details from official sources.")