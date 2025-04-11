from flask import Flask, render_template
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/status')
def status():
    return {"status": "Bot is online!", "message": "Discord bot is running smoothly."}

def run():
    app.run(host='0.0.0.0', port=5000)

def keep_alive():
    t = Thread(target=run)
    t.start()