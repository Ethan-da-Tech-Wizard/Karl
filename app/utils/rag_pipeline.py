import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import fitz  # PyMuPDF
import docx

class RAGPipeline:
    def __init__(self, model_name='all-MiniLM-L6-v2', index_path="data/vector_db"):
        self.encoder = SentenceTransformer(model_name)
        self.index_path = index_path
        os.makedirs(self.index_path, exist_ok=True)
        
        self.dimension = self.encoder.get_embedding_dimension()
        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents = []  # Stores the text chunks corresponding to index positions
        
    def extract_text(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        text = ""
        try:
            if ext == '.pdf':
                doc = fitz.open(filepath)
                for page in doc:
                    text += page.get_text() + "\n"
            elif ext == '.docx':
                doc = docx.Document(filepath)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            else:
                # Default to text reader for .txt, .py, .md, .csv, etc.
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
        return text

    def chunk_text(self, text, chunk_size=200, overlap=50):
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks

    def ingest_file(self, filepath):
        print(f"Ingesting {filepath}...")
        text = self.extract_text(filepath)
        if not text.strip():
            return 0
            
        chunks = self.chunk_text(text)
        if not chunks:
            return 0
            
        embeddings = self.encoder.encode(chunks)
        self.index.add(np.array(embeddings).astype('float32'))
        self.documents.extend(chunks)
        return len(chunks)

    def retrieve(self, query, top_k=3):
        if self.index.ntotal == 0:
            return []
            
        query_vector = self.encoder.encode([query]).astype('float32')
        distances, indices = self.index.search(query_vector, min(top_k, self.index.ntotal))
        
        results = []
        for i in indices[0]:
            if i != -1 and i < len(self.documents):
                results.append(self.documents[i])
        return results
