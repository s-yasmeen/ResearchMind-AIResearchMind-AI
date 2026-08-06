from tools.arxiv_search import ArxivSearch
from tools.pdf_downloader import PDFDownloader
from tools.pdf_loader import PDFLoader
from tools.text_chunker import TextChunker
from memory.vector_store import VectorStore


class ArxivIndexer:

    @staticmethod
    def index(query):

        papers = ArxivSearch.search(query, max_results=5)

        db = VectorStore()

        for paper in papers:

            filename = paper["title"].replace("/", "_") + ".pdf"

            pdf = PDFDownloader.download(
                paper["pdf_url"],
                filename
            )

            text = PDFLoader.load(pdf)

            chunks = TextChunker.chunk(text)

            db.add_documents(chunks)

            print("Indexed:", paper["title"])