from google import genai

client = genai.Client(api_key="NEW_KEY")

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Hello"
)

print(response.text)