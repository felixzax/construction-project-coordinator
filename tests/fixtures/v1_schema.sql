
CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY, name TEXT NOT NULL, address TEXT DEFAULT '', owner TEXT DEFAULT '', description TEXT DEFAULT '', phase TEXT DEFAULT 'Planning', status TEXT DEFAULT 'Active', archived INTEGER DEFAULT 0, updated TEXT);
CREATE TABLE IF NOT EXISTS contacts(id INTEGER PRIMARY KEY, name TEXT NOT NULL, role TEXT DEFAULT '', company TEXT DEFAULT '', email TEXT DEFAULT '', phone TEXT DEFAULT '', notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS project_contacts(project_id INTEGER REFERENCES projects(id), contact_id INTEGER REFERENCES contacts(id), PRIMARY KEY(project_id,contact_id));
CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id), title TEXT NOT NULL, deadline TEXT DEFAULT '', priority TEXT DEFAULT 'Normal', contact_id INTEGER REFERENCES contacts(id), status TEXT DEFAULT 'Not Started', notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id), title TEXT NOT NULL, category TEXT DEFAULT 'Architectural Plans');
CREATE TABLE IF NOT EXISTS versions(id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES documents(id), revision TEXT NOT NULL, submitted TEXT DEFAULT '', status TEXT DEFAULT 'Draft', requirements TEXT DEFAULT '', file_path TEXT DEFAULT '', resubmission INTEGER DEFAULT 0, created TEXT, UNIQUE(document_id,revision));
CREATE TABLE IF NOT EXISTS communications(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id), contact_id INTEGER REFERENCES contacts(id), occurred TEXT NOT NULL, summary TEXT NOT NULL, follow_up TEXT DEFAULT '', status TEXT DEFAULT 'Open');
CREATE TABLE IF NOT EXISTS milestones(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id), title TEXT NOT NULL, phase TEXT DEFAULT '', deadline TEXT DEFAULT '', status TEXT DEFAULT 'Planned');
CREATE TABLE IF NOT EXISTS activity(id INTEGER PRIMARY KEY, project_id INTEGER REFERENCES projects(id), occurred TEXT, description TEXT);
PRAGMA user_version=1;
