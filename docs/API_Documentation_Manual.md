# docs_API_Documentation

# Movie Ticket Booking System – API Documentation

Version: 1.0.0
Base URL: https://api.movietix.in/api/v1/
Framework: FastAPI
Content Type: application/json
Authentication: JWT Bearer Token
Last Updated: 2025-11-06

OpenAPI (development hint): GET /openapi.json
Interactive Docs (if enabled): /docs and /redoc

---

## Overview

A role-based movie ticket booking platform.

- Admin — Manage users, movies, screens, seats, shows, pricing, discounts, GST, content
- User — Browse movies, view shows, lock seats, book tickets, manage payments

---

## Roles & Permissions

| Role | Permissions |
| --- | --- |
| Admin | Manage users, movies, screens, seats, seat categories, shows, pricing, tax, food, backups |
| User | View content, find shows, lock seats, book tickets, pay, view notifications |

Use the Authorization header:
Authorization: Bearer

---

## Token Rules

- Access token: 1 hour
- Refresh token: 7 days

---

## Authentication

### Signup

POST /users/signup
Auth: No

Request

```json
{  "name": "Akhil",  "email": "akhil@example.com",  "phone": "9828278289",  "password": "Password@123"}
```

Response 201

```json
{  "user_id": 4,  "name": "Akhil",  "email": "akhil@example.com",  "phone": "9828278289",  "role": "user",  "created_at": "2025-11-06T14:50:17.863031"}
```

### Login

POST /users/login
Auth: No

Request

```json
{  "email": "akhil@example.com",  "password": "Password@123"}
```

Response 200

```json
{  "access_token": "<jwt>",  "token_type": "bearer",  "refresh_token": "<refresh-jwt>"}
```

Notes:
- In some environments, email/password may be accepted as query/form fields. Prefer JSON body where supported.

### Refresh Token

POST /users/refresh
Auth: Yes

Request

```json
{ "refresh_token": "<refresh-jwt>" }
```

Response 200

```json
{ "access_token": "<new-access-jwt>" }
```

---

## Users (Admin)

Base: /users
Tag: users
Auth: Admin required unless stated

### Get All Users

GET /users?skip=0&limit=10&role=user

Query
- skip: int (default 0)
- limit: int (default 10)
- role: string (optional, e.g., “user” or “admin”)

Response 200

```json
[  {    "user_id": 4,    "name": "Akhil",    "email": "akhil@example.com",    "role": "user"  }]
```

### Get User by ID

GET /users/{user_id}

Path
- user_id: int

Response 200

```json
{  "user_id": 4,  "name": "Akhil",  "email": "akhil@example.com",  "role": "user"}
```

### Update User

PUT /users/{user_id}

Path
- user_id: int

Request (example)

```json
{  "name": "Akhil Updated",  "role": "admin"}
```

Response 200

```json
{ "message": "User updated successfully" }
```

### Delete User

DELETE /users/{user_id}

Response 200

```json
{ "message": "User deleted successfully" }
```

---

## Movies

Base: /movies
Auth: Admin for create/update/delete. Read endpoints are public.

### Create Movie

POST /movies/
Auth: Admin

Request

```json
{  "title": "Inception",  "description": "A mind-bending thriller about dream invasion and manipulation.",  "duration": 148,  "language": ["English", "Japanese", "French"],  "release_date": "2010-07-16T00:00:00",  "certificate": "A",  "background_image_url": null,  "cast": [    { "name": "Leonardo DiCaprio", "role": "Hero" },    { "name": "Joseph Gordon-Levitt", "role": "Supporting" }  ],  "crew": [    { "name": "Christopher Nolan", "role": "Director" },    { "name": "Hans Zimmer", "role": "Music" }  ],  "genre": ["Adventure", "Drama", "Science Fiction"],  "rating": 8.8,  "poster_url": "https://example.com/inception-poster.jpg",  "is_active": true}
```

Response 201

```json
{  "movie_id": 1,  "title": "Inception",  "description": "A mind-bending thriller about dream invasion and manipulation.",  "duration": 148,  "language": ["English", "Japanese", "French"],  "release_date": "2010-07-16T00:00:00",  "certificate": "A",  "background_image_url": null,  "cast": [    { "name": "Leonardo DiCaprio", "role": "Hero" },    { "name": "Joseph Gordon-Levitt", "role": "Supporting" }  ],  "crew": [    { "name": "Christopher Nolan", "role": "Director" },    { "name": "Hans Zimmer", "role": "Music" }  ],  "genre": ["Adventure", "Drama", "Science Fiction"],  "rating": 8.8,  "poster_url": "https://example.com/inception-poster.jpg",  "is_active": true}
```

