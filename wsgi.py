from app import create_app
import app.routes # Just rejestering routes for my app

app = create_app()

if __name__ == "__main__":
    app.run()