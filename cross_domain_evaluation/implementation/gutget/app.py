import os
from flask import Flask, request, jsonify, abort
from dotenv import load_dotenv
from openai import OpenAI
import requests
import string
from urllib.parse import parse_qsl

# Load environment variables from the .env file
load_dotenv()

app = Flask(__name__)

# Retrieve API keys from environment variables
REQUIRED_API_KEY = os.getenv("REQUIRED_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GUTENDEX_URL = "https://gutendex.com/books"

# Initialize the OpenAI client using the new library format.
client = OpenAI(api_key=OPENAI_API_KEY)

@app.route("/query_books", methods=["POST"])
def query_books():
    data = request.get_json()
    if not data or "query" not in data:
        abort(400, description="Bad Request: No query parameter provided")

    api_key = request.headers.get("Authorization")
    if not api_key or api_key != f"Bearer {REQUIRED_API_KEY}":
        abort(401, description="Unauthorized: Invalid or missing API key")
    
    user_query = data["query"]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You are a helpful librarian assistant that is designed to assist users with finding, "
                            "discovering and exploring books on Project Gutenberg by making API requests to the gutindex API. "
                            "Below is the documentation required to use this API. Make your best judgement as to the query required "
                            "in order to return the most appropriate books. Only provide the API request and nothing else. Unless asked otherwise, provide books only in english. \n\n"
                            "Lists of Books\n"
                            "Lists of book information in the database are queried using the API at /books (e.g. gutendex.com/books). "
                            "Book data will be returned in the format\n\n"
                            "{\n  \"count\": <number>,\n  \"next\": <string or null>,\n  \"previous\": <string or null>,\n  "
                            "\"results\": <array of Books>\n}\n"
                            "where results is an array of 0-32 book objects, next and previous are URLs to the next and previous pages of results, "
                            "and count in the total number of books for the query on all pages combined.\n\n"
                            "By default, books are ordered by popularity, determined by their numbers of downloads from Project Gutenberg.\n\n"
                            "Parameters can also be added to book-list queries in a typical URL format. For example, to get the first page of written by authors alive after 1899 "
                            "and published in English or French, you can go to /books?author_year_start=1900&languages=en,fr\n\n"
                            "You can find available query parameters below.\n\n"
                            "author_year_start and author_year_end\n"
                            "Use these to find books with at least one author alive in a given range of years. They must have positive or negative integer values. "
                            "For example, /books?author_year_end=-499 gives books with authors alive before 500 BCE, and /books?author_year_start=1800&author_year_end=1899 gives books with authors alive in the 19th Century.\n\n"
                            "copyright\n"
                            "Use this to find books with a certain copyright status: true for books with existing copyrights, false for books in the public domain in the USA, "
                            "or null for books with no available copyright information. These can be combined with commas. For example, /books?copyright=true,false gives books with available copyright information.\n\n"
                            "ids\n"
                            "Use this to list books with Project Gutenberg ID numbers in a given list of numbers. They must be comma-separated positive integers. "
                            "For example, /books?ids=11,12,13 gives books with ID numbers 11, 12, and 13.\n\n"
                            "languages\n"
                            "Use this to find books in any of a list of languages. They must be comma-separated, two-character language codes. "
                            "For example, /books?languages=en gives books in English, and /books?languages=fr,fi gives books in either French or Finnish or both.\n\n"
                            "mime_type\n"
                            "Use this to find books with a given MIME type. Gutendex gives every book with a MIME type starting with the value. "
                            "For example, /books?mime_type=text%2F gives books with types text/html, text/plain; charset=us-ascii, etc.; and /books?mime_type=text%2Fhtml gives books with types text/html, text/html; charset=utf-8, etc.\n\n"
                            "search\n"
                            "Use this to search author names and book titles with given words. They must be separated by a space (i.e. %20 in URL-encoded format) and are case-insensitive. "
                            "For example, /books?search=dickens%20great includes Great Expectations by Charles Dickens.\n\n"
                            "sort\n"
                            "Use this to sort books: ascending for Project Gutenberg ID numbers from lowest to highest, descending for IDs highest to lowest, or popular (the default) for most popular to least popular by number of downloads.\n\n"
                            "topic\n"
                            "Use this to search for a case-insensitive key-phrase in books' bookshelves or subjects. For example, /books?topic=children gives books on the \"Children's Literature\" bookshelf, with the subject \"Sick children -- Fiction\", and so on.\n\n"
                            "Individual Books\n"
                            "Individual books can be found at /books/<id>, where <id> is the book's Project Gutenberg ID number. Error responses will appear in this format:\n\n"
                            "{\n  \"detail\": <string of error message>\n}\n"
                            "API Objects\n"
                            "Types of JSON objects served by Gutendex are given below.\n\n"
                            "Book\n"
                            "{\n  \"id\": <number of Project Gutenberg ID>,\n  \"title\": <string>,\n  \"subjects\": <array of strings>,\n  "
                            "\"authors\": <array of Persons>,\n  \"summaries\": <array of strings>,\n  \"translators\": <array of Persons>,\n  "
                            "\"bookshelves\": <array of strings>,\n  \"languages\": <array of strings>,\n  \"copyright\": <boolean or null>,\n  "
                            "\"media_type\": <string>,\n  \"formats\": <Format>,\n  \"download_count\": <number>\n}\n\n"
                            "Format\n"
                            "{\n  <string of MIME-type>: <string of URL>,\n  ...\n}\n\n"
                            "Person\n"
                            "{\n  \"birth_year\": <number or null>,\n  \"death_year\": <number or null>,\n  \"name\": <string>\n}\n"
                        )
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_query
                    }
                ]
            }
        ],
        response_format={"type": "text"},
        temperature=0.5,
        max_completion_tokens=2048,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    parsed_query = response.choices[0].message.content
    print(parsed_query)
    try:
        # Make the request to Gutendex API with the given query parameters
        api_response = requests.get(GUTENDEX_URL, params=parsed_query)
        api_response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
        
        # Process the API response to tidy up the output
        data = api_response.json()
        count = data.get("count", 0)
        results = data.get("results", [])
        tidy_books = []
        for book in results:
            # Construct a tidy book object
            tidy_book = {
                "id": book.get("id"),
                "title": book.get("title"),
                "authors": book.get("authors"),
                "subjects": book.get("subjects"),
                "languages": book.get("languages")
            }
            # Combine summaries into a single string, if available
            summaries = book.get("summaries")
            tidy_book["summary"] = " ".join(summaries) if summaries else None
            
            # Extract the cover image from formats
            formats = book.get("formats", {})
            cover_image = formats.get("image/jpeg")
            if not cover_image:
                # Fallback: use any format that starts with "image"
                for mime, url in formats.items():
                    if mime.startswith("image"):
                        cover_image = url
                        break
            tidy_book["image"] = cover_image
            
            # Extract the zip file for download
            tidy_book["book_download"] = formats.get("application/zip")
            
            tidy_books.append(tidy_book)
            print(tidy_book)
        
        return jsonify({
            "count": count,
            "results": tidy_books
        }), 200

    except requests.exceptions.RequestException as e:
        abort(500, description=f"Error querying Gutendex API: {e}")