### Get All Movies

GET /movies/?genre=Sci-Fi&language=en&release_date_from=2014-01-01&sort_by=release_date

Filters
- genre: string
- language: string
- release_date_from: ISO date
- sort_by: one of release_date, rating, title

Response 200

```json
[  {    "movie_id": 1,    "title": "Inception",    "description": "A mind-bending thriller about dream invasion and manipulation.",    "duration": 148,    "language": ["English", "Japanese", "French"],    "release_date": "2010-07-16T00:00:00",    "certificate": "A",    "background_image_url": null,    "cast": [      { "name": "Leonardo DiCaprio", "role": "Hero" },      { "name": "Joseph Gordon-Levitt", "role": "Supporting" }    ],    "crew": [      { "name": "Christopher Nolan", "role": "Director" },      { "name": "Hans Zimmer", "role": "Music" }    ],    "genre": ["Sci-Fi"],    "rating": 8.8,    "poster_url": "https://example.com/inception-poster.jpg",    "is_active": true  }]
```

### Get Movie

GET /movies/{movie_id}

Response 200

```json
{  "movie_id": 1,  "title": "Inception",  "description": "A mind-bending thriller about dream invasion and manipulation.",  "duration": 148,  "language": ["English", "Japanese", "French"],  "release_date": "2010-07-16T00:00:00",  "certificate": "A",  "background_image_url": null,  "cast": [    { "name": "Leonardo DiCaprio", "role": "Hero" },    { "name": "Joseph Gordon-Levitt", "role": "Supporting" }  ],  "genre": ["Adventure", "Drama", "Science Fiction"],  "rating": 4.2,  "poster_url": "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",  "is_active": true}
```

### Update Movie

PUT /movies/{movie_id}
Auth: Admin

Request

```json
{ "title": "Leo" }
```

Response 200

```json
{  "movie_id": 1,  "title": "Leo",  "description": "A mind-bending thriller about dream invasion and manipulation.",  "duration": 148,  "language": ["English", "Japanese", "French"],  "release_date": "2010-07-16T00:00:00",  "certificate": "A",  "background_image_url": null,  "cast": [    { "name": "Leonardo DiCaprio", "role": "Hero" },    { "name": "Joseph Gordon-Levitt", "role": "Supporting" }  ],  "genre": ["Adventure", "Drama", "Science Fiction"],  "rating": 4.2,  "poster_url": "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",  "is_active": true}
```

### Delete Movie

DELETE /movies/{movie_id}
Auth: Admin

Response 200

```json
{ "detail": "Movie with ID 1 deleted successfully" }
```

---

## Screens

Base: /screens
Tag: Screens
Auth: Admin for write operations; listing may be public depending on deployment.

### Create Screen

POST /screens/
Auth: Admin

Request

```json
{ "name": "Screen 1", "type": "IMAX", "total_seats": 200 }
```

Response 201

```json
{ "screen_id": 1, "name": "Screen 1", "type": "IMAX", "total_seats": 200, "is_available": true }
```

### Get All Screens

GET /screens/?type=IMAX&is_available=true&skip=0&limit=10

Filters
- type: string
- name: string
- total_seats: int
- is_available: bool
- skip, limit

Response 200

```json
[  {    "screen_id": 1,    "screen_name": "1",    "screen_type": "3D",    "total_seats": 100,    "is_available": true  }]
```

### Get Screen

GET /screens/{screen_id}

Response 200

```json
{ "screen_id": 1, "name": "Screen 1", "type": "IMAX", "total_seats": 200, "is_available": true }
```

### Update Screen

PUT /screens/{screen_id}

Request

```json
{ "total_seats": 100 }
```

Response 200

```json
{  "screen_id": 1,  "screen_name": "1",  "screen_type": "3D",  "total_seats": 100,  "is_available": true}
```

### Delete Screen

DELETE /screens/{screen_id}

Response 200

```json
{ "message": "Screen deleted successfully" }
```

---

## Seats

Base: /seats
Tag: Seats
Auth: Admin for write operations

### Create Seats (bulk)

POST /seats/

Request

```json
[
  {
    "screen_id": 3,
    "row_number": 1,
    "col_number": 1,
    "category_id": 5,
    "seat_number": "A1",
    "is_available": true,
  }
]
```

Response 201

```json
[
  {
    "screen_id": 3,
    "row_number": 1,
    "col_number": 1,
    "category_id": 5,
    "seat_number": "A1",
    "is_available": true,
    "seat_id": 13
  }
]
```

