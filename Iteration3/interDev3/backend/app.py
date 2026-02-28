from app.routes import app  # Use the API app with registered routes/blueprints

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
