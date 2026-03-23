# Creating the Flask application object, loading the shared configuration, and importing the routes.
from flask import Flask

app = Flask(__name__)
app.config.from_object("app.config.Config")

from app import routes
