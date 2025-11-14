from flask import Flask, render_template, jsonify

def create_app():
    app = Flask(__name__)

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/health")
    def health():
        return jsonify(status="ok")

    return app
