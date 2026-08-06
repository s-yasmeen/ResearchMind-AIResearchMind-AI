import arxiv


class ArxivSearch:

    @staticmethod
    def search(query, max_results=5):

        print("Creating arxiv client...")

        client = arxiv.Client(
            page_size=max_results,
            delay_seconds=3,
            num_retries=2
        )

        print("Creating search query...")

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )

        papers = []

        print("Calling arxiv API...")

        for paper in client.results(search):

            print("Found:", paper.title)

            papers.append({
                "title": paper.title,
                "authors": ", ".join(a.name for a in paper.authors),
                "summary": paper.summary,
                "pdf_url": paper.pdf_url
            })

        print("Returning papers...")

        return papers