from memory.vector_store import VectorStore


db = VectorStore()

docs = [

    "CNNs are widely used for biometric spoof detection.",

    "Vision Transformers improve fingerprint recognition.",

    "Diffusion models can synthesize spoof fingerprints.",

    "GANs generate realistic biometric attacks.",

]

db.add_documents(docs)

results = db.search(
    "fingerprint spoof detection"
)

print()

print("=" * 50)

for r in results:

    print(r)

    print("-" * 50)