### Get All Seats

GET /seats?skip=0&limit=50

Response 200

```json
[
  {
    "screen_id": 3,
    "row_number": 1,
    "col_number": 1,
    "category_id": 5,
    "seat_number": "A1",
    "is_available": true,
    "seat_id": 13
  }
]
```

### Get Seat

GET /seats/{seat_id}

Response 200

```json
[
  {
    "screen_id": 3,
    "row_number": 1,
    "col_number": 1,
    "category_id": 5,
    "seat_number": "A1",
    "is_available": true,
    "seat_id": 13
  }
]
```

### Update Seat

PUT /seats/{seat_id}

Request

```json
{ "category_id": 3 
```

Response 200

```json
{
  "screen_id": 3,
  "row_number": 1,
  "col_number": 1,
  "category_id": 3,
  "seat_number": "A1",
  "is_available": true,
  "seat_id": 13
}
```

### Delete Seat

DELETE /seats/{seat_id}

Response 200

```json
{ "message": "Seat deleted successfully" }
```

---

## Seat Categories

Base: /seat-categories
Tag: Seat Categories
Auth: Admin for write operations

### Create

POST /seat-categories/

```json
{
  "category_name": "premium",
  "screen_id": 3,
  "rows": 10,
  "cols": 10,
  "base_price": 999.99,
  "category_id": 5
}
```

### List

GET /seat-categories/?skip=0&limit=10

Response 200

```json
[{
  "category_name": "premium",
  "screen_id": 3,
  "rows": 10,
  "cols": 10,
  "base_price": 999.99,
  "category_id": 5
}]
```

### Get

GET /seat-categories/{category_id}

Response 200:

```jsx
{
  "category_name": "premium",
  "screen_id": 3,
  "rows": 10,
  "cols": 10,
  "base_price": 999.99,
  "category_id": 5
}
```

### Update

PUT /seat-categories/{category_id}

path:category_id =5

Request:

```jsx
{
 
  "base_price": 500
}
```

Response 200:

```jsx
{
  "category_name": "premium",
  "screen_id": 3,
  "rows": 10,
  "cols": 10,
  "base_price": 500,
  "category_id": 5
}
```

### Delete

DELETE /seat-categories/{category_id}

Response:

```jsx
{
  "detail": "SeatCategory deleted successfully"
}
```

---

## Shows

Base: /shows
Tag: Shows

### Create Show

POST /shows/
Auth: Admin

Request

```json
{
  "movie_id": 4,
  "screen_id": 3,
  "show_date": "2025-11-06",
  "show_time": "11:11:12.389Z",
  "status": "UPCOMING"
}
```

Response 201

```json
{
  "movie_id": 4,
  "screen_id": 3,
  "show_date": "2025-11-06",
  "show_time": "11:11:12.389000",
  "status": "UPCOMING",
  "show_id": 86,
  "created_at": "2025-11-06T11:11:45.109469+05:30"
}
```

### Get Shows

GET /shows?movie_id=1&screen_id=1&date=2025-11-07&status=scheduled&skip=0&limit=20

Filters: movie_id, screen_id, date, status

Response 200

```json
[
  {
    "movie_id": 4,
    "screen_id": 3,
    "show_date": "2025-11-06",
    "show_time": "11:11:12.389000",
    "status": "UPCOMING",
    "show_id": 86,
    "created_at": "2025-11-06T11:11:45.109469+05:30"
  }
]
```

### Cancel Show

PUT /shows/{show_id}/cancel
Auth: Admin

Response 200

```json
{
  "movie_id": 4,
  "screen_id": 3,
  "show_date": "2025-11-06",
  "show_time": "11:11:12.389000",
  "status": "CANCELLED",
  "show_id": 86,
  "created_at": "2025-11-06T11:11:45.109469+05:30"
}
```

### Available Slots

GET /shows/available-slots?screen_id=1&date=2025-11-10

Response 200

```json
{
"available_slots": [
{
"start": "15:27:12.389000",
"end": "23:59:00"
}
]
}[  { "start_time": "10:00", "end_time": "12:30" },  { "start_time": "13:30", "end_time": "16:00" }]
```

---

## Show Category Pricing

Base: /show-category-pricing
Tag: Pricing
Auth: Admin for all CRUD

- POST /show-category-pricing/
    - Create price for a seat category in a specific show
    - Request
        
        ```json
        {
          "show_id": 1,
          "category_id": 5,
          "price": 500
        }
        
        ```
        
    - Response 201
        
        ```json
        {
          "pricing_id": 14,
          "show_id": 1,
          "category_id": 5,
          "price": 500
        }
        
        ```
        
