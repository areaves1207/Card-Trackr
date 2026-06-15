# CardTrackr — Technical Architecture Deep Dive

This document explains **why** every decision was made. Read this before touching code so you can explain every piece of the system in an interview without hesitation.

---

## Table of Contents
1. [The Core Problem](#1-the-core-problem)
2. [Why Not Train a Custom Model](#2-why-not-train-a-custom-model)
3. [The Card Identification Pipeline](#3-the-card-identification-pipeline)
4. [Tech Stack Decisions](#4-tech-stack-decisions)
5. [Database Design](#5-database-design)
6. [API Design](#6-api-design)
7. [Authentication (JWT)](#7-authentication-jwt)
8. [Cloud Storage (R2)](#8-cloud-storage-r2)
9. [Containerization (Docker)](#9-containerization-docker)
10. [Frontend Architecture](#10-frontend-architecture)
11. [How to Talk About This in an Interview](#11-how-to-talk-about-this-in-an-interview)

---

## 1. The Core Problem

A user holds up a Pokemon card to a camera, or uploads a photo/video of cards in a binder. We need to:

1. **Locate** the card in the image (it might be at an angle, partially lit, on a cluttered desk)
2. **Identify** which specific card it is (there are 15,000+ unique Pokemon cards)
3. **Save** it to the user's collection so they can review it later

The challenge is step 2. Unlike identifying "a cat" or "a car" (broad categories), we need to distinguish between *Charizard from Base Set (1999)* vs *Charizard from Celebrations (2021)* — totally different cards with different market values.

---

## 2. Why Not Train a Custom Model

Your first instinct was to train a YOLO or CNN model on Pokemon card images. This is a reasonable thought but has fatal flaws:

**The math problem:** There are ~15,000 unique cards. A classification model needs hundreds of examples per class to generalize well. That's potentially millions of labeled images. Gathering, labeling, storing, and training on that data would take months of compute time and terabytes of storage.

**The maintenance problem:** New sets release 3–4 times per year, each adding 150–300 new cards. You'd have to retrain the model every few months.

**The smarter approach:** The Pokemon TCG community has already solved the hard part. The [Pokemon TCG API](https://api.pokemontcg.io) has a database of every card ever printed, with images, metadata, and a unique ID system. Our job is not to *classify* what card we see — it's to *extract enough text* from the card to ask the API "which card is this?"

This is a fundamental engineering skill: **don't solve problems that are already solved. Compose existing solutions.**

**Interview answer:** *"Training a 15K-class classification model was impractical at scale. I instead designed a two-stage pipeline: use computer vision to extract structured text from the card, then use an external API to do the lookup. This is faster, more accurate, cheaper to run, and automatically stays up to date as new cards are released."*

---

## 3. The Card Identification Pipeline

This is the most technically interesting part of the project. Here is each stage in detail.

### Stage 1: Card Detection (OpenCV)

**What:** Find the Pokemon card in the photo and extract it as a clean, straight-on image.

**Why this is hard:** A photo of a card in the real world might be:
- Tilted at an angle (perspective distortion)
- Partially in shadow
- On a patterned background (table, carpet, binder sleeve)
- Slightly out of focus

**How OpenCV solves it:**

```
Raw photo
    │
    ▼ Convert to grayscale
    │   (removes color noise, faster to process)
    │
    ▼ Gaussian blur
    │   (smooths out texture noise so edges are cleaner)
    │
    ▼ Canny edge detection
    │   (finds sharp boundaries — the card's border is a strong edge)
    │
    ▼ Find contours
    │   (traces connected edge paths into shapes)
    │
    ▼ Filter for rectangles
    │   (Pokemon cards are ~2.5" × 3.5" rectangles; we look for a
    │    4-cornered contour with roughly the right aspect ratio)
    │
    ▼ Perspective transform (warpPerspective)
        (takes the 4 corners of the detected card and mathematically
         "flattens" the perspective so we get a straight-on view)
```

**Key concept — perspective transform:** Imagine looking at a rectangle on a table from an angle. The far edge looks shorter than the near edge (like train tracks converging). A perspective transform is a matrix multiplication that reverses this distortion. OpenCV's `cv2.getPerspectiveTransform()` computes the matrix from 4 source points (the card corners) to 4 destination points (the corners of our output image), and `cv2.warpPerspective()` applies it to every pixel.

**Output:** A clean, straight, standardized crop of just the card — like a scanner would produce.

### Stage 2: Text Extraction (EasyOCR)

**What:** Read the card name and collector number from the cropped card image.

**Why these two fields?**
- **Card name** — printed in large bold text at the top of every card. This is the most readable text in the image.
- **Collector number** — printed at the bottom right in format `X/Y` (e.g., `58/102`). Combined with the card name, this uniquely identifies the card within any set.

**How we use the crop:** Rather than running OCR on the whole card (which has flavor text, damage numbers, etc.), we crop to specific regions:
- Top 15% of the card → card name
- Bottom 8% of the card → collector number

This significantly improves OCR accuracy because we're giving the model less ambiguous text to read.

**Why EasyOCR over Tesseract:**
- EasyOCR is a deep learning model that handles rotated/warped text much better
- Tesseract works well on clean printed documents but struggles with real-world photos
- EasyOCR returns a confidence score with each detection, which we use to decide whether to show the user a manual selection fallback

### Stage 3: API Lookup (Pokemon TCG API)

**What:** Take the name + number from OCR and find the exact card.

**The query:**
```
GET https://api.pokemontcg.io/v2/cards?q=name:"Charizard" number:"4"
```

This returns JSON with the card's full metadata: set name, rarity, image URLs, HP, attacks, etc.

**What if OCR gets it slightly wrong?** The API supports partial name matching, so `"Charizard"` still works even if OCR reads `"Charlzard"` (confusing lowercase L and I is a common OCR mistake). We can also implement fuzzy matching on the name before querying.

**Confidence + fallback:** If our OCR confidence is below a threshold, we send back the top 3 API candidates and let the user pick the correct one in the UI. This turns a potential failure into a feature.

### Stage 4: Caching

**Problem:** The Pokemon TCG API has rate limits and we don't want to pay for the same lookup every time.

**Solution:** After the first successful lookup of a card, we store its metadata in our `pokemon_cards` table. Subsequent scans of the same card ID skip the API entirely.

This is **caching at the application layer** — a pattern you'll use constantly in backend engineering.

### Video Processing

For video uploads, we need to extract frames and process each one. The key challenge is **deduplication** — when someone flips through 10 cards over 30 seconds, we might get 60 frames per card (at 2fps × 30 seconds). We only want to record each card once.

**Solution:**
1. Extract frames at 2 fps using OpenCV's `VideoCapture`
2. Run the pipeline on each frame
3. Keep a running set of `card_id`s already found in this session
4. Only add a card to results if it's not already in the set

This runs as a **background task** — the API returns a `session_id` immediately, and the frontend polls `GET /api/scan/{session_id}` every 2 seconds to get results as they come in. This is called **long polling** and is simpler than WebSockets for this use case.

---

## 4. Tech Stack Decisions

### Why FastAPI (not Flask, Django, Express)

**vs Flask:** Flask is synchronous by default. FastAPI is async-first (built on Starlette + asyncio). When we upload an image and wait for the CV pipeline to run, async means other requests aren't blocked while that's happening.

**vs Django:** Django is "batteries included" — it has an ORM, admin panel, templating engine, etc. For an API-only backend, that's overhead we don't need. FastAPI is leaner and more explicit.

**vs Express (Node.js):** Python has the best ecosystem for computer vision (OpenCV, EasyOCR are Python libraries). Mixing Python CV with Node.js would mean running two services. FastAPI keeps everything in one process.

**Killer feature:** FastAPI auto-generates interactive API documentation at `/docs` (Swagger UI) from your code's type hints. You can demo the entire API to an interviewer without a frontend. This alone makes it worth choosing.

### Why PostgreSQL (not SQLite, MongoDB)

**vs SQLite:** SQLite is a file-based database. It doesn't handle concurrent writes well (important when multiple users are scanning at the same time). PostgreSQL is a proper client-server DB.

**vs MongoDB:** Our data is relational — users have collections, collections have cards, cards have scan results. Relational data belongs in a relational database. MongoDB adds complexity without benefit here.

**PostgreSQL specifically:** It's the industry standard for production applications. It supports full-text search, JSONB columns (useful for storing raw API response), and has excellent Python driver support.

### Why SQLAlchemy + Alembic

**SQLAlchemy** is Python's standard ORM (Object-Relational Mapper). It lets you write Python classes that map to database tables and query using Python instead of raw SQL. This gives you:
- Type safety (your IDE knows what fields exist)
- Protection from SQL injection (queries are parameterized automatically)
- Database portability (swap PostgreSQL for SQLite in tests)

**Alembic** handles **database migrations** — versioned scripts that evolve your schema over time. When you add a column to a table, Alembic generates a migration file that can be applied to any environment (your laptop, staging, production) consistently. This is industry standard practice. Showing you use migrations signals you've thought about production deployments.

### Why Cloudflare R2

We need to store uploaded images somewhere. Options:
- Local disk: Doesn't work with Docker, doesn't scale
- Amazon S3: The industry standard, but has egress fees
- Cloudflare R2: S3-compatible API (same code works), zero egress fees, generous free tier

**S3-compatible** means the Python `boto3` library (written for S3) works with R2 unchanged by just swapping the endpoint URL. This is a great interview talking point about vendor-neutral API design.

---

## 5. Database Design

Understanding *why* the schema is designed this way is more important than memorizing it.

### Why separate `pokemon_cards` from `collection_cards`?

`pokemon_cards` is a **cache of the Pokemon TCG API**. It stores information that is the same for every user who owns that card: the card's name, image, set, rarity. It never changes.

`collection_cards` is **user-specific data**: which user owns this card, how many copies they have, what condition it's in, any personal notes. This changes per user.

This is database **normalization** — avoiding data duplication. If we put the card's image URL in `collection_cards`, and 1,000 users all own Charizard, we'd store that image URL 1,000 times. By separating the tables and using a foreign key, we store it once.

```
pokemon_cards        collection_cards
─────────────        ────────────────
id (PK)  ◄───────── pokemon_card_id (FK)
api_id               collection_id (FK) ──► collections
name                 quantity
image_url            condition
set_name             notes
```

### Why a separate `scan_sessions` table?

A scan session is a distinct event in the system:
- It has a **status** (pending, processing, complete, failed)
- It might produce multiple cards (video with 10 cards)
- We want to track *when* and *how* each card was added to a collection

Without this, we'd have no way to show the user "here's everything from your scan on June 14th."

### The `scan_results` table as a join

`scan_results` links a scan session to the cards found. The `confidence` field lets us surface low-confidence detections so the user can verify them. `auto_added` tracks whether the user confirmed the card or it was added automatically.

---

## 6. API Design

### Why REST (not GraphQL)

GraphQL shines when the frontend needs to compose very different data shapes from a single endpoint. Our frontend is straightforward: show me my collection, scan some cards, add cards to collection. REST is simpler to implement and debug, and is what most backend roles use.

### Resource-oriented URLs

Good REST API design names URLs after **resources** (nouns), not actions (verbs):
- `POST /api/scan/images` — create a scan (the upload is the action, scan is the resource)
- `GET /api/collection` — read the collection resource
- `DELETE /api/collection/cards/42` — delete a specific card-in-collection

**Bad design** (action-oriented): `/api/uploadAndScanImage`, `/api/removeCardFromCollection`

### Why return `session_id` from scan immediately?

Image processing (OpenCV + EasyOCR) can take 2–5 seconds per image. If we made the client wait for that synchronously, the HTTP request would hang for potentially 30+ seconds for a video file. That's a bad user experience and can trigger browser/proxy timeouts.

Instead: accept the upload, start processing in the background, immediately return a `session_id`. The client polls `GET /api/scan/{session_id}` every 2 seconds. Results appear progressively as cards are identified.

This pattern is called **async job processing** and is fundamental to backend systems that do heavy computation.

---

## 7. Authentication (JWT)

### How JWT works (explain this cold in any interview)

JWT = JSON Web Token. It's a way to authenticate API requests without storing session state on the server.

**Login flow:**
1. User sends `POST /api/auth/login` with email + password
2. Server verifies password against `bcrypt` hash in the database
3. Server creates a JWT: a JSON payload `{user_id: 42, exp: <timestamp>}` signed with a secret key using HMAC-SHA256
4. Server returns the JWT string to the client
5. Client stores it (in memory or localStorage) and sends it in every subsequent request as `Authorization: Bearer <token>`
6. Server verifies the signature on each request — if valid, trusts the `user_id` inside it

**Why is this secure?** The signature includes both the payload and a secret that only the server knows. Changing even one character of the payload invalidates the signature. The server can verify the token without any database lookup.

**The trade-off:** JWTs can't be revoked before they expire (no "logout from all devices"). For a portfolio project this is fine. Production systems often use short-lived JWTs (15 minutes) + refresh tokens to mitigate this.

### Why bcrypt for passwords?

Never store plaintext passwords. Never store MD5 or SHA-256 hashes — those are fast, and an attacker with the hash database can brute-force them quickly.

`bcrypt` is a **slow hash** by design. It has a configurable "work factor" that makes each hash take ~100ms. That means an attacker can only try ~10 passwords/second per core instead of millions. It also automatically salts each hash (preventing rainbow table attacks).

---

## 8. Cloud Storage (R2)

### Why store uploads in R2 instead of the database?

Storing binary files (images, videos) in a PostgreSQL database is a common beginner mistake. It makes the DB bloated and slow. The right pattern: store files in object storage (S3/R2), store the **URL** to the file in the database.

### How the upload flow works:
1. Client sends the image as multipart form data to `POST /api/scan/images`
2. FastAPI receives the file in memory as bytes
3. Backend uploads to R2 using the boto3 library: `s3_client.put_object(Bucket=..., Key=..., Body=file_bytes)`
4. R2 returns a URL for the stored object
5. We save that URL to `scan_sessions.source_url` in Postgres
6. We then run the CV pipeline on the image bytes (already in memory — no need to download from R2)

R2's zero egress fees matter because serving card images through the API would otherwise cost money on S3.

---

## 9. Containerization (Docker)

### Why Docker?

"Works on my machine" is a real problem. Docker packages your application + its exact environment (OS libraries, Python version, system dependencies like OpenCV) into an **image** that runs identically everywhere.

**Docker concepts you should know:**

- **Image:** A snapshot of an environment. Built from a `Dockerfile`. Read-only.
- **Container:** A running instance of an image. Has writable state.
- **Dockerfile:** A recipe to build an image. Lists what to install and how to start the app.
- **docker-compose:** Orchestrates multiple containers (backend + frontend + postgres) with one command: `docker-compose up`

### Why this matters for the interview:

Docker shows you've thought about **deployment**, not just development. Writing a working `docker-compose.yml` means anyone can clone your repo and have the full stack running in 2 minutes. This is what professional teams do.

### The 3-container setup:

```
docker-compose up
├── postgres:15       ← Database (official image, no custom Dockerfile needed)
├── backend           ← Built from backend/Dockerfile
│   PORT: 8000
│   ENV: DATABASE_URL, SECRET_KEY, R2_* credentials
└── frontend          ← Built from frontend/Dockerfile
    PORT: 5173 (dev) / 80 (prod via nginx)
```

They communicate on a Docker internal network. The backend reaches postgres at `postgres:5432` (hostname = service name in docker-compose).

---

## 10. Frontend Architecture

### Why React + TypeScript

React is the dominant frontend framework in industry. TypeScript adds static typing to JavaScript, catching bugs before runtime. Together they're the most common combo in job postings.

**Key React concepts this project demonstrates:**
- **Component composition** — ScanUpload, CardGrid, ScanResultModal are reusable pieces
- **State management** — scan session status, collection data, auth state
- **Custom hooks** — `useCollection()`, `useScanSession(sessionId)` for polling
- **Async data fetching** — managing loading/error/success states cleanly

### Why Vite (not Create React App)

Create React App is deprecated. Vite is the modern standard: it's 10–100x faster in development and produces smaller production builds. Every current job posting that mentions a build tool mentions Vite.

### Why shadcn/ui

shadcn/ui is not a traditional component library you install. It's a collection of copy-pasteable components built on Radix UI (accessible primitives) and styled with Tailwind. You own the code — no version lock-in, fully customizable. It produces professional-looking UIs fast.

---

## 11. How to Talk About This in an Interview

### The elevator pitch (30 seconds):
*"CardTrackr lets you photograph your Pokemon card collection — or even scan a video of flipping through a binder — and it automatically identifies each card and adds it to your inventory. The interesting engineering challenge was identification: there are 15,000+ unique cards so training a model was impractical. I built a two-stage pipeline: OpenCV detects and perspective-corrects the card in the photo, then EasyOCR extracts the card name and collector number, and I query the Pokemon TCG API to resolve the exact card. The stack is FastAPI, PostgreSQL, Cloudflare R2, and React — all containerized with Docker."*

### Questions they will ask and how to answer:

**"Why did you choose FastAPI over Flask or Django?"**
FastAPI is async-first, which matters because our CV pipeline blocks the thread while processing. It also auto-generates OpenAPI docs from type hints, which makes the API self-documenting. Django would have been overkill — we don't need its ORM sugar, admin panel, or templating engine.

**"How does your card identification actually work?"**
Walk through the 4 stages: card detection (OpenCV + perspective transform), text extraction (EasyOCR on cropped regions), API lookup, caching in postgres. Mention the fallback when OCR confidence is low.

**"How do you handle the async video processing?"**
The upload endpoint returns a session_id immediately. Processing runs as a background task. The frontend polls the session endpoint every 2 seconds to get progressive results. This keeps the API responsive and gives the user real-time feedback.

**"How does authentication work?"**
JWTs: user logs in with email + bcrypt-hashed password, gets back a signed token. The token contains the user_id and expiry, signed with a server secret. Every authenticated endpoint verifies the signature. Stateless — no session table needed.

**"How would you scale this if it got popular?"**
- Move background tasks to Celery + Redis (a proper task queue instead of FastAPI's built-in BackgroundTasks)
- Read replicas for PostgreSQL to handle more concurrent queries
- Cache pokemon_cards lookups in Redis (faster than PostgreSQL for hot data)
- Horizontal scaling of the FastAPI backend behind a load balancer (it's stateless, so multiple instances work fine)

**"What would you do differently?"**
*"I'd add a WebSocket endpoint for real-time scan progress instead of polling — it reduces unnecessary requests. I'd also explore using a perceptual hash lookup for cards where OCR fails, by pre-computing hashes for all 15K card images from the API. That would be a more robust fallback than asking the user to manually select the card."*

---

## Key Terms Glossary

| Term | What it means |
|---|---|
| Perspective transform | Mathematical operation that "unwarps" a rectangle photographed at an angle |
| OCR | Optical Character Recognition — reading text from images |
| ORM | Object-Relational Mapper — Python classes that represent DB tables |
| Migration | A versioned script that changes the DB schema |
| JWT | JSON Web Token — signed payload for stateless auth |
| bcrypt | Intentionally slow password hashing algorithm |
| Object storage | Store for files/blobs (S3/R2) — separate from a database |
| Background task | Work that runs after an HTTP response is already sent |
| Long polling | Client repeatedly asks "are you done yet?" until the answer is yes |
| Contour | A curve in an image that connects points of equal intensity (used to find edges) |
| Docker image | Packaged snapshot of an app + its environment |
| docker-compose | Tool to run multiple containers as a coordinated system |
