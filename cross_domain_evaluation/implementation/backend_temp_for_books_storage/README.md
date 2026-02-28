# Book Storage Backend

## Overview
This is a temporary backend for book storage, designed to facilitate interaction with JSON data. Vue cannot directly modify JSON files, so this backend serves as an intermediary. Future improvements include integrating a JSON file into Matt's backend. Using a local backend simplifies testing, reviewing, and deleting JSON files.

## Features
- Retrieve stored book data (`GET /books`)
- Store book data by overwriting the existing file (`POST /books`)
- Clear all stored book data (`DELETE /books`)

## Installation
### Prerequisites
Ensure you have [Node.js](https://nodejs.org/) installed on your system.

### Steps
1. Clone this repository:
   ```sh
   git clone <repository-url>
   cd <repository-folder>
   ```
2. Install dependencies:
   ```sh
   npm install
   ```
3. Start the backend server:
   ```sh
   node server.js
   ```
   The server will run at `http://localhost:2600`.

## API Endpoints
### 1. Get Book Data
**Endpoint:** `GET /books`

**Response:**
```json
{
  "lines": [],
  "nodes": [],
  "rootId": ""
}
```

### 2. Store Book Data
**Endpoint:** `POST /books`

**Request Body:**
```json
{
  "lines": [...],
  "nodes": [...],
  "rootId": "some-id"
}
```

**Response:**
```json
{
  "message": "Book data successfully stored"
}
```

### 3. Clear Book Data
**Endpoint:** `DELETE /books`

**Response:**
```json
{
  "message": "All book data cleared"
}
```

## Notes
- The backend reads from and writes to `books-data.json`.
- All data is overwritten upon storage.
- The backend includes CORS support to allow cross-origin requests.


## License
MIT License

