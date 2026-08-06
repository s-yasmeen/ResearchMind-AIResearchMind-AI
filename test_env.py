import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GOOGLE_API_KEY")

print("Key loaded:", key is not None)

if key:
    print("First 10 chars:", key[:10])
    print("Length:", len(key))
else:
    print("No key found")