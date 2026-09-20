# JSON → Markdown

Invoke `json-markdown-export` through the shared Agent Runner with explicit repository root, input JSON, output Markdown, profile/template-set identity, optional SQLite database, and validate/apply intent. Validation is the default. Apply writes one standalone file atomically or uses the bounded recovery transaction when a database is supplied.