def format_message(message):
    """
    Convert a simple message with 'role' and 'text' keys into the structure required by GPT4o.
    """
    return {
        "role": message.get("role", "user"),
        "content": [
            { "type": "text", "text": message.get("text", "") }
        ]
    }


def get_tidy_books(query_params, n):
    """
    Makes the GET request to Gutendex API using a dictionary of query parameters and returns a list
    of tidy book objects, limited to n books. It checks for duplicates based on both book id and the
    (title, authors) combination.
    """
    response = requests.get(GUTENDEX_URL, params=query_params)
    response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
    
    data = response.json()
    results = data.get("results", [])
    tidy_books = []
    seen_ids = set()
    seen_keys = set()  # Track (title, authors) duplicates
    for book in results:
        book_id = book.get("id")
        if book_id in seen_ids:
            continue
        seen_ids.add(book_id)
        
        title = book.get("title", "").strip()
        authors = [author.get("name", "").strip() for author in book.get("authors", [])]
        key = (title, tuple(sorted(authors)))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        
        tidy_book = {
            "id": book_id,
            "title": title,
            "authors": book.get("authors"),
            "subjects": book.get("subjects"),
            "languages": book.get("languages")
        }
        summaries = book.get("summaries")
        tidy_book["summary"] = " ".join(summaries) if summaries else None

        formats = book.get("formats", {})
        cover_image = formats.get("image/jpeg")
        if not cover_image:
            # Fallback: use any format that starts with "image"
            for mime, url in formats.items():
                if mime.startswith("image"):
                    cover_image = url
                    break
        tidy_book["image"] = cover_image
        tidy_book["book_download"] = formats.get("application/zip")
        
        tidy_books.append(tidy_book)
        if len(tidy_books) == n:
            break
    return tidy_books


