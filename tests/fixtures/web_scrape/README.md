# Web Scrape Fixture Set

This directory contains scraped or transcribed (User Question, SQL query) examples gathered from public web sources.

Conventions
- Each case has its own directory with a human-readable descriptive id.
- `uq.txt` stores the user question.
- `source.sql` stores the SQL exactly as harvested from the source, or minimally normalized for plain text preservation.
- `documentation.txt` stores a short provenance note.
- `metadata.json` stores source URL and whether the UQ was explicit or inferred.

Notes
- The original Google share link redirected into a Google Search flow rather than exposing stable share-page content. See `_google_share_redirect_note.txt`.
- Some source SQL uses old ChEMBL schemas or dialect-specific constructs. These fixtures are intentionally stored as source material first; adaptation for executable tests can happen later.
- A separate second-pass corpus now lives in `tests/fixtures/web_scrape2/` for newer sources harvested with stricter provenance and promotion criteria.
