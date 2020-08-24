CREATE TABLE IF NOT EXISTS tokens (
  token TEXT PRIMARY KEY NOT NULL,
  dsid TEXT NOT NULL,
  url TEXT NOT NULL,
  ts INTEGER NOT NULL,  /* Unix timestamp of token creation */
  status INTEGER,  /* [requested, staged, verified] */
  UNIQUE (token)
);

CREATE TABLE IF NOT EXISTS dataset_urls (
  url TEXT PRIMARY KEY NOT NULL,
  dsid TEXT NOT NULL,
  UNIQUE (url)
);