- GET /show-category-pricing/?show_id=10
    - Query
        - show_id: int (optional)
        - category_id: int (optional)
        - skip, limit (optional)
    - Response 200
        
        ```json
        [
          { "pricing_id": 14, "show_id": 10, "category_id": 2, "price": 450.0 }
        ]
        
        ```
        
- GET /show-category-pricing/{id}
    - Path
        - id: int
    - Response 200
        
        ```json
        { "pricing_id": 14, "show_id": 10, "category_id": 2, "price": 450.0 }
        
        ```
        
    - Errors: 404 Not found
- PUT /show-category-pricing/{id}
    - Request
        
        ```json
        { "price": 475.0 }
        
        ```
        
    - Response 200
        
        ```json
        { "pricing_id": 14, "show_id": 10, "category_id": 2, "price": 475.0 }
        
        ```
        
    - Errors: 404 Not found
- DELETE /show-category-pricing/{id}
    - Response 200
        
        ```json
        { "message": "Pricing deleted successfully" }
        
        ```
        
    - Errors: 404 Not found
    - Base: /seatlocks
    Purpose: Prevent double booking during checkout.

---

## Show Category Pricing

Base: /show-category-pricing
Tag: Pricing
Auth: Admin for all CRUD

- POST /show-category-pricing/
    - Create price for a seat category in a specific show
    - Request
        
        ```json
        {  "show_id": 1,  "category_id": 5,  "price": 500}
        ```
        
    - Response 201
        
        ```json
        {  "pricing_id": 14,  "show_id": 1,  "category_id": 5,  "price": 500}
        ```
        
- GET /show-category-pricing/?show_id=10
    - Query
        - show_id: int (optional)
        - category_id: int (optional)
        - skip, limit (optional)
    - Response 200
        
        ```json
        [  { "pricing_id": 14, "show_id": 10, "category_id": 2, "price": 450.0 }]
        ```
        
- GET /show-category-pricing/{id}
    - Path
        - id: int
    - Response 200
        
        ```json
        { "pricing_id": 14, "show_id": 10, "category_id": 2, "price": 450.0 }
        ```
        
    - Errors: 404 Not found
- PUT /show-category-pricing/{id}
    - Request
        
        ```json
        { "price": 475.0 }
        ```
        
    - Response 200
        
        ```json
        { "pricing_id": 14, "show_id": 10, "category_id": 2, "price": 475.0 }
        ```
        
    - Errors: 404 Not found
- DELETE /show-category-pricing/{id}
    - Response 200
        
        ```json
        { "message": "Pricing deleted successfully" }
        ```
        
    - Errors: 404 Not found

---

## Seat Lock System

Base: /seatlocks
Purpose: Prevent double booking during checkout.
Tag: Seat Locks
Auth: User/Admin

- POST /seatlocks/
    - Lock seat(s) for a show (with TTL)
    - Request
        
        ```json
        { "show_id": 10, "seat_id": 101, "user_id": 4,  "status": "LOCKED",
          "locked_at": "2025-11-06T11:48:26.450Z",
          "expires_at": "2025-11-06T11:58:26.450Z"
          }
        ```
        
    - Response 201
        
        ```json
        { "lock_id":1,
        "show_id": 10, "seat_id": 101, "user_id": 4,  "status": "LOCKED",
          "locked_at": "2025-11-06T11:48:26.450Z",
          "expires_at": "2025-11-06T11:58:26.450Z"
          }
        ```
        
    - Errors: 409 Seat already locked, 404 Show/Seat not found
- GET /seatlocks/?show_id=10
    - Query: show_id (optional), user_id (optional), skip, limit
    - Response 200
        
        ```json
        { "lock_id":1,
        "show_id": 10, "seat_id": 101, "user_id": 4,  "status": "LOCKED",
          "locked_at": "2025-11-06T11:48:26.450Z",
          "expires_at": "2025-11-06T11:58:26.450Z"
          }
        ```
        
- DELETE /seatlocks/{id}
    - Response 200
        
        ```json
        { "message": "Seat lock released" }
        ```
        
    - Errors: 404 Not found
- POST /seatlocks/cleanup
    - Force cleanup of expired locks
    - Response 200
        
        ```json
        { "released_count": 3 }
        ```
        

---

## Bookings

Base: /bookings
Tag: Bookings
Auth: User/Admin

