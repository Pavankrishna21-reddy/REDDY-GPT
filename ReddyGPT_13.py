import streamlit as st
import threading
from duckduckgo_search import DDGS
from newspaper import Article
import requests
from bs4 import BeautifulSoup
import os
import uuid
import datetime

# Create chat history file if not exists
CHAT_HISTORY_FILE = "chat_history.txt"
if not os.path.exists(CHAT_HISTORY_FILE):
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        f.write("")

# Function to fetch top 5 search results from DuckDuckGo
def search_duckduckgo(query):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, region="in-en", safesearch="moderate", timelimit="d", max_results=5):
            results.append({
                "title": r.get("title"),
                "href": r.get("href"),
                "body": r.get("body")
            })
    return results

# Function to summarize content from a URL
def summarize_url(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        article.nlp()
        return article.summary
    except:
        try:
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraphs = soup.find_all('p')
            text = ' '.join([p.text for p in paragraphs[:5]])
            return text[:1000]
        except:
            return "Summary unavailable."

# Function to add to history
def save_to_history(user_input, response):
    with open(CHAT_HISTORY_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] User: {user_input}\n")
        f.write(f"[{timestamp}] ReddyGPT: {response}\n\n")

# Sidebar for chat history
with st.sidebar:
    st.markdown("### ☰ ReddyGPT Chat History")
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = f.read()
        st.text_area("Chat Log", history, height=300)
        if st.button("Clear History"):
            open(CHAT_HISTORY_FILE, "w").close()
            st.rerun()

# Page Setup
st.set_page_config(page_title="ReddyGPT", page_icon="🤖")
st.markdown("""
    <style>
    .stTextInput>div>div>input {
        font-size: 18px;
    }
    .voice-btn {
        position: absolute;
        right: 75px;
        top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🤖 ReddyGPT: Live Web Search + AI Response")

# User Input
user_input = st.text_input("Enter your query here:", "")

# Run search and show results
if user_input:
    st.markdown(f"### 🔍 Results for: `{user_input}`")
    results = search_duckduckgo(user_input)
    if results:
        for idx, res in enumerate(results):
            st.markdown(f"**{idx+1}. [{res['title']}]({res['href']})**")
            summary = summarize_url(res['href'])
            st.write(summary)
            st.markdown("---")
        save_to_history(user_input, results[0]['title'])
    else:
        st.warning("No search results found.")
        
        pyinstaller --onefile --noconsole ReddyGPT_13.py


