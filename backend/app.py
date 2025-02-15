import os
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()
api_key = os.getenv("API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuestionRequest(BaseModel):
    question: str

# Function to extract text from PDF files
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

# Function to split text into manageable chunks
def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=500)
    chunks = text_splitter.split_text(text)
    return chunks

# Function to create a vector store from text chunks
def create_vector_store(text_chunks):
    embeddings = FastEmbedEmbeddings()
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss")

# Function to initialize or load the vector store
def init_vector_store():
    embeddings = FastEmbedEmbeddings()
    if os.path.exists("faiss"):
        vector_store = FAISS.load_local("faiss", embeddings, allow_dangerous_deserialization=True)
    else:
        dataset_dir = "dataset"
        pdf_files = [
            os.path.join(dataset_dir, file)
            for file in os.listdir(dataset_dir)
            if file.endswith(".pdf")
        ]
        if not pdf_files:
            raise Exception("No PDF files found in the dataset directory.")
        raw_text = get_pdf_text(pdf_files)
        text_chunks = get_text_chunks(raw_text)
        create_vector_store(text_chunks)
        vector_store = FAISS.load_local("faiss", embeddings, allow_dangerous_deserialization=True)
    return vector_store

# Global variable to hold the vector store instance
vector_store = None

@app.on_event("startup")
async def startup_event():
    global vector_store
    try:
        vector_store = init_vector_store()
    except Exception as e:
        print(f"Error initializing vector store: {e}")

# Function to set up the conversational chain
def get_conversational_chain():
    prompt_template = """
    You are Coursevita FAQ Assistant.
    Do not provide any other answer unrelated to Coursevita.
    You will respond to the user's queries by leveraging the Context Provided.
    Context: {context}
    Question: {question}
    Answer:
    """
    # Ensure an event loop is available
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    model = ChatOpenAI(
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key
    )
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

# Function for processing user input and generating an answer
def user_input(user_question: str):
    global vector_store
    embeddings = FastEmbedEmbeddings()
    if vector_store is None:
        vector_store = init_vector_store()
    docs = vector_store.similarity_search(user_question)
    chain = get_conversational_chain()
    response = chain({
        "input_documents": docs,
        "question": user_question
    }, return_only_outputs=True)
    return response["output_text"]

# API endpoint to ask a question
@app.post("/ask")
async def ask_question(request: QuestionRequest):
    try:
        answer = user_input(request.question)
        return {"answer": answer}
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)