# OpenToDo

A basic to-do application built with Python (Flask) — created as a hands-on practice project to learn web development and Python programming from the ground up.

## Features

- **User Registration & Login** — Create an account and log in with secure password hashing
- **Task Management** — Add and delete tasks specific to your account
- **Session Authentication** — Protected routes using Flask-Login
- **SQLite Database** — Persistent storage with SQLAlchemy ORM
- **Clean UI** — Simple, responsive interface with a sidebar layout

## Tech Stack

- **Python** — Core programming language
- **Flask** — Lightweight web framework
- **Flask-SQLAlchemy** — Database ORM
- **Flask-Login** — User session management
- **Werkzeug** — Password hashing
- **SQLite** — Database engine
- **HTML/CSS** — Frontend templates and styling

## Getting Started

### Prerequisites

- Python 3.x
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/OpenToDo.git
   cd OpenToDo
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # On Windows
   ```

3. Install dependencies:
   ```bash
   pip install flask flask-login flask-sqlalchemy sqlalchemy werkzeug
   ```

4. Run the app:
   ```bash
   python app.py
   ```

5. Open your browser and navigate to **http://127.0.0.1:5000**

## Project Structure

```
OpenToDo/
├── app.py              # Main application entry point
├── readme.md           # This file
├── instance/
│   └── mydatabase.db   # SQLite database (created on first run)
├── static/
│   ├── css/
│   │   ├── style.css   # Compiled stylesheet
│   │   ├── style.scss  # Sass source file
│   │   └── style.css.map
│   ├── js/
│   │   └── alerts.js   # JavaScript for alert dismissals
│   └── icons/
│       └── checklist.png
└── templates/
    ├── base.html       # Base template (layout skeleton)
    ├── login.html      # Login page
    ├── register.html   # Registration page
    └── index.html      # Main dashboard with task list
```

## How It Works

1. **Register** — Create a new account with a unique username and password. Passwords are hashed using Werkzeug before being stored.
2. **Login** — Authenticate with your credentials to access the dashboard.
3. **Add Tasks** — Type a task description and click "Add task" to save it to your account.
4. **Delete Tasks** — Remove tasks you no longer need using the delete button.
5. **Logout** — End your session and return to the login page.

## What I Learned

This project was built as a learning exercise to practice:

- Python fundamentals and OOP (class-based models)
- Flask routing, templates, and request handling
- Database design with SQLAlchemy relationships
- User authentication and session management
- Secure password storage with hashing
- HTML/CSS for building functional user interfaces
- Version control with Git

## License

This project is open source and available for anyone to use and learn from.
