# CookAI — Microservices Architecture

> **Architecture accuracy note:** CookAI V1.3 is currently a **modular monolith**: one FastAPI application contains multiple functional modules and is deployed with PostgreSQL using Docker Compose. The first diagram below is a **proposed logical service decomposition**, not a claim that each box is already an independently deployed microservice. The second diagram shows the current implementation more accurately.

## Proposed logical service architecture

```mermaid
flowchart LR
    U[User / Admin Browser] --> FE[CookAI Web Frontend]
    FE --> API[API Entry / FastAPI]

    API --> AUTH[Identity & Access<br/>Register / Login / Role]
    API --> REC[Recipe & AI<br/>Ingredient input / Gemini]
    API --> USAGE[Usage Management<br/>Daily quota]
    API --> SUB[Subscription<br/>Free / Pro]
    API --> PAY[Payment<br/>Sandbox / webhook]
    API --> DASH[Dashboard & Admin<br/>Users / usage / revenue]
    API --> HIST[Recipe Engagement<br/>History / rating / recipe book]
    API --> NUT[Personal Nutrition<br/>Guidance / portion adjustment]

    AUTH --> DB[(PostgreSQL)]
    REC --> DB
    USAGE --> DB
    SUB --> DB
    PAY --> DB
    DASH --> DB
    HIST --> DB
    NUT --> DB
    REC --> GEM[Google Gemini API]
    FE -. text-to-speech .-> TTS[Browser Speech API]
```

## Current deployment architecture

```mermaid
flowchart TB
    B[Browser / CookAI UI] -->|HTTP :8001 local V1.3| A[Single FastAPI Application<br/>Auth + AI + Usage + Subscription<br/>Payment + Dashboard + History<br/>Recipe Book + Nutrition]
    A -->|SQLAlchemy / DATABASE_URL| D[(PostgreSQL 16)]
    A -->|HTTPS API request| G[Google Gemini API]
    B -->|Speech synthesis| S[Browser Speech API]
    C[Docker Compose] -. manages .-> A
    C -. manages .-> D
```

## Notes
- V1.3 local setup: API host port `8001` → container port `8000`; PostgreSQL host port `5433` → container port `5432`.
- V1.2 previously used host ports `8000` and `5432`.
- Current modules are logical responsibilities inside one FastAPI application, not independent deployed microservices.
- PostgreSQL is the current relational database; Gemini is an external AI service.
- Payment is sandbox-only.
- If an assignment requires a “Microservices Architecture” diagram, label the first diagram as a **proposed logical architecture** and use the current deployment diagram to describe what is actually implemented.
