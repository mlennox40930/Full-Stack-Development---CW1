from flask import Flask
from blueprints.movies_bp import movies_bp
from blueprints.reviews_bp import reviews_bp
from blueprints.auth_bp import auth_bp

app = Flask(__name__)

# Register Blueprints
app.register_blueprint(movies_bp)
app.register_blueprint(reviews_bp)
app.register_blueprint(auth_bp)

if __name__ == "__main__":
    app.run(debug=True, port=5001)