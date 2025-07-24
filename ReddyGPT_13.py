import os
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
import aiohttp
import openai
import streamlit as st
from duckduckgo_search import AsyncDDGS

# Configuration
load_dotenv()
logging.basicConfig(
    filename='reddygpt.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SearchEngine:
    """Unified search interface for multiple engines"""
    def __init__(self):
        self.engines = {
            'google': self._google_search,
            'serpapi': self._serpapi_search,
            'duckduckgo': self._duckduckgo_search
        }
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

    async def _google_search(self, query: str) -> List[Dict]:
        """Google Custom Search JSON API"""
        params = {
            'key': os.getenv('GOOGLE_API_KEY'),
            'cx': os.getenv('GOOGLE_CSE_ID'),
            'q': query,
            'num': 5
        }
        try:
            async with self.session.get(
                "https://www.googleapis.com/customsearch/v1",
                params=params
            ) as response:
                data = await response.json()
                return [{
                    'title': item['title'],
                    'url': item['link'],
                    'snippet': item.get('snippet', ''),
                    'engine': 'google'
                } for item in data.get('items', [])]
        except Exception as e:
            logging.error(f"Google search error: {str(e)}")
            return []

    async def _serpapi_search(self, query: str) -> List[Dict]:
        """SERP API Search"""
        params = {
            'api_key': os.getenv('SERPAPI_KEY'),
            'q': query,
            'engine': 'google',
            'num': 5
        }
        try:
            async with self.session.get(
                "https://serpapi.com/search.json",
                params=params
            ) as response:
                data = await response.json()
                return [{
                    'title': item.get('title'),
                    'url': item.get('link'),
                    'snippet': item.get('snippet', ''),
                    'engine': 'serpapi'
                } for item in data.get('organic_results', [])]
        except Exception as e:
            logging.error(f"SERPAPI error: {str(e)}")
            return []

    async def _duckduckgo_search(self, query: str) -> List[Dict]:
        """DuckDuckGo Search"""
        try:
            async with AsyncDDGS() as ddgs:
                return [{
                    'title': r.get('title', ''),
                    'url': r.get('href', '#'),
                    'snippet': r.get('body', ''),
                    'engine': 'duckduckgo'
                } async for r in ddgs.text(query, max_results=5)]
        except Exception as e:
            logging.error(f"DuckDuckGo error: {str(e)}")
            return []

    async def search(self, query: str) -> List[Dict]:
        """Execute parallel searches with fallback"""
        tasks = [engine(query) for engine in self.engines.values()]
        results = await asyncio.gather(*tasks)
        
        # Deduplicate results by URL
        seen_urls = set()
        deduped = []
        for engine_results in results:
            for item in engine_results:
                if item['url'] not in seen_urls:
                    deduped.append(item)
                    seen_urls.add(item['url'])
        return deduped[:10]  # Return top 10 unique results

class ReddyGPT:
    def __init__(self):
        self.search_engine = SearchEngine()
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.conversation_log = "conversations.log"

    async def generate_response(self, query: str) -> str:
        """Generate response with search context"""
        try:
            # Get search results (all engines in parallel)
            search_results = await self.search_engine.search(query)
            
            # Prepare context
            context = "\n".join(
                f"🔍 [{res['engine'].upper()}] {res['title']}\n"
                f"   {res['snippet']}\n"
                f"   Source: {res['url']}\n"
                for res in search_results[:5]  # Top 5 results
            ) if search_results else "No search results found"

            # Generate AI response
            messages = [
                {
                    "role": "system",
                    "content": """You are ReddyGPT, an advanced AI assistant. Rules:
1. Provide accurate, concise responses
2. Cite sources when available
3. For Hyderabad queries, include local insights
4. Format lists clearly"""
                },
                {
                    "role": "user", 
                    "content": f"Query: {query}\n\nSearch Results:\n{context}"
                }
            ]

            response = await openai.ChatCompletion.acreate(
                model="gpt-4-turbo-preview",
                messages=messages,
                temperature=0.7,
                stream=True
            )

            # Stream response
            full_response = ""
            placeholder = st.empty()
            async for chunk in response:
                if chunk.choices[0].delta.get("content"):
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
            
            return full_response

        except Exception as e:
            logging.error(f"Response error: {str(e)}")
            return "⚠️ I encountered an error. Please try again later."

    def log_conversation(self, user_input: str, response: str):
        """Log conversation with timestamp"""
        with open(self.conversation_log, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] USER: {user_input}\n")
            f.write(f"[{datetime.now()}] ASSISTANT: {response}\n\n")

# Streamlit UI
async def main():
    st.set_page_config(
        page_title="ReddyGPT Pro",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session
    if 'bot' not in st.session_state:
        st.session_state.bot = ReddyGPT()
        st.session_state.messages = []

    # Sidebar
    with st.sidebar:
        st.title("🔧 Control Panel")
        st.markdown("**Active Search Engines:**")
        st.checkbox("Google", value=True, key="use_google")
        st.checkbox("SERPAPI", value=True, key="use_serpapi")
        st.checkbox("DuckDuckGo", value=True, key="use_duckduckgo")
        
        if st.button("Clear Conversation"):
            st.session_state.messages = []
            st.rerun()

    # Main interface
    st.title("🌐 ReddyGPT Pro")
    st.caption("Multi-Search AI Assistant")

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input
    if prompt := st.chat_input("Ask me anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = await st.session_state.bot.generate_response(prompt)
            st.session_state.bot.log_conversation(prompt, response)
            st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    asyncio.run(main())
