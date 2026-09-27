-- Indexes (Technical Proposal §3.1)

CREATE INDEX IF NOT EXISTS idx_paper_year ON paper (year);
CREATE INDEX IF NOT EXISTS idx_paper_venue ON paper (venue_id);
CREATE INDEX IF NOT EXISTS idx_authorship_paper ON authorship (paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_title_fts ON paper USING GIN (to_tsvector('english', title));

-- Derived graph: weighted co-authorship (undirected, a < b)
CREATE MATERIALIZED VIEW IF NOT EXISTS coauthor_edge AS
SELECT a1.author_id AS src, a2.author_id AS dst,
       COUNT(*) AS weight, MIN(p.year) AS first_year, MAX(p.year) AS last_year
FROM authorship a1
JOIN authorship a2 ON a1.paper_id = a2.paper_id AND a1.author_id < a2.author_id
JOIN paper p ON p.paper_id = a1.paper_id
GROUP BY 1, 2;

CREATE UNIQUE INDEX IF NOT EXISTS idx_coauthor_edge_pair ON coauthor_edge (src, dst);

-- pgvector HNSW index (built after the table has data in real usage,
-- but declared here so a fresh init matches the schema exactly)
CREATE INDEX IF NOT EXISTS idx_paper_embedding_hnsw
  ON paper_embedding USING hnsw (embedding vector_cosine_ops);
