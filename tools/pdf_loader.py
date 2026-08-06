import fitz
from pathlib import Path


class PDFLoader:

    @staticmethod
    def load(pdf_path):

        print("Loading:", Path(pdf_path).name)

        doc = fitz.open(pdf_path)

        text = ""

        for page in doc:
            text += page.get_text()

        doc.close()

        return text

    @staticmethod
    def load_folder(folder):

        documents = []

        folder = Path(folder)

        for pdf in folder.glob("*.pdf"):

            text = PDFLoader.load(pdf)

            documents.append({
                "source": pdf.name,
                "text": text
            })

        return documents