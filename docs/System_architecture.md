# System Architecture Document
**Movie Ticket Booking System**  
Version: 1.0  
Last Updated: 15 November 2025  
Technology Stack: FastAPI + PostgreSQL + WebSockets + Redis (Seat Locks) + MongoDB (Audit/Notifications)

---

## 1. Executive Summary

The Movie Ticket Booking System is a FastAPI-based backend for browsing movies, managing shows, seat layouts and dynamic pricing, locking seats, booking tickets, processing payments, sending notifications, and administering platform data. It supports strict role-based access control with two roles: admin and user, and uses JWT authentication with 1-hour access tokens and 7-day refresh tokens.

### 1.1 Purpose

- Centralized management of movies, screens, seats, shows, pricing, GST, discounts, food items, backups/restores
- Reliable seat selection with race-free, TTL-based seat locks
- Secure booking and payment lifecycle, including refunds
- Real-time notifications (e.g., booking confirmations and updates)
- Operable admin workflows for data management and maintenance (backup/restore)
- Feedback capture and response

### 1.2 Key Features

- JWT-based authentication with RBAC (roles: admin, user) and ownership checks
- Movies, screens, seat categories, and shows management
- Show-category pricing model (per show, per seat category)
- Seat availability and seat lock mechanism to prevent double booking
- Booking pipeline with tax (GST), discounts, and optional food add-ons
- Payments and refunds (gateway-agnostic; webhook verification recommended)
- Real-time notifications via WebSockets and REST
- Backups and restores auditable via API
- Feedback and admin replies

Note: Token lifetimes and role semantics are aligned with the API documentation (Access token: 1 hour, Refresh token: 7 days). The detailed RBAC and authentication matrix remains as defined in the Authentication & RBAC doc.

---

## 2. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend Framework | FastAPI | REST API, WebSocket support, async operations |
| Database | PostgreSQL | Primary relational data store (entities, bookings, payments) |
| ORM | SQLAlchemy | Data models and queries |
| Authentication | JWT (Access 1h, Refresh 7d) | Token-based authentication |
| Password Hashing | Argon2 or bcrypt | Secure password storage |
| Concurrency Control | Redis | Ephemeral seat locks with TTL |
| WebSocket | FastAPI WebSockets | Real-time notifications |
| API Documentation | OpenAPI/Swagger | Interactive API documentation |
| File Storage | Local File System | Movie posters, images (e.g., /static/uploads) |
| Logging/Audit | MongoDB | Request logs, notifications store (optional) |

