import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

def initialize_triage_vector_store():
    pdf_path = "DringlichAI_Mock_Triage_Guide.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"Error: Could not find {pdf_path} in the directory!")
        return None

    print(f"Loading and chunking {pdf_path}...")
    
    # 1. Load your exact PDF
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    
    # 2. Split text into manageable chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    split_docs = text_splitter.split_documents(documents)
    
    # 3. Use your installed nomic-embed-text model for embeddings
    embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")
    
    # 4. Save into a local Chroma vector database
    vector_store = Chroma.from_documents(
        documents=split_docs,
        embedding=embeddings,
        persist_directory="./chroma_triage_db"
    )
    
    print("Vector store successfully created and persisted!")
    return vector_store

if __name__ == "__main__":
    initialize_triage_vector_store()