- POST /bookings/
    - Create booking (seats must be locked)
    - Request
        
        ```json
        {
          "user_id": 4,
          "show_id": 1,
          "discount_id": 2,
          "seats": [
            14
          ],
          "foods": [
            {
              "food_id":2,
              "quantity":2
            }
          ]
        }
        ```
        
    - Response 201
        
        ```json
        {
          "booking_id": 63,
          "user_id": 4,
          "show_id": 1,
          "booking_reference": "BKNG-EB24E83E",
          "booking_status": "CONFIRMED",
          "payment_id": 19,
          "discount_id": 2,
          "booking_time": "2025-11-08T13:37:26.287377+05:30",
          "amount": 808,
          "seats": [
            {
              "booking_id": 63,
              "seat_id": 14,
              "show_id": 1,
              "price": 500,
              "gst_id": 1,
              "booked_seat_id": 30
            }
          ],
          "foods": [
            {
              "booking_id": 63,
              "food_id": 2,
              "quantity": 2,
              "unit_price": 100,
              "gst_id": 3,
              "booked_food_id": 25
            }
          ]
        }
        ```
        
    - Errors: 409 Seat not locked / already booked, 400 Invalid payment
- GET /bookings/{booking_id}
    - Response 200
        
        ```json
        [
          {
            "booking_id": 19,
            "user_id": 1,
            "show_id": 1,
            "booking_reference": "BKNG-B1378B0D",
            "booking_status": "PENDING",
            "payment_id": 0,
            "discount_id": 2,
            "booking_time": "2025-10-29T11:22:09.832000+05:30",
            "amount": 527,
            "seats": [
              {
                "booking_id": 19,
                "seat_id": 3,
                "show_id": 1,
                "price": 120,
                "gst_id": 1,
                "booked_seat_id": 1
              },
              {
                "booking_id": 19,
                "seat_id": 8,
                "show_id": 1,
                "price": 120,
                "gst_id": 1,
                "booked_seat_id": 2
              }
            ],
            "foods": [
              {
                "booking_id": 19,
                "food_id": 2,
                "quantity": 2,
                "unit_price": 100,
                "gst_id": 3,
                "booked_food_id": 7
              }
            ]
          },
          {
            "booking_id": 57,
            "user_id": 1,
            "show_id": 30,
            "booking_reference": "BKNG-F8E3894D",
            "booking_status": "CONFIRMED",
            "payment_id": 17,
            "discount_id": 1,
            "booking_time": "2025-11-05T19:58:44.252000+05:30",
            "amount": 898,
            "seats": [
              {
                "booking_id": 57,
                "seat_id": 3,
                "show_id": 30,
                "price": 500,
                "gst_id": 1,
                "booked_seat_id": 28
              }
            ],
            "foods": [
              {
                "booking_id": 57,
                "food_id": 2,
                "quantity": 2,
                "unit_price": 100,
                "gst_id": 3,
                "booked_food_id": 23
              }
            ]
          }
        ]
        ```
        
    - Errors: 404 Not found
- PUT /bookings/{booking_id}/cancel
    - Response 200
        
        ```json
        [
          {
            "status_log_id": 19,
            "booking_id": 63,
            "from_status": null,
            "to_status": "PENDING",
            "changed_at": "2025-11-08T19:07:26.289771+05:30",
            "changed_by": "StatusChangedByEnum.SYSTEM",
            "reason": "Booking created"
          },
          {
            "status_log_id": 20,
            "booking_id": 63,
            "from_status": "PENDING",
            "to_status": "CONFIRMED",
            "changed_at": "2025-11-08T19:07:26.289771+05:30",
            "changed_by": "StatusChangedByEnum.PAYMENT_SERVICE",
            "reason": "Payment succeeded"
          }
        ]
        ```
        
    - Notes: Seats may be released; refunds depend on policy
    
- GET /bookings/{booking_id}/LOGS
    - Response 200
        
        ```json
        {
          "message": "Booking cancelled successfully",
          "booking_id": 63,
          "refund_amount": 0
        }
        ```
        
    - Notes: Seats may be released; refunds depend on policy
    
- GET /bookings/{booking_id}/LOGS
    - Response 200
        
        ```json
        {
          "message": "Booking cancelled successfully",
          "booking_id": 63,
          "refund_amount": 0
        }
        ```
        
    - Notes: Seats may be released; refunds depend on policy
    

---

## Payments

Base: /payments
Tag: Payments
Auth: User/Admin

