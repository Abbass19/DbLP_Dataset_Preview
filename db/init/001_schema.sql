-- DBLP Explorer schema (Technical Proposal §3.1)

CREATE EXTENSION IF NOT EXISTS vector;

-- Nodes
CREATE TABLE IF NOT EXISTS author (
  author_id   SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  orcid       TEXT,
  dblp_pid    TEXT UNIQUE            -- from <www> person records
);

CREATE TABLE IF NOT EXISTS venue (
  venue_id    SERIAL PRIMARY KEY,
  key_prefix  TEXT UNIQUE,           -- e.g. conf/kdd, journals/tkde
  name        TEXT,
  type        TEXT CHECK (type IN ('conference','journal','other'))
);

CREATE TABLE IF NOT EXISTS paper (
  paper_id    SERIAL PRIMARY KEY,
  dblp_key    TEXT UNIQUE NOT NULL,  -- e.g. conf/kdd/SmithL21
  title       TEXT NOT NULL,
  year        SMALLINT,
  type        TEXT,                  -- article, inproceedings, ...
  venue_id    INT REFERENCES venue,
  doi         TEXT,
  abstract    TEXT                   -- enriched from OpenAlex
);

-- Edges
CREATE TABLE IF NOT EXISTS authorship (             -- Author -[AUTHORED]-> Paper
  author_id   INT REFERENCES author,
  paper_id    INT REFERENCES paper,
  "position"  SMALLINT,              -- author order
  PRIMARY KEY (author_id, paper_id)
);

CREATE TABLE IF NOT EXISTS citation (               -- Paper -[CITES]-> Paper
  citing_id   INT REFERENCES paper,
  cited_id    INT REFERENCES paper,
  PRIMARY KEY (citing_id, cited_id)
);

-- Results written back by the centrality job
CREATE TABLE IF NOT EXISTS author_metrics (
  author_id           INT PRIMARY KEY REFERENCES author,
  degree              INT,
  pagerank            DOUBLE PRECISION,
  betweenness         DOUBLE PRECISION,
  community           INT,
  pagerank_percentile     DOUBLE PRECISION,
  betweenness_percentile  DOUBLE PRECISION,
  computed_at         TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS paper_metrics (
  paper_id    INT PRIMARY KEY REFERENCES paper,
  pagerank    DOUBLE PRECISION,
  computed_at TIMESTAMPTZ DEFAULT now()
);

-- Chatbot embeddings (pgvector)
CREATE TABLE IF NOT EXISTS paper_embedding (
  paper_id    INT PRIMARY KEY REFERENCES paper,
  embedding   vector(768)
);
