from sentence_transformers import CrossEncoder


class Reranker:

    _model = None

    def __init__(self):

        if Reranker._model is None:

            print("Loading reranker...")

            Reranker._model = CrossEncoder(
                "cross-encoder/ms-marco-MiniLM-L-6-v2"
            )

        self.model = Reranker._model

    def rerank(self, query, docs):

        pairs = [
            (query, doc)
            for doc in docs
        ]

        scores = self.model.predict(pairs)

        ranked = sorted(
            zip(scores, docs),
            reverse=True
        )

        return [doc for _, doc in ranked]