- GET /payments/?skip=0&limit=10
    - Response 200
    
    [
      {
        "payment_status": "COMPLETED",
        "payment_method": "UPI",
        "transaction_code": "TEST-REF-123",
        "amount": 100,
        "refund_amount": null,
        "payment_id": 2
      },
      {
        "payment_status": "COMPLETED",
        "payment_method": "UPI",
        "transaction_code": "BKNG-4FB7EBA6",
        "amount": 756,
        "refund_amount": null,
        "payment_id": 4
      },
     
    ]
    
- GET /payments/{payment_id}
    - Response 200
        
        ```json
        
          {
            "payment_status": "COMPLETED",
            "payment_method": "UPI",
            "transaction_code": "TEST-REF-123",
            "amount": 100,
            "refund_amount": null,
            "payment_id": 2
          }
        ```
        
- DELETE /payments/{payment_id}
    - Response 200
        
        ```json
        { "message": "Payment deleted successfully" }
        ```
        

---

## Discounts

Base: /discounts
Tag: Discounts
Auth: Admin for write

- POST /discounts/
    - Request
        
        ```json
        
          {
            "promo_code": "diwali10",
            "discount_percent": 10,
          }
        ```
        
    - Response 201
        
        ```json
        
          {
            "promo_code": "diwali10",
            "discount_percent": 10,
            "discount_id": 2
          }
        
        ```
        
- GET /discounts/
    - Response 200
        
        ```json
        [
          {
            "promo_code": "diwali10",
            "discount_percent": 10,
            "discount_id": 2
          }
        ]
        ```
        
- GET /discounts/{discount_id}
    - Response 200
        
        ```json
        
          {
            "promo_code": "diwali10",
            "discount_percent": 10,
            "discount_id": 2
          }
        
        ```
        
    - Errors: 404 Discount not found
- PUT /discounts/{discount_id}
    - Request
        
        ```json
        
          {
            "promo_code": "diwali20",
            "discount_percent": 20
          }
        ```
        
    - Response 200
        
        ```json
        {
          "promo_code": "diwali20",
          "discount_percent": 20,
          "discount_id": 2
        }
        ```
        
- DELETE /discounts/{discount_id}
    - Response 200
        
        ```json
        { "message": "Discount deleted successfully" }
        ```
        

---

## GST (Tax)

Base: /gst
Tag: GST
Auth: Admin

- POST /gst/
    - Request
        
        ```json
        { "s_gst": 10,
            "c_gst": 10,
            "gst_category": "ticket"
         }
        ```
        
    - Response 201
        
        ```json
        { "gst_id": 1,
          "s_gst": 10,
          "c_gst": 10,
           "gst_category": "ticket"
        }
        ```
        
- GET /gst/
    - Response 200
        
        ```json
        [
          {
            "s_gst": 10,
            "c_gst": 10,
            "gst_category": "ticket",
            "gst_id": 1
          },
          {
            "s_gst": 12,
            "c_gst": 12,
            "gst_category": "snacks",
            "gst_id": 2
          },
          {
            "s_gst": 15,
            "c_gst": 14,
            "gst_category": "bevarage",
            "gst_id": 3
          }
        ]
        ```
        
- PUT /gst/{gst_id}
    - Request
        
        ```json
        {
            "s_gst": 15,
            "c_gst": 15,
            "gst_category": "ticket",
         }
        ```
        
    - Response 200
        
        ```json
        { 
        
           "gst_id": 1,
           "s_gst": 10,
           "c_gst": 10,
           "gst_category": "ticket"
        }
        ```
        
    - Errors: 404 GST record not found

---

## Food & Beverages

### Categories

Base: /food-categories
Tag: Food Categories
Auth: Admin for write

- POST /food-categories/
    - Request
        
        ```json
         {"category_name": "bevarages"}
        ```
        
    - Response 201
        
        ```json
        { "category_id": 1, "name": "beverages"}
        ```
        
    - Errors: 400 Food Category already exists
- GET /food-categories/?skip=0&limit=10
    - Response 200
        
        ```json
        [
          {
            "category_name": "bevarages",
            "category_id": 1
          },
          {
            "category_name": "snacks",
            "category_id": 2
          }
        ]
        ```
        
- GET /food-categories/{category_id}
    - Response 200
        
        ```json
        { "category_id": 1, "name": "Beverages"}
        ```
        
    - Errors: 404 Food Category not found
- PUT /food-categories/{category_id}
    - Request
        
        ```json
        { "name": "Snacks"}
        ```
        
    - Response 200
        
        ```json
        { "category_id": 1, "name": "Snacks"}
        ```
        
- DELETE /food-categories/{category_id}
    - Response 200
        
        ```json
        { "message": "Food category deleted successfully" }
        ```
        

