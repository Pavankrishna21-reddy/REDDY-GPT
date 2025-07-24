import os
import asyncio
import logging
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
import aiohttp
import openai
import streamlit as st
from duckduckgo_search import AsyncDDGS

# Initialize configuration
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reddygpt.log'),
        logging.StreamHandler()
    ]
)

class SearchEngine:
    def __init__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))

    async def _google_search(self, query: str) -> List[Dict]:
        """Google Custom Search API"""
        try:
            async with self.session.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    'key': os.getenv('GOOGLE_API_KEY'),
                    'cx': os.getenv('GOOGLE_CSE_ID'),
                    'q': query,
                    'num': 3
                }
            ) as response:
                data = await response.json()
                return [{
                    'title': item.get('title', 'No title'),
                    'url': item.get('link', '#'),
                    'content': item.get('snippet', ''),
                    'engine': 'google'
                } for item in data.get('items', [])]
        except Exception as e:
            logging.warning(f"Google search failed: {str(e)}")
            return []

    async def _ddg_search(self, query: str) -> List[Dict]:
        """DuckDuckGo Search"""
        try:
            async with AsyncDDGS() as ddgs:
                return [{
                    'title': r.get('title', ''),
                    'url': r.get('href', '#'),
                    'content': r.get('body', ''),
                    'engine': 'ddg'
                } async for r in ddgs.text(query, max_results=3)]
        except Exception as e:
            logging.warning(f"DuckDuckGo search failed: {str(e)}")
            return []

    async def search(self, query: str) -> List[Dict]:
        """Run all available searches"""
        results = []
        try:
            # Run searches in parallel
            google, ddg = await asyncio.gather(
                self._google_search(query),
                self._ddg_search(query)
            )
            results = google + ddg
            
            # Deduplicate by URL
            seen = set()
            return [r for r in results if not (r['url'] in seen or seen.add(r['url']))]
        except Exception as e:
            logging.error(f"Search failed: {str(e)}")
            return results

class ReddyGPT:
    def __init__(self):
        self.searcher = SearchEngine()
        self._init_openai()
        
    def _init_openai(self):
        """Validate OpenAI credentials"""
        if not os.getenv('OPENAI_API_KEY'):
            st.error("❌ Missing OpenAI API key in .env file")
            st.stop()
        openai.api_key = os.getenv('OPENAI_API_KEY')

    async def respond(self, query: str) -> str:
        """Generate AI response with search context"""
        try:
            # Get search results
            results = await self.searcher.search(query)
            context = "\n".join(
                f"• {r['title']}\n  {r['content']}\n  Source: {r['url']}"
                for r in results[:3]
            ) if results else "No search results found"

            # Stream response
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are ReddyGPT..."},
                    {"role": "user", "content": f"Query: {query}\nContext:\n{context}"}
                ],
                stream=True
            )
            
            full_response = ""
            placeholder = st.empty()
            async for chunk in response:
                if chunk.choices[0].delta.get("content"):
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response + "▌")
            return full_response

        except Exception as e:
            logging.error(f"Response failed: {str(e)}")
            return f"⚠️ Error: {str(e)}"

# Streamlit App
async def main():
    st.set_page_config(page_title="ReddyGPT", page_icon="🤖")
    
    if 'bot' not in st.session_state:
        st.session_state.bot = ReddyGPT()
        st.session_state.messages = []

    st.title("🐦‍🔥 ReddyGPT")
    
    # Display chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # User input
    if prompt := st.chat_input("Ask me anything"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                response = await st.session_state.bot.respond(prompt)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"System error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
