import os

DB = {
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "123456"),
    "host":     os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "interactive_quiz"),
    "port":     3306,
}