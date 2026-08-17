# Web Scrape Round 2 Fixture Set

This directory contains a second pass of scraped or transcribed (User Question, SQL query) examples gathered from public web sources.

Why a separate corpus
- The second pass used stricter lessons from the first pass: prefer primary-source SQL, preserve exact filter semantics, and keep provenance cleaner for later promotion.
- Most examples here are still source material only. Two stronger cases have now been promoted into executable lanes, while the remaining simple count queries stay as source material.

Conventions
- Each case has its own directory with a human-readable descriptive id.
- `uq.txt` stores the user question.
- `source.sql` stores the SQL exactly as harvested from the source, or minimally normalized for plain text preservation.
- `documentation.txt` stores a short provenance note.
- `metadata.json` stores source URL and harvest metadata.
