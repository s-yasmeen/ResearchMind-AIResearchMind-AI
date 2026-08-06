from rank_bm25 import BM25Okapi


class BM25Retriever:

    def __init__(self, documents):

        self.documents = documents

        tokenized = [
            doc.lower().split()
            for doc in documents
        ]

        self.bm25 = BM25Okapi(tokenized)

    def search(self, query, k=5):

        scores = self.bm25.get_scores(
            query.lower().split()
        )

        ranked = sorted(
            zip(scores, self.documents),
            reverse=True
        )

        return [doc for _, doc in ranked[:k]]