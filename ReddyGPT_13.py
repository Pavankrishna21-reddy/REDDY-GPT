import streamlit as st
from duckduckgo_search import AsyncDDGS
import openai
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime
import logging

# Configuration
load_dotenv()
logging.basicConfig(filename='reddygpt.log', level=logging.INFO)

class ReddyGPT:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        openai.api_key = self.api_key
        self.search_client = AsyncDDGS(timeout=15)
        self.conversation_log = "conversations.log"
        
        # Initialize session state
        if 'history' not in st.session_state:
            st.session_state.history = []

    async def _search_web(self, query):
        """Enhanced asynchronous web search with error handling"""
        try:
            results = []
            async for result in self.search_client.text(
                query,
                region="wt-wt",
                max_results=5,
                safesearch="Moderate"
            ):
                results.append({
                    'title': result.get('title', 'No title'),
                    'url': result.get('href', '#'),
                    'content': result.get('body', 'No content')[:500]  # Truncate long content
                })
            return results
        except Exception as e:
            logging.error(f"Search Error: {str(e)}")
            return []

    async def _generate_response(self, query, context=""):
        """Generate AI response with fallback logic"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are ReddyGPT, an advanced AI assistant. Follow these rules:
                    1. Provide accurate, concise responses
                    2. For Hyderabad-related queries, include local insights
                    3. Format lists with bullet points
                    4. Admit when you don't know something"""
                },
                {
                    "role": "user",
                    "content": f"Query: {query}\n\nContext:\n{context}"
                }
            ]
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-4-turbo-preview",  # Fastest model
                messages=messages,
                temperature=0.7,
                stream=True  # Enable streaming
            )
            
            # Stream the response
            full_response = ""
            placeholder = st.empty()
            async for chunk in response:
                if chunk.choices[0].delta.get("content"):
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
            
            return full_response
            
        except Exception as e:
            logging.error(f"API Error: {str(e)}")
            return "I'm experiencing technical difficulties. Please try again later."

    def _log_conversation(self, user_input, response):
        """Log conversation with timestamp"""
        with open(self.conversation_log, "a", encoding="utf-8") as f:
            log_entry = f"[{datetime.now()}] User: {user_input}\n"
            log_entry += f"[{datetime.now()}] Assistant: {response}\n\n"
            f.write(log_entry)

async def main():
    # Initialize app
    st.set_page_config(
        page_title="ReddyGPT Pro",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize chatbot
    if 'bot' not in st.session_state:
        st.session_state.bot = ReddyGPT()
    
    # Sidebar
    with st.sidebar:
        st.title("ReddyGPT Settings")
        st.markdown("---")
        st.markdown("**Current Features:**")
        st.markdown("- Web Search Integration")
        st.markdown("- Real-time Streaming")
        st.markdown("- Conversation Logging")
        
        if st.button("Clear Conversation"):
            st.session_state.history = []
            st.rerun()
        
        if os.path.exists("conversations.log"):
            with open("conversations.log", "r") as f:
                st.download_button(
                    "Download Full Log",
                    f.read(),
                    "reddygpt_conversations.log"
                )

    # Main interface
    st.title("🌍 ReddyGPT Pro")
    st.caption("Advanced AI Assistant with Web Search")
    
    # Display chat history
    for message in st.session_state.history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # User input
    if prompt := st.chat_input("Ask me anything..."):
        # Add user message to history
        st.session_state.history.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            # Step 1: Get search results
            search_results = await st.session_state.bot._search_web(prompt)
            context = "\n".join(
                f"• {res['title']}: {res['content']}\nSource: {res['url']}" 
                for res in search_results[:3]
            ) if search_results else ""
            
            # Step 2: Generate and stream response
            response = await st.session_state.bot._generate_response(prompt, context)
            
            # Update history and log
            st.session_state.history.append({"role": "assistant", "content": response})
            st.session_state.bot._log_conversation(prompt, response)

if __name__ == "__main__":
    asyncio.run(main())
