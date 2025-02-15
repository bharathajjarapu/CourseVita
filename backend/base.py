import os
from dotenv import load_dotenv
import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
import asyncio

# Load environment variables
load_dotenv()
api_key = os.getenv("API_KEY")

# Function to get text from PDF files
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

# Function to split text into manageable chunks
def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=5000, chunk_overlap=500)
    chunks = text_splitter.split_text(text)
    return chunks

# Function to create a vector store from text chunks
def create_vector_store(text_chunks):
    embeddings = FastEmbedEmbeddings()
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss")

# Function to load and configure the conversational chain
def get_conversational_chain():
    prompt_template = """
        You are FAQ Assistant.
        You will respond to the user's queries by leveraging the Context Provided.
        Context: {context}
        Question: {question}
        Answer:
    """

    # Ensure there is an event loop in the current thread
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    model = ChatOpenAI(
        model="llama-3.2-3b-preview",
        temperature=0.3,
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key
    )

    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

def user_input(user_question):
    embeddings = FastEmbedEmbeddings()

    if os.path.exists("faiss"):
        new_db = FAISS.load_local("faiss", embeddings, allow_dangerous_deserialization=True)
    else:
        pdf_files = [os.path.join("dataset", file) for file in os.listdir("dataset") if file.endswith(".pdf")]
        raw_text = get_pdf_text(pdf_files)
        text_chunks = get_text_chunks(raw_text)
        create_vector_store(text_chunks)
        new_db = FAISS.load_local("faiss", embeddings, allow_dangerous_deserialization=True)

    docs = new_db.similarity_search(user_question)
    chain = get_conversational_chain()

    response = chain({
        "input_documents": docs,
        "question": user_question
    }, return_only_outputs=True)

    return response["output_text"]


# Streamlit app interface
def main():
    st.set_page_config("FAQ", page_icon=":scales:")
    st.header("FAQ: AI Assistant :scales:")

    if "messages" not in st.session_state.keys():
        st.session_state.messages = [{"role": "assistant", "content": "Hi I'm FAQ Assistant."}]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    prompt = st.chat_input("Type your question here...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        if st.session_state.messages[-1]["role"] != "assistant":
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = user_input(prompt)
                    st.write(response)

            if response is not None:
                message = {"role": "assistant", "content": response}
                st.session_state.messages.append(message)

# Process PDF files and create vector store if not already available
def prepare_data():
    if not os.path.exists("faiss"):
        pdf_files = [os.path.join("dataset", file) for file in os.listdir("dataset") if file.endswith(".pdf")]
        raw_text = get_pdf_text(pdf_files)
        text_chunks = get_text_chunks(raw_text)
        create_vector_store(text_chunks)

if __name__ == "__main__":
    prepare_data()