def build_graph_from_books(tidy_books):
    """
    Transforms a list of tidy books into a graph structure.
    Node IDs are assigned as lowercase letters starting with 'a'.
    Nodes are connected only if they share at least one common author.
    In each node's data, we include the existing keys (pic, title, author, slotType)
    plus all of the book data from the tidy_books object.
    """
    nodes = []
    letters = list(string.ascii_lowercase)
    
    # Build nodes and temporarily store list of author names for connection logic.
    for i, book in enumerate(tidy_books):
        node_id = letters[i] if i < len(letters) else str(i)
        # Extract list of author names from the book.
        authors_list = [author.get("name", "").strip() for author in book.get("authors", [])]
        node = {
            "id": node_id,
            "text": node_id,
            "data": {
                "pic": book.get("image"),  # existing variable
                "title": book.get("title"),  # existing variable
                "author": ", ".join(authors_list),  # existing variable
                "slotType": f"slot{i+1}",  # existing variable
                # Additional book data from query_books:
                "subjects": book.get("subjects"),
                "languages": book.get("languages"),
                "summary": book.get("summary"),
                "book_download": book.get("book_download"),
                "authors_list": authors_list  # temporary field for edge-building
            }
        }
        nodes.append(node)
    
    # Build edges only if two nodes share at least one common author.
    lines = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if set(nodes[i]["data"]["authors_list"]).intersection(nodes[j]["data"]["authors_list"]):
                lines.append({
                    "from": nodes[i]["id"],
                    "to": nodes[j]["id"]
                })
    
    # Remove the temporary authors_list field from nodes before output.
    for node in nodes:
        node["data"].pop("authors_list", None)
    
    graph = {
        "rootId": nodes[0]["id"] if nodes else None,
        "nodes": nodes,
        "lines": lines
    }
    return graph


