from memory.vector_store import VectorStore


class Retriever:

    @staticmethod
    def retrieve(query, k=8):

        store = VectorStore()

        return store.search(
            query=query,
            n_results=k
        )