Optional/Pluggable:
- Task Queue: FastAPI BackgroundTasks or Celery for cleanup (e.g., stale locks)
- Payment Gateway: Stripe/Razorpay/etc. with signed webhooks

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                         │
│     (Web, Admin Dashboard, Mobile Clients)                  │
└────────────────────────┬────────────────────────────────────┘
                         │  HTTPS (REST) + WebSocket (wss://)
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    FastAPI Application                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               Middleware Stack                       │   │
│  │  - CORS (Cross-Origin Requests)                      │   │
│  │  - Trusted Host (Security)                           │   │
│  │  - Logging / Audit (to MongoDB)                      │   │
│  │  - JWT Auth (Access/Refresh)                         │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │                API Router Layer (v1)                 │   │
│  │  /users         - signup, login, refresh             │   │
│  │  /movies        - catalog CRUD (admin), list/get     │   │
│  │  /screens       - screens CRUD (admin), list/get     │   │
│  │  /seats         - seat CRUD (admin)                  │   │
│  │  /seat-categories - CRUD (admin)                     │   │
│  │  /shows         - create/list/cancel (admin), list   │   │
│  │  /show-category-pricing - CRUD (admin)               │   │
│  │  /seatlocks     - create/list/delete/cleanup         │   │
│  │  /bookings      - create/get/cancel/logs             │   │
│  │  /payments      - list/get/delete (admin), own reads │   │
│  │  /discounts     - CRUD (admin)                       │   │
│  │  /gst           - CRUD (admin)                       │   │
│  │  /food-categories - CRUD (admin)                     │   │
│  │  /food-items    - CRUD (admin), list/get             │   │
│  │  /notifications - list/mark-read                     │   │
│  │  /backup        - backup logs CRUD (admin)           │   │
│  │  /restore       - restore logs CRUD (admin)          │   │
│  │  /feedback      - create/list, reply (admin)         │   │
│  │  /ws            - WebSocket connections              │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │               Business Logic Layer                   │   │
│  │  - Booking Orchestrator & Validation                 │   │
│  │  - Seat Lock Manager (Redis TTL)                     │   │
│  │  - Pricing Engine (Show + Category + GST + Discount) │   │
│  │  - Payment Orchestration (initiate/refund)           │   │
│  │  - Notifications (REST + WebSocket)                  │   │
│  │  - Backup/Restore Operations                         │   │
│  │  - Feedback & Admin Reply                            │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │                 Data Access Layer                    │   │
│  │   SQLAlchemy ORM Models:                             │   │
│  │  - User  - Movie  - Screen  - Seat  - SeatCategory  │   │
│  │  - Show  - ShowCategoryPricing - SeatLock (ephemeral)│   │
│  │  - Booking - Payment - Discount - GST                │   │
│  │  - FoodCategory - FoodItem - Notification - Backup   │   │
│  │  - Restore - Feedback                                │   │
│  └──────────────────────┬───────────────────────────────┘   │
└─────────────────────────┼───────────────────────────────────┘
                          │
                ┌─────────┴─────────┬─────────────────────────┐
                │                   │                         │
      ┌─────────▼────────┐  ┌──────▼──────────┐     ┌────────▼─────────┐
      │   PostgreSQL      │  │     Redis       │     │     MongoDB       │
      │ (Primary DB)      │  │ (Seat Locks)    │     │ (Audit/Notif)     │
      │ Entities, TXNs    │  │ TTL + atomicity │     │ Logs & messages   │
      └───────────────────┘  └─────────────────┘     └───────────────────┘

            ┌─────────────────────────────┐
            │       External Services     │
            │ - Payment Gateway (webhooks)│
            │ - GitHub (backup storage)   │
            └─────────────────────────────┘
```

---

## 4. Data Flow Diagrams

### 4.1 User Registration & Login Flow

User → POST /users/signup  
  ↓  
Validate Input (Pydantic)  
  ↓  
Check Email/Phone Uniqueness → PostgreSQL  
  ↓  
Hash Password (Argon2/bcrypt)  
  ↓  
Create User → PostgreSQL  
  ↓  
200/201 Created (no tokens until login)

User → POST /users/login  
  ↓  
Verify Credentials  
  ↓  
Issue JWTs (Access 1h, Refresh 7d)  
  ↓  
Return { access_token, token_type, refresh_token }

User → POST /users/refresh  
  ↓  
Validate Refresh Token (signature/exp/jti not revoked)  
  ↓  
Return new Access Token

---

### 4.2 Browse Movies, Shows, and Availability

Client → GET /movies (filters optional)  
  ↓  
Query PostgreSQL  
  ↓  
Return list of movies

Client → GET /shows (filters by movie_id, screen_id, date, status)  
  ↓  
Query PostgreSQL  
  ↓  
Return list of shows

Client → GET /shows/{id}/availability  
  ↓  
Aggregate seat layout + booked seats + live locks (Redis)  
  ↓  
Return seat map with availability

Note: Read endpoints may be public; configurable per deployment.

---

### 4.3 Seat Lock and Booking Flow

User → POST /seatlocks/  
Body: { show_id, seat_id(s) }  
  ↓  
Auth (JWT: user or admin)  
  ↓  
Validate show and seats; ensure not booked or locked  
  ↓  
Create lock(s) in Redis with TTL (e.g., 10 minutes)  
  ↓  
Return lock_id(s)

User → POST /bookings/  
Body: { user_id, show_id, seats, foods?, discount_id? }  
  ↓  
Auth (JWT)  
  ↓  
Validate locks are owned by user and not expired  
  ↓  
Calculate pricing (base + category + GST - discount + add-ons)  
  ↓  
BEGIN TRANSACTION  
  ↓  
Persist booking, seat allocations, add-ons, taxes → PostgreSQL  
  ↓  
Mark seats as sold; finalize booking status (PENDING/CONFIRMED)  
  ↓  
COMMIT  
  ↓  
Create Notification → MongoDB  
  ↓  
Return booking payload

Conflicts: If seat raced/expired, respond 409 with guidance to refresh availability.

---

### 4.4 Payment Processing

User → Initiate payment (during/after booking creation)  
- Payment orchestration associates payment record (PENDING) to booking
- On gateway callback/webhook:
  - Verify signature
  - Update payment_status (COMPLETED/FAILED)
  - Transition booking_status accordingly
  - Log status changes (booking logs endpoint)

Admin can trigger refunds according to policy: update payment, adjust booking status, push notification.

---

### 4.5 Notifications (REST + WebSocket)

Server Event (booking created/confirmed/cancelled, refund)  
  ↓  
Create Notification → MongoDB  
  ↓  
If WebSocket session active for user: push JSON event  
  ↓  
User can fetch via GET /notifications and mark read via GET /notifications/mark_all_read/{user_id}

WebSocket lifecycle:
- Client connects WS /ws
- Authenticate on connect (token)
- Store connection in a ConnectionManager keyed by user_id/sid
- Heartbeats keep-alive; remove on disconnect

---

### 4.6 Admin Show & Pricing Management

Admin → POST /shows/  
  ↓  
Create show with movie_id, screen_id, date/time, status

Admin → POST /show-category-pricing/  
  ↓  
Set per-category price for a given show

Admin → PUT /shows/{show_id}/cancel  
  ↓  
Cancel show; cascade notifications to impacted bookings if needed

Admin → GET /shows/available-slots?screen_id=&date=  
  ↓  
Compute free time windows based on existing shows

---

### 4.7 Backups and Restores

Admin → POST /backup/  
  ↓  
Create backup entry, upload artifact to GitHub, store metadata → PostgreSQL/MongoDB  
  ↓  
Return backup details

Admin → POST /restore/  
  ↓  
Validate source backup; execute restore; log operation  
  ↓  
Return restore details

List/get/delete backup/restore records via REST endpoints.

---

### 4.8 Feedback

User → POST /feedback/  
  ↓  
Create feedback for booking_id with rating/comment

Admin → PUT /feedback/{feedback_id}/reply  
  ↓  
Respond to feedback; persist reply

Admin/User → GET /feedback/  
  ↓  
List feedback (admin sees all; users see their own)

---

## 5. Middleware Stack

### CORS Middleware
- Configure allowed origins, methods, headers
- Credentials setting as needed

### Trusted Host
- Restrict Host header to known domains

### Logging / Audit Middleware
- Request/response metadata (method, path, status, latency)
- User/context correlation IDs
- Error tracking
- Persist to MongoDB (or log sink), with PII minimization

### Authentication Dependency
- Validate JWT Access token (1h)
- Load user and role
- Enforce role checks and ownership policies at routers

Optional:
- Rate limiting on login, seat locks, payments
- Request ID and tracing (OpenTelemetry)

---

## 6. Security & RBAC Summary

- Roles: admin and user (only)
- Access token: 1 hour; Refresh token: 7 days
- Authorization: Bearer <access_token>
- Enforce ownership on user-facing resources (bookings, payments, notifications, feedback)
- Admin writes for catalog, pricing, tax, food, backups, restores
- Seat Lock: Redis TTL to prevent double booking; validate ownership at booking
- Aligns with and retains the existing authentication matrix defined in the Authentication & RBAC documentation

---

## 7. Data Model Overview (Conceptual)

Core entities in PostgreSQL:
- User(id, name, email, phone, role, password_hash, created_at, updated_at)
- Movie, Screen, Seat, SeatCategory
- Show(id, movie_id, screen_id, show_date, show_time, status)
- ShowCategoryPricing(show_id, category_id, price)
- Booking(id, user_id, show_id, status, amount, discount_id?, payment_id?, created_at)
- BookedSeat(booking_id, seat_id, show_id, price, gst_id)
- Payment(id, status, method, transaction_code, amount, refund_amount)
- Discount(id, promo_code, discount_percent)
- GST(id, s_gst, c_gst, gst_category)
- FoodCategory, FoodItem
- BookedFood(booking_id, food_id, quantity, unit_price, gst_id)
- BackupLog, RestoreLog
- Feedback(id, booking_id, user_id, rating, comment, reply, timestamps)

Ephemeral in Redis:
- SeatLock(lock_id, user_id, show_id, seat_ids, locked_at, expires_at, status)

MongoDB (optional):
- Notifications(_id, user_id, booking_id?, type, message, is_read, created_at, read_at)
- Audit logs

---

## 8. Non-Functional Considerations

- Scalability: Horizontal scale FastAPI workers; Redis centralizes seat locks; DB indexing for shows and bookings
- Reliability: Transactions for bookings; idempotent payment callbacks; retry strategies
- Performance: Read-heavy endpoints cached where safe (e.g., show listings)
- Observability: Structured logs, metrics (seat_lock_conflicts, booking_latency), tracing
- Compliance: Secure PII handling; avoid logging secrets/tokens

---

## 9. Contact & Support

Developer: Sylendra Vinayak R  
Documentation: /docs  
Support Email: sylendravinayak@gmail.com

---