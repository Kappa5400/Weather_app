DROP TABLE IF EXISTS cities;

CREATE TABLE IF NOT EXISTS cities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    coordinates TEXT NOT NULL,
    elevation TEXT REAL,
    comment TEXT
);
