import streamlit as st
import speech_recognition as sr
from duckduckgo_search import DDGS
from newspaper import Article
import requests
from bs4 import BeautifulSoup
import os
import uuid
import datetime
from langdetect import detect

# Create chat history file if not exists
CHAT_HISTORY_FILE = "chat_history.txt"
if not os.path.exists(CHAT_HISTORY_FILE):
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        f.write("")

# Function to get voice input
def get_voice_input():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎤 Listening...")
        audio = recognizer.listen(source)
        try:
            query = recognizer.recognize_google(audio, language="en-IN")
            return query
        except sr.UnknownValueError:
            st.warning("❌ Could not understand the audio.")
        except sr.RequestError:
            st.error("🔌 Could not connect to Google Speech Recognition.")
    return ""

# Language check: only allow Telugu, Hindi, English
def is_supported_language(text):
    try:
        lang = detect(text)
        return lang in ["en", "hi", "te"]
    except:
        return False

# Fetch search results (top 5)
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

# Summarize from URL
def summarize_url(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        article.nlp()
        return article.summary
    except:
        try:
            res = requests.get(url, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            paras = soup.find_all('p')
            return ' '.join(p.text for p in paras[:5])[:1000]
        except:
            return "Summary not available."

# Save conversation
def save_to_history(user_input, response):
    with open(CHAT_HISTORY_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] User: {user_input}\n")
        f.write(f"[{timestamp}] ReddyGPT: {response}\n\n")

# Chat History Sidebar
with st.sidebar:
    st.markdown("### ☰ ReddyGPT Chat History")
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = f.read()
        st.text_area("Chat Log", history, height=300)
    if st.button("🧹 Clear History"):
        open(CHAT_HISTORY_FILE, "w").close()
        st.rerun()

# App Layout
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

st.title("🤖 ReddyGPT: Live Web Search + AI Summary")

col1, col2 = st.columns([9, 1])
with col1:
    user_input = st.text_input("Type your question:", "")
with col2:
    if st.button("🎙️", help="Voice Search"):
        user_input = get_voice_input()
        st.rerun()

# MAIN SEARCH SECTION
if user_input:
    if is_supported_language(user_input):
        st.markdown(f"### 🔍 Results for: `{user_input}`")
        results = search_duckduckgo(user_input)
        if results:
            for i, res in enumerate(results):
                st.markdown(f"**{i+1}. [{res['title']}]({res['href']})**")
                summary = summarize_url(res['href'])
                st.write(summary)
                st.markdown("---")
            save_to_history(user_input, results[0]['title'])
        else:
            st.warning("😕 No results found.")
    else:
        st.error("⚠️ Only Telugu, Hindi, and English are supported.")
