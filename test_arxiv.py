import arxiv

print("Starting search")

client = arxiv.Client(
    page_size=2,
    delay_seconds=3,
    num_retries=2
)

search = arxiv.Search(
    query="biometric spoofing",
    max_results=2,
    sort_by=arxiv.SortCriterion.SubmittedDate
)

print("Searching arXiv...")

count = 0

for paper in client.results(search):
    count += 1
    print("\n-------------------------")
    print("Title:", paper.title)
    print("Authors:", [a.name for a in paper.authors])
    print("PDF:", paper.pdf_url)

print("\nTotal papers:", count)
print("Finished")
