import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")


client = OpenAI(
  api_key=api_key
)

response = client.responses.create(
  model="gpt-5.4-mini",
  input="write a haiku about ai",
  store=True,
)

print(response.output_text)

