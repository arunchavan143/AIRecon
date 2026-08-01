CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE targets (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id),
    domain TEXT NOT NULL,
    added_at TIMESTAMP DEFAULT now()
);

CREATE TABLE hosts (
    id SERIAL PRIMARY KEY,
    target_id INT REFERENCES targets(id),
    hostname TEXT NOT NULL,
    ip TEXT,
    status_code INT,
    title TEXT,
    tech_stack TEXT[],
    server TEXT,
    alive BOOLEAN DEFAULT false,
    first_seen TIMESTAMP DEFAULT now(),
    last_seen TIMESTAMP DEFAULT now()
);
