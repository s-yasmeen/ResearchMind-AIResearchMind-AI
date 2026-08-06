from sentence_transformers import SentenceTransformer


class EmbeddingModel:

    _model = None

    def __init__(self):

        if EmbeddingModel._model is None:

            print("Loading embedding model...")

            EmbeddingModel._model = SentenceTransformer(
                "BAAI/bge-base-en-v1.5"
            )

        self.model = EmbeddingModel._model

    def encode(self, texts):

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        return embeddings.tolist()