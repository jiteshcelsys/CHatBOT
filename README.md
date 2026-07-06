## Document-Based Question Answering

This application allows users to upload one or more documents and ask questions based on their contents. The system uses a **Vector Database** to enable efficient semantic search and retrieval.

### How It Works

1. **Document Upload**
   - Users upload supported document formats (e.g., PDF, DOCX, TXT).

2. **Text Processing**
   - The document is divided into smaller chunks for better retrieval.

3. **Embedding Generation**
   - Each text chunk is converted into vector embeddings using an embedding model.

4. **Vector Database Storage**
   - The generated embeddings are stored in a vector database for fast similarity search.

5. **Question Answering**
   - When a user asks a question, the query is converted into an embedding.
   - The vector database retrieves the most relevant document chunks based on semantic similarity.
   - These retrieved chunks are provided as context to the Large Language Model (LLM), which generates an accurate answer grounded in the uploaded document.

### Key Features

- Upload and process documents.
- Semantic search using vector embeddings.
- Context-aware question answering.
- Answers are generated based only on the uploaded document content, minimizing hallucinations.
- Efficient retrieval using a vector database.
