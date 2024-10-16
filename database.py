import sqlite3
from contextlib import contextmanager

DATABASE_NAME = 'hh_vacancies.db'


@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db_connection() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT,
                salary_from INTEGER,
                salary_to INTEGER,
                area TEXT,
                experience TEXT,
                employment TEXT,
                url TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS vacancy_requirements (
                vacancy_id INTEGER,
                requirement_id INTEGER,
                FOREIGN KEY (vacancy_id) REFERENCES vacancies (id),
                FOREIGN KEY (requirement_id) REFERENCES requirements (id),
                PRIMARY KEY (vacancy_id, requirement_id)
            );
        ''')
        conn.commit()


if __name__ == '__main__':
    init_db()
