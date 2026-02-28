import requests
import os
from dotenv import load_dotenv

# Define the API endpoint
url = "http://127.0.0.1:5000/query_books"

load_dotenv()
# Define the API key (replace with your actual key)
REQUIRED_API_KEY = os.getenv("REQUIRED_API_KEY")

# Define the request headers with authorization
headers = {
    "Authorization": f"Bearer {REQUIRED_API_KEY}",
    "Content-Type": "application/json"
}

# Define the request payload
data = {"query": "Give me 19th century gothic books"}

# Send the request
response = requests.post(url, json=data, headers=headers)

print(response)

# Print the response
print(response.status_code, response.json())
