import streamlit as st
import openai
import os
from datetime import datetime
from PyPDF2 import PdfReader
import docx
import hashlib

# Configuration
class Config:
    CHAT_HISTORY_FILE = "reddy_gpt_global.db"
    DEFAULT_PROMPT = """You are ReddyGPT - a world-class AI assistant. Provide:
    1. Expert-level responses
    2. File analysis when documents are uploaded
    3. Fast, concise answers
    4. Proper formatting with markdown"""
    
    # Set your OpenAI API key via environment variable
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Core Engine
class ReddyGPT:
    def __init__(self):
        self.config = Config()
        self._init_db()
        openai.api_key = self.config.OPENAI_API_KEY

    def _init_db(self):
        if not os.path.exists(self.config.CHAT_HISTORY_FILE):
            with open(self.config.CHAT_HISTORY_FILE, "w") as f:
                f.write("")

    def analyze_file(self, file):
        """Extract text from various file formats"""
        try:
            if file.type == "application/pdf":
                reader = PdfReader(file)
                return "\n".join([page.extract_text() for page in reader.pages])
            elif file.type == "text/plain":
                return str(file.read(), "utf-8")
            elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                doc = docx.Document(file)
                return "\n".join([para.text for para in doc.paragraphs])
            else:
                return "Unsupported file format"
        except Exception as e:
            return f"File processing error: {str(e)}"

    def generate_response(self, user_input, file_content=None):
        messages = [
            {"role": "system", "content": self.config.DEFAULT_PROMPT},
            {"role": "user", "content": user_input}
        ]
        
        if file_content:
            messages.insert(1, {"role": "system", "content": f"Document content:\n{file_content}"})
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo-preview",  # Fastest high-quality model
                messages=messages,
                temperature=0.7,
                stream=True  # For real-time streaming
            )
            return self._stream_response(response)
        except Exception as e:
            return f"⚠️ Error: {str(e)}"

    def _stream_response(self, response):
        """Stream the response for better UX"""
        full_response = ""
        placeholder = st.empty()
        for chunk in response:
            if chunk.choices[0].delta.get("content"):
                full_response += chunk.choices[0].delta.content
                placeholder.markdown(full_response + "▌")
        placeholder.markdown(full_response)
        return full_response

# Streamlit UI
def main():
    st.set_page_config(page_title="ReddyGPT Pro", page_icon="🌍", layout="wide")
    
    # Initialize
    if 'reddy' not in st.session_state:
        st.session_state.reddy = ReddyGPT()
        st.session_state.messages = []
        st.session_state.file_content = None

    # Sidebar
    with st.sidebar:
        st.title("ReddyGPT Pro")
        st.markdown("""
        **World-class AI assistant**  
        - File upload support  
        - GPT-4 Turbo powered  
        - Real-time streaming  
        """)
        
        # File uploader
        uploaded_file = st.file_uploader(
            "📎 Upload PDF/TXT/DOCX",
            type=["pdf", "txt", "docx"],
            accept_multiple_files=False
        )
        
        if uploaded_file:
            with st.spinner("Analyzing file..."):
                st.session_state.file_content = st.session_state.reddy.analyze_file(uploaded_file)
                st.success(f"File processed: {uploaded_file.name}")

    # Main chat
    st.title("🌍 ReddyGPT Pro")
    st.caption("World-class AI with document analysis")

    # Display messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # User input
    if prompt := st.chat_input("Ask anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            response = st.session_state.reddy.generate_response(
                prompt,
                st.session_state.file_content
            )
            st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
