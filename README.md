# Card-Trackr
Step 1: Generate a real secret key and put it in .env:


python -c "import secrets; print(secrets.token_hex(32))"
Step 2: Start everything:


docker-compose up --build
Step 3: Run the migration (one time):


docker-compose exec backend alembic upgrade head
Step 4: Open http://localhost:5173 — the full app is live. The auto-generated API docs are at http://localhost:8000/docs.

CardTrackr
CardTrackr is a Pokemon card inventory app that helps users quickly identify cards from photos, confirm uncertain matches, and save the results into a searchable collection. The goal is to make it feel practical, polished, and technically strong enough to stand out on a resume.

Project Goal
The app should let a user:

Upload a photo of one or more Pokemon cards.
Detect and identify the card or generate a ranked list of likely matches.
Confirm the correct result when confidence is low.
Save the card to their collection.
Review their inventory later with search and filters.
Recommended Architecture
The best approach is not to train a model to classify every Pokemon card directly. That would require too much labeled data and would be hard to maintain.

Instead, use a staged pipeline:

Card detection and cropping
OCR and text extraction
Metadata lookup through a Pokemon card API
Confidence scoring and candidate ranking
Manual confirmation when needed
Save confirmed cards to Postgres
This approach is much more realistic and still gives you a strong full-stack and backend project.

Proposed Stack
Frontend: React
Backend: Python FastAPI
Database: Postgres
Image storage: Cloudflare R2 or a similar object store
Computer vision: OpenCV plus OCR tooling
Metadata source: Pokemon card API with local caching
MVP Scope
The first version should focus on:

Single photo uploads, not video scanning
Personal app first, not full SaaS multi-user infrastructure
External card metadata API usage
Manual confirmation for uncertain matches
A clean scan-to-collection workflow
Data Model Direction
The app should keep these concepts separate:

User accounts
Uploaded images
Scan sessions
Match candidates
Cached Pokemon card metadata
Collection entries
That separation makes the system easier to scale and keeps scan logic independent from owned inventory data.

Why This Is a Good Resume Project
This project can demonstrate:

API design and backend architecture
Database modeling and migrations
Async processing and request handling
Practical computer vision integration
External API integration and caching
Product thinking and UX tradeoffs
A realistic engineering approach to an ML-adjacent problem
Future Enhancements
After the MVP works, the best upgrades are:

Video binder scanning
Frame deduplication
Background jobs for scan processing
Smarter matching with image similarity
Better card-confidence scoring
Multi-user accounts and sharing
Development Plan
Build the single-photo scan flow first.
Add the metadata lookup and local cache.
Save confirmed cards in Postgres.
Build the frontend upload and review experience.
Add polish, logging, and tests.
Expand to video scanning later.
If you want, I can next turn this into a more polished README with sections like setup, screenshots, roadmap, and tech stack so it looks like a real public GitHub project.