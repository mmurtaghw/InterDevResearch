import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Define the API endpoint for the graph version
url = "http://127.0.0.1:5000/query_books_graph"
REQUIRED_API_KEY = os.getenv("REQUIRED_API_KEY")

# Define the request headers with authorization
headers = {
    "Authorization": f"Bearer {REQUIRED_API_KEY}",
    "Content-Type": "application/json"
}

# Define the request payload with a natural language query and n number of books
data = {
    "query": "Give gothic literature",
    "n": 10  
}

# Send the request
response = requests.post(url, json=data, headers=headers)

# Print the response status code and JSON output
print(response.status_code)
print(response.json())