### Items

Base: /food-items
Tag: Food Items
Auth: Admin for write

- GET /food-items/?skip=0&limit=10&category_id=1&is_available=true
    - Response 200
        
        ```json
        [
          {
            "item_name": "coke",
            "description": "cool drinks offers refreshing",
            "price": 100,
            "category_id": 2,
            "is_available": true,
            "image_url": "https:/img",
            "food_id": 2
          }
        ]
        ```
        
- GET /food-items/{food_id}
    - Response 200
        
        ```json
        [
          {
            "item_name": "coke",
            "description": "cool drinks offers refreshing",
            "price": 100,
            "category_id": 2,
            "is_available": true,
            "image_url": "https:img",
            "food_id": 2
          }
        ]
        ```
        
    - Errors: 404 Food item not found
- POST /food-items/
    - Request
        
        ```json
        
          {
            "item_name": "coke",
            "description": "cool drinks offers refreshing",
            "price": 100,
            "category_id": 2,
            "is_available": true,
            "image_url": "https:img"
            }
        ```
        
    - Response 201
        
        ```json
        
           {
            "item_name": "coke",
            "description": "cool drinks offers refreshing",
            "price": 100,
            "category_id": 2,
            "is_available": true,
            "image_url": "https:img",
            "food_id":2
            }
        ```
        
- PUT /food-items/{food_id}
    - Request
        
        ```json
        { "price": 175.0}
        ```
        
    - Response 200
        
        ```json
          [
          {
            "item_name": "coke",
            "description": "cool drinks offers refreshing",
            "price": 175,
            "category_id": 2,
            "is_available": true,
            "image_url": "https:img"
            }
          ]
        ```
        
- DELETE /food-items/{food_id}
    - Response 200
        
        ```json
        { "message": "Food item deleted successfully" }
        ```
        

---

## Notifications

Base: /notifications
Tag: Notifications
Auth: User/Admin

- GET /notifications/?skip=0&limit=10&user_id=4
    - Response 200
        
        ```json
        {
            "_id": "690f479cfee4125074b81813",
            "user_id": 4,
            "booking_id": null,
            "notification_type": "BOOKING_CONFIRMED",
            "message": "Your booking BKNG-EB24E83E is confirmed.",
            "is_read": false,
            "created_at": "2025-11-08T13:18:58.656000",
            "read_at": null
          }
        ```
        
- GET /notifications/mark_all_read/{user_id}
    - Response 200
        
        ```json
        {
            "_id": "690f479cfee4125074b81813",
            "user_id": 4,
            "booking_id": null,
            "notification_type": "BOOKING_CONFIRMED",
            "message": "Your booking BKNG-EB24E83E is confirmed.",
            "is_read": true,
            "created_at": "2025-11-08T13:18:58.656000",
            "read_at": "2025-11-10T13:18:58.656000"
          }
        ```
        

---

## Backups

Base: /backup
Tag: Backups
Auth: Admin

- POST /backup/
    - Create backup log entry
    - Request
        
        ```json
        {
          "backupType": "postgres",
          "tables": [
            "bookings"
          ],
          "notes": "booking tables backup"
        }
        ```
        
    - Response 201
        
        ```json
        {
          "operationId": "BKUP-20251108144648",
          "backupType": "postgres",
          "status": "completed",
          "url": "https://github.com/sylendravinayak/backup/blob/main/postgres_backup_20251108_144648.sql",
          "filePath": "postgres_backup_20251108_144648.sql",
          "size": 6372,
          "tables": [
            "bookings"
          ],
          "performedBy": 0,
          "startedAt": "2025-11-08T14:46:48.630000",
          "completedAt": "2025-11-08T14:46:50.615000",
          "errorMessage": null,
          "notes": "booking tables backup",
          "id": "690f57d8d15a0fd355a80ff8"
        }
        ```
        
- GET /backup/?skip=0&limit=10
    - Response 200
        
        ```json
        [ 
        {
          "operationId": "BKUP-20251108144648",
          "backupType": "postgres",
          "status": "completed",
          "url": "https://github.com/sylendravinayak/backup/blob/main/postgres_backup_20251108_144648.sql",
          "filePath": "postgres_backup_20251108_144648.sql",
          "size": 6372,
          "tables": [
            "bookings"
          ],
          "performedBy": 0,
          "startedAt": "2025-11-08T14:46:48.630000",
          "completedAt": "2025-11-08T14:46:50.615000",
          "errorMessage": null,
          "notes": "booking tables backup",
          "id": "690f57d8d15a0fd355a80ff8"
        }
        ]
        ```
        
