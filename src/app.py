import os
from flask import Flask

def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key-default'),
        DATABASE_PATH=os.environ.get('DATABASE_PATH', 'data/minilms.db'),
    )

    if test_config:
        app.config.update(test_config)

    @app.route('/')
    def index():
        return {"message": "Mini LMS API is running"}

    @app.route('/health')
    def health():
        return {"status": "ok"}

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)