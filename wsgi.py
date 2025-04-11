from flask_app import app

# Export for gunicorn
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)