- GET /backup/{id}
    - Response 200
        
        ```json
        {
          "operationId": "BKUP-20251108144648",
          "backupType": "postgres",
          "status": "completed",
          "url": "https://github.com/sylendravinayak/backup/blob/main/postgres_backup_20251108_144648.sql",
          "filePath": "postgres_backup_20251108_144648.sql",
          "size": 6372,
          "tables": [
            "bookings"
          ],
          "performedBy": 0,
          "startedAt": "2025-11-08T14:46:48.630000",
          "completedAt": "2025-11-08T14:46:50.615000",
          "errorMessage": null,
          "notes": "booking tables backup",
          "id": "690f57d8d15a0fd355a80ff8"
        }
        ```
        
- DELETE /backup/{id}
    - Response 200
        
        ```json
        { "message": "Backup log deleted" }
        ```
        

## Restores

Base: /restores
Tag: Restores
Auth: Admin

- POST /restore/
    - Create restore a existing  backup
    - Request
        
        ```json
        {
          "backupId": "6911f54afa472c3f4056ae24",
          "restoreType": "postgres",
          "notes": "string"
        }
        ```
        
    - Response 201
        
        ```json
        {
          "operationId": "REST-20251112092649",
          "backupType": "postgres",
          "status": "completed",
          "sourceBackupId": "6911f54afa472c3f4056ae24",
          "sourceUrl": "https://github.com/sylendravinayak/backup/blob/main/postgres_backup_20251110_142306.sql",
          "performedBy": 0,
          "startedAt": "2025-11-12T09:26:49.663000",
          "completedAt": "2025-11-12T09:26:51.214000",
          "errorMessage": null,
          "notes": "string",
          "id": "691452d96d0f0c697b3b4a9b"
        }
        ```
        
- GET /restore/?skip=0&limit=10
    - Response 200
        
        ```json
        [ 
        {
          "operationId": "REST-20251112092649",
          "backupType": "postgres",
          "status": "completed",
          "sourceBackupId": "6911f54afa472c3f4056ae24",
          "sourceUrl": "https://github.com/sylendravinayak/backup/blob/main/postgres_backup_20251110_142306.sql",
          "performedBy": 0,
          "startedAt": "2025-11-12T09:26:49.663000",
          "completedAt": "2025-11-12T09:26:51.214000",
          "errorMessage": null,
          "notes": "string",
          "id": "691452d96d0f0c697b3b4a9b"
        }
        ]
        ```
        
- GET /restore/
    - Response 200
        
        ```json
        {
          "operationId": "REST-20251112092649",
          "backupType": "postgres",
          "status": "completed",
          "sourceBackupId": "6911f54afa472c3f4056ae24",
          "sourceUrl": "https://github.com/sylendravinayak/backup/blob/main/postgres_backup_20251110_142306.sql",
          "performedBy": 0,
          "startedAt": "2025-11-12T09:26:49.663000",
          "completedAt": "2025-11-12T09:26:51.214000",
          "errorMessage": null,
          "notes": "string",
          "id": "691452d96d0f0c697b3b4a9b"
        }
        ```
        

---

## Feedback

Base: /feedback
Tag: feedback
Auth: Admin

- POST /feedback/
    - Create feedback
    - Request
        
        ```json
        {
          "booking_id":15,
          "user_id":6,
          "rating": 5,
          "comment": "nice cinematic experience"
        }
        ```
        
    - Response 201
        
        ```json
        {
          "booking_id": 15,
          "user_id": 6,
          "rating": 5,
          "comment": "nice cinematic experience",
          "feedback_id": 5,
          "feedback_date": "2025-11-12T14:43:58.946448+05:30",
          "reply": null
        }
        ```
        
- PUT /feedback/{feedback_id}/reply
    - Create feedback
    - Request
        
        ```json
        {
         "relpy":"Thank you"
        }
        ```
        
    - Response 201
        
        ```json
        {
          "booking_id": 15,
          "user_id": 6,
          "rating": 5,
          "comment": "nice cinematic experience",
          "feedback_id": 5,
          "feedback_date": "2025-11-12T14:43:58.946448+05:30",
          "reply": "thankyou"
        }
        ```
        
- GET  /feedback/
    - Retrive feedback
    - Response 201
        
        ```json
        [{
          "booking_id": 15,
          "user_id": 6,
          "rating": 5,
          "comment": "nice cinematic experience",
          "feedback_id": 5,
          "feedback_date": "2025-11-12T14:43:58.946448+05:30",
          "reply": null
        }]
        ```