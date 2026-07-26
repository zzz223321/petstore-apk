import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, 'petstore.db')
SECRET_KEY = 'change-me-in-production'
DEBUG = False