@app.route("/query_books_graph", methods=["POST"])
def query_books_graph():
    data = request.get_json()
    if not data or "query" not in data:
        abort(400, description="Bad Request: No query parameter provided")
    
    # Validate API key from headers.
    api_key = request.headers.get("Authorization")
    if not api_key or api_key != f"Bearer {REQUIRED_API_KEY}":
        abort(401, description="Unauthorized: Invalid or missing API key")
    
    # Retrieve the 'n' parameter, defaulting to 10 if not provided.
    n = data.get("n", 10)
    try:
        n = int(n)
        if n < 1:
            abort(400, description="Bad Request: n must be at least 1")
    except ValueError:
        abort(400, description="Bad Request: n must be an integer")
    
    user_query = data["query"]

    # Use the OpenAI client to generate the parsed query string.
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You are a helpful librarian assistant that is designed to assist users with finding, "
                            "discovering and exploring books on Project Gutenberg by making API requests to the gutindex API. "
                            "Below is the documentation required to use this API. Make your best judgement as to the query required "
                            "in order to return the most appropriate books. Only provide the API request and nothing else. Unless asked otherwise, provide books only in english. \n\n"
                            "Lists of Books\n"
                            "Lists of book information in the database are queried using the API at /books (e.g. gutendex.com/books). "
                            "Book data will be returned in the format\n\n"
                            "{\n  \"count\": <number>,\n  \"next\": <string or null>,\n  \"previous\": <string or null>,\n  "
                            "\"results\": <array of Books>\n}\n"
                            "where results is an array of 0-32 book objects, next and previous are URLs to the next and previous pages of results, "
                            "and count in the total number of books for the query on all pages combined.\n\n"
                            "By default, books are ordered by popularity, determined by their numbers of downloads from Project Gutenberg.\n\n"
                            "Parameters can also be added to book-list queries in a typical URL format. For example, to get the first page of written by authors alive after 1899 "
                            "and published in English or French, you can go to /books?author_year_start=1900&languages=en,fr\n\n"
                            "You can find available query parameters below.\n\n"
                            "author_year_start and author_year_end\n"
                            "Use these to find books with at least one author alive in a given range of years. They must have positive or negative integer values. "
                            "For example, /books?author_year_end=-499 gives books with authors alive before 500 BCE, and /books?author_year_start=1800&author_year_end=1899 gives books with authors alive in the 19th Century.\n\n"
                            "copyright\n"
                            "Use this to find books with a certain copyright status: true for books with existing copyrights, false for books in the public domain in the USA, "
                            "or null for books with no available copyright information. These can be combined with commas. For example, /books?copyright=true,false gives books with available copyright information.\n\n"
                            "ids\n"
                            "Use this to list books with Project Gutenberg ID numbers in a given list of numbers. They must be comma-separated positive integers. "
                            "For example, /books?ids=11,12,13 gives books with ID numbers 11, 12, and 13.\n\n"
                            "languages\n"
                            "Use this to find books in any of a list of languages. They must be comma-separated, two-character language codes. "
                            "For example, /books?languages=en gives books in English, and /books?languages=fr,fi gives books in either French or Finnish or both.\n\n"
                            "mime_type\n"
                            "Use this to find books with a given MIME type. Gutendex gives every book with a MIME type starting with the value. "
                            "For example, /books?mime_type=text%2F gives books with types text/html, text/plain; charset=us-ascii, etc.; and /books?mime_type=text%2Fhtml gives books with types text/html, text/html; charset=utf-8, etc.\n\n"
                            "search\n"
                            "Use this to search author names and book titles with given words. They must be separated by a space (i.e. %20 in URL-encoded format) and are case-insensitive. "
                            "For example, /books?search=dickens%20great includes Great Expectations by Charles Dickens.\n\n"
                            "sort\n"
                            "Use this to sort books: ascending for Project Gutenberg ID numbers from lowest to highest, descending for IDs highest to lowest, or popular (the default) for most popular to least popular by number of downloads.\n\n"
                            "topic\n"
                            "Use this to search for a case-insensitive key-phrase in books' bookshelves or subjects. For example, /books?topic=children gives books on the \"Children's Literature\" bookshelf, with the subject \"Sick children -- Fiction\", and so on.\n\n"
                            "Individual Books\n"
                            "Individual books can be found at /books/<id>, where <id> is the book's Project Gutenberg ID number. Error responses will appear in this format:\n\n"
                            "{\n  \"detail\": <string of error message>\n}\n"
                            "API Objects\n"
                            "Types of JSON objects served by Gutendex are given below.\n\n"
                            "Book\n"
                            "{\n  \"id\": <number of Project Gutenberg ID>,\n  \"title\": <string>,\n  \"subjects\": <array of strings>,\n  "
                            "\"authors\": <array of Persons>,\n  \"summaries\": <array of strings>,\n  \"translators\": <array of Persons>,\n  "
                            "\"bookshelves\": <array of strings>,\n  \"languages\": <array of strings>,\n  \"copyright\": <boolean or null>,\n  "
                            "\"media_type\": <string>,\n  \"formats\": <Format>,\n  \"download_count\": <number>\n}\n\n"
                            "Format\n"
                            "{\n  <string of MIME-type>: <string of URL>,\n  ...\n}\n\n"
                            "Person\n"
                            "{\n  \"birth_year\": <number or null>,\n  \"death_year\": <number or null>,\n  \"name\": <string>\n}\n"
                        )
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_query
                    }
                ]
            }
        ],
        response_format={"type": "text"},
        temperature=0.5,
        max_completion_tokens=2048,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    parsed_query = response.choices[0].message.content.strip()
    print("Parsed query:", parsed_query)
    
    # Post-process the parsed query:
    # Remove a leading '/books' if present.
    if parsed_query.startswith('/books'):
        parsed_query = parsed_query[len('/books'):]
    # Remove any leading '?'.
    if parsed_query.startswith('?'):
        parsed_query = parsed_query[1:]
    # Convert the query string to a dictionary of parameters.
    query_params = dict(parse_qsl(parsed_query))
    print("Final query parameters:", query_params)
    
    try:
        tidy_books = get_tidy_books(query_params, n)
        graph = build_graph_from_books(tidy_books)
        return jsonify(graph), 200
    except requests.exceptions.RequestException as e:
        abort(500, description=f"Error querying Gutendex API: {e}")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data or "messages" not in data:
        abort(400, description="Bad Request: No messages provided in the request body")
    
    # Validate API key from headers
    api_key = request.headers.get("Authorization")
    if not api_key or api_key != f"Bearer {REQUIRED_API_KEY}":
        abort(401, description="Unauthorized: Invalid or missing API key")
    
    conversation = data["messages"]
    formatted_messages = []
    
    if not any(msg.get("role") == "system" for msg in conversation):
        formatted_messages.append({
            "role": "system",
            "content": [
                { "type": "text", "text": "You are a helpful librarian assistant. Please format your responses as plain text." }
            ]
        })
    
    for msg in conversation:
        formatted_messages.append(format_message(msg))
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=formatted_messages,
            response_format={"type": "text"},
            temperature=0.5,
            max_completion_tokens=2048,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        next_message = response.choices[0].message.content
        print(next_message)
        return jsonify(next_message), 200
    except Exception as e:
        abort(500, description=f"Error processing chat: {e}")

@app.route('/health')
def health():
    return "OK", 200

if __name__ == "__main__":
    app.run()
