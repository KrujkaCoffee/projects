BEGIN IMMEDIATE;

WITH cutoff AS (
  SELECT max(rowid) AS max_id FROM SqlEvents
),
batch AS (
  SELECT
    query,
    substr(date, 1, 10) AS day,
    COUNT(*) AS cnt,
    MIN(completion_time) AS ct_min,
    MAX(completion_time) AS ct_max
  FROM SqlEvents
  WHERE rowid <= (SELECT max_id FROM cutoff)
    AND date IS NOT NULL AND length(date) >= 10
  GROUP BY query, substr(date, 1, 10)
)

INSERT INTO SqlEvents_by_query (query, day, cnt, completion_time_min, completion_time_max)
SELECT query, day, cnt, ct_min, ct_max
FROM batch
ON CONFLICT(query, day) DO UPDATE SET
  cnt = SqlEvents_by_query.cnt + excluded.cnt,
  completion_time_min =
    CASE
      WHEN SqlEvents_by_query.completion_time_min IS NULL THEN excluded.completion_time_min
      WHEN excluded.completion_time_min IS NULL THEN SqlEvents_by_query.completion_time_min
      ELSE min(SqlEvents_by_query.completion_time_min, excluded.completion_time_min)
    END,
  completion_time_max =
    CASE
      WHEN SqlEvents_by_query.completion_time_max IS NULL THEN excluded.completion_time_max
      WHEN excluded.completion_time_max IS NULL THEN SqlEvents_by_query.completion_time_max
      ELSE max(SqlEvents_by_query.completion_time_max, excluded.completion_time_max)
    END;


WITH cutoff AS (
  SELECT max(rowid) AS max_id FROM SqlEvents
)
INSERT OR IGNORE INTO SqlEvents_by_query_app (query, day, app)
SELECT DISTINCT
  query,
  substr(date, 1, 10) AS day,
  app
FROM SqlEvents
WHERE rowid <= (SELECT max_id FROM cutoff)
  AND app IS NOT NULL AND app <> ''
  AND date IS NOT NULL AND length(date) >= 10;

UPDATE SqlEvents_by_query
SET apps = (
  SELECT group_concat(app)
  FROM SqlEvents_by_query_app a
  WHERE a.query = SqlEvents_by_query.query
    AND a.day   = SqlEvents_by_query.day
);

WITH cutoff AS (
  SELECT max(rowid) AS max_id FROM SqlEvents
)
DELETE FROM SqlEvents
WHERE rowid <= (SELECT max_id FROM cutoff);

COMMIT;
