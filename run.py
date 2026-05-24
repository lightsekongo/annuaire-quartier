from dotenv import load_dotenv
load_dotenv()  # Charge les variables depuis .env

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)