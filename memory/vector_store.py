import chromadb

from core.embeddings import EmbeddingModel


class VectorStore:

    def __init__(self):

        self.client = chromadb.PersistentClient(
            path="memory/chroma_db"
        )

        self.collection = self.client.get_or_create_collection(
            name="researchmind"
        )

        self.embedder = EmbeddingModel()

    def add_documents(self, chunks):

        if not chunks:
            return

        embeddings = self.embedder.encode(chunks)

        ids = [
            f"doc_{i}"
            for i in range(
                self.collection.count(),
                self.collection.count() + len(chunks)
            )
        ]

        self.collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings
        )

    def search(self, query, n_results=5):

        embedding = self.embedder.encode(query)

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results
        )

        return results["documents"][0]