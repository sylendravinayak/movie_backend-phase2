# FastAPI API Documentation

**Version:** 0.1.0

**Generated on:** 2025-11-06 14:53:23


---
API Documentation
---


## `/users/signup`

### POST: Signup

**Description:** 

**Tags:** users


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/users/login`

### POST: Login

**Description:** 

**Tags:** users


**Parameters:**

- `email` (query) — 

- `password` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/users/`

### GET: Get All Users

**Description:** 

**Tags:** users


**Parameters:**

- `skip` (query) — 

- `limit` (query) — 

- `role` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/users/{user_id}`

### GET: Get User

**Description:** 

**Tags:** users


**Parameters:**

- `user_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### PUT: Update User

**Description:** 

**Tags:** users


**Parameters:**

- `user_id` (path) — 


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/users/refresh`

### POST: Generate New Access Token

**Description:** 

**Tags:** users


**Responses:**

- `200` — Successful Response


---


## `/movies/`

### POST: Create Movie

**Description:** 

**Tags:** movies


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### GET: Get All Movies

**Description:** 

**Tags:** movies


**Parameters:**

- `skip` (query) — 

- `limit` (query) — 

- `genre` (query) — 

- `language` (query) — 

- `release_date_from` (query) — 

- `sort_by` (query) — Comma-separated sorting fields, e.g. rating:desc,release_date:asc


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/movies/{movie_id}`

### GET: Get Movie

**Description:** 

**Tags:** movies


**Parameters:**

- `movie_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### PUT: Update Movie

**Description:** 

**Tags:** movies


**Parameters:**

- `movie_id` (path) — 


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### DELETE: Delete Movie

**Description:** 

**Tags:** movies


**Parameters:**

- `movie_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/screens/`

### POST: Create Screen

**Description:** Create a new screen

**Tags:** Screens


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### GET: Get All Screens

**Description:** Fetch all screens

**Tags:** Screens


**Parameters:**

- `skip` (query) — 

- `limit` (query) — 

- `name` (query) — 

- `type` (query) — 

- `total_seats` (query) — 

- `is_available` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/screens/{screen_id}`

### GET: Get Screen

**Description:** Fetch a screen by ID

**Tags:** Screens


**Parameters:**

- `screen_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### PUT: Update Screen

**Description:** Update screen details

**Tags:** Screens


**Parameters:**

- `screen_id` (path) — 


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### DELETE: Delete Screen

**Description:** Delete a screen

**Tags:** Screens


**Parameters:**

- `screen_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/seats/`

### POST: Create Seat

**Description:** Create a new seat

**Tags:** Seats


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### GET: Get All Seats

**Description:** Fetch all seats

**Tags:** Seats


**Parameters:**

- `skip` (query) — 

- `limit` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/seats/{seat_id}`

### GET: Get Seat

**Description:** Fetch a seat by ID

**Tags:** Seats


**Parameters:**

- `seat_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### PUT: Update Seat

**Description:** Update seat details

**Tags:** Seats


**Parameters:**

- `seat_id` (path) — 


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### DELETE: Delete Seat

**Description:** Delete a seat

**Tags:** Seats


**Parameters:**

- `seat_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/seat-categories/`

### POST: Create Category

**Description:** 

**Tags:** Seat Categories


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### GET: Get All Categories

**Description:** 

**Tags:** Seat Categories


**Parameters:**

- `screen_id` (query) — 

- `category_name` (query) — 

- `skip` (query) — 

- `limit` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/seat-categories/{category_id}`

### GET: Get Category

**Description:** 

**Tags:** Seat Categories


**Parameters:**

- `category_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### PUT: Update Category

**Description:** 

**Tags:** Seat Categories


**Parameters:**

- `category_id` (path) — 


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### DELETE: Delete Category

**Description:** 

**Tags:** Seat Categories


**Parameters:**

- `category_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/shows/`

### POST: Create Show

**Description:** 

**Tags:** Shows


**Request Body Example:**


**Responses:**

- `201` — Successful Response

- `422` — Validation Error


---

### GET: Get All Shows

**Description:** 

**Tags:** Shows


**Parameters:**

- `skip` (query) — 

- `limit` (query) — 

- `movie_id` (query) — 

- `screen_id` (query) — 

- `status` (query) — 

- `show_date` (query) — Filter by show date (YYYY-MM-DD)


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/shows/{show_id}/cancel`

### PUT: Cancel Show

**Description:** 

**Tags:** Shows


**Parameters:**

- `show_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/shows/auto-schedule`

### POST: Auto Schedule

**Description:** 

**Tags:** Shows


**Parameters:**

- `start_date` (query) — Start date for scheduling (YYYY-MM-DD)


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/shows/available-slots`

### GET: Get Available Slots

**Description:** 

**Tags:** Shows


**Parameters:**

- `screen_id` (query) — 

- `movie_id` (query) — 

- `date` (query) — Date in YYYY-MM-DD format


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/shows/{show_id}`

### GET: Get Show

**Description:** 

**Tags:** Shows


**Parameters:**

- `show_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/show-category-pricing/`

### POST: Create Pricing

**Description:** 

**Tags:** Show Category Pricing


**Request Body Example:**


**Responses:**

- `201` — Successful Response

- `422` — Validation Error


---

### GET: Get All Pricing

**Description:** 

**Tags:** Show Category Pricing


**Parameters:**

- `skip` (query) — 

- `limit` (query) — 

- `show_id` (query) — 

- `category_id` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/show-category-pricing/{pricing_id}`

### GET: Get Pricing

**Description:** 

**Tags:** Show Category Pricing


**Parameters:**

- `pricing_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### PUT: Update Pricing

**Description:** 

**Tags:** Show Category Pricing


**Parameters:**

- `pricing_id` (path) — 


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### DELETE: Delete Pricing

**Description:** 

**Tags:** Show Category Pricing


**Parameters:**

- `pricing_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/seatlocks/`

### POST: Create Seat Lock

**Description:** 

**Tags:** Seat Locks


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### GET: Get All Seat Locks

**Description:** 

**Tags:** Seat Locks


**Parameters:**

- `skip` (query) — 

- `limit` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/seatlocks/{lock_id}`

### GET: Get Seat Lock

**Description:** 

**Tags:** Seat Locks


**Parameters:**

- `lock_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### PUT: Update Seat Lock

**Description:** 

**Tags:** Seat Locks


**Parameters:**

- `lock_id` (path) — 


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### DELETE: Delete Seat Lock

**Description:** 

**Tags:** Seat Locks


**Parameters:**

- `lock_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/seatlocks/cleanup`

### POST: Cleanup Expired Locks

**Description:** 

**Tags:** Seat Locks


**Responses:**

- `200` — Successful Response


---


## `/payments/`

### POST: Create Payment

**Description:** 

**Tags:** Payments


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### GET: Get All Payments

**Description:** 

**Tags:** Payments


**Parameters:**

- `skip` (query) — 

- `limit` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/payments/{payment_id}`

### GET: Get Payment

**Description:** 

**Tags:** Payments


**Parameters:**

- `payment_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### PUT: Update Payment

**Description:** 

**Tags:** Payments


**Parameters:**

- `payment_id` (path) — 


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### DELETE: Delete Payment

**Description:** 

**Tags:** Payments


**Parameters:**

- `payment_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/food-categories/`

### GET: Get All Food Categories

**Description:** 

**Tags:** Food Categories


**Parameters:**

- `skip` (query) — 

- `limit` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### POST: Create Food Category

**Description:** 

**Tags:** Food Categories


**Request Body Example:**


**Responses:**

- `201` — Successful Response

- `422` — Validation Error


---


## `/food-categories/{category_id}`

### GET: Get Food Category

**Description:** 

**Tags:** Food Categories


**Parameters:**

- `category_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### PUT: Update Food Category

**Description:** 

**Tags:** Food Categories


**Parameters:**

- `category_id` (path) — 


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### DELETE: Delete Food Category

**Description:** 

**Tags:** Food Categories


**Parameters:**

- `category_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/food-items/`

### GET: Get All Food Items

**Description:** 

**Tags:** Food Items


**Parameters:**

- `skip` (query) — 

- `limit` (query) — 

- `category_id` (query) — Filter by category_id

- `is_available` (query) — Filter by availability


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### POST: Create Food Item

**Description:** 

**Tags:** Food Items


**Request Body Example:**


**Responses:**

- `201` — Successful Response

- `422` — Validation Error


---


## `/food-items/{food_id}`

### GET: Get Food Item

**Description:** 

**Tags:** Food Items


**Parameters:**

- `food_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### PUT: Update Food Item

**Description:** 

**Tags:** Food Items


**Parameters:**

- `food_id` (path) — 


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### DELETE: Delete Food Item

**Description:** 

**Tags:** Food Items


**Parameters:**

- `food_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/discounts/`

### GET: Get All Discounts

**Description:** 

**Tags:** Discounts


**Responses:**

- `200` — Successful Response


---

### POST: Create Discount

**Description:** 

**Tags:** Discounts


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/discounts/{discount_id}`

### GET: Get Discount

**Description:** 

**Tags:** Discounts


**Parameters:**

- `discount_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### PUT: Update Discount

**Description:** 

**Tags:** Discounts


**Parameters:**

- `discount_id` (path) — 


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### DELETE: Delete Discount

**Description:** 

**Tags:** Discounts


**Parameters:**

- `discount_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/gst/`

### GET: List Gst

**Description:** 

**Tags:** GST


**Responses:**

- `200` — Successful Response


---

### POST: Create Gst

**Description:** 

**Tags:** GST


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/gst/{gst_id}`

### PUT: Update Gst

**Description:** 

**Tags:** GST


**Parameters:**

- `gst_id` (path) — 


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/bookings/`

### GET: Get Bookings

**Description:** 

**Tags:** Bookings


**Parameters:**

- `skip` (query) — 

- `limit` (query) — 

- `user_id` (query) — 

- `show_id` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### POST: Create Booking

**Description:** 

**Tags:** Bookings


**Request Body Example:**


**Responses:**

- `201` — Successful Response

- `422` — Validation Error


---


## `/bookings/{booking_id}/logs`

### GET: Get Booking Logs

**Description:** 

**Tags:** Bookings


**Parameters:**

- `booking_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/bookings/cancel/{booking_id}`

### PUT: Delete Booking

**Description:** 

**Tags:** Bookings


**Parameters:**

- `booking_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/bookings/{booking_id}`

### GET: Get Booking

**Description:** 

**Tags:** Bookings


**Parameters:**

- `booking_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/booked_seats/`

### GET: Get Booked Seats

**Description:** 

**Tags:** Bookings


**Parameters:**

- `skip` (query) — 

- `limit` (query) — 

- `booking_id` (query) — 

- `seat_id` (query) — 

- `show_id` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/backups/`

### POST: Create Backup

**Description:** 

**Tags:** Backups


**Parameters:**

- `admin_id` (query) — ID of the admin/user performing the backup


**Request Body Example:**


**Responses:**

- `201` — Successful Response

- `422` — Validation Error


---

### GET: List Backups

**Description:** 

**Tags:** Backups


**Parameters:**

- `limit` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/backups/{backup_id}`

### GET: Get Backup

**Description:** 

**Tags:** Backups


**Parameters:**

- `backup_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### DELETE: Delete Backup

**Description:** 

**Tags:** Backups


**Parameters:**

- `backup_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/restore/`

### POST: Create Restore

**Description:** 

**Tags:** Restore Logs


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### GET: Get All

**Description:** 

**Tags:** Restore Logs


**Parameters:**

- `skip` (query) — 

- `limit` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/restore/{id}`

### GET: Get Restore

**Description:** 

**Tags:** Restore Logs


**Parameters:**

- `id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### PUT: Update Restore

**Description:** 

**Tags:** Restore Logs


**Parameters:**

- `id` (path) — 


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### DELETE: Delete Restore

**Description:** 

**Tags:** Restore Logs


**Parameters:**

- `id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/notifications/`

### POST: Create Notification

**Description:** 

**Tags:** Notifications


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### GET: Get Notifications

**Description:** 

**Tags:** Notifications


**Parameters:**

- `skip` (query) — 

- `limit` (query) — 

- `user_id` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/notifications/notify`

### GET: Test Notification

**Description:** 

**Tags:** Notifications


**Parameters:**

- `user_id` (query) — 

- `msg` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/notifications/{id}`

### GET: Get Notification

**Description:** 

**Tags:** Notifications


**Parameters:**

- `id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### DELETE: Delete Notification

**Description:** 

**Tags:** Notifications


**Parameters:**

- `id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/notifications/mark-all-read/{user_id}`

### PUT: Mark All Read

**Description:** 

**Tags:** Notifications


**Parameters:**

- `user_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/seatmap/{show_id}`

### GET: Render Seatmap

**Description:** 

**Tags:** Seatmap UI


**Parameters:**

- `show_id` (path) — 

- `user_id` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/feedbacks`

### POST: Create Feedback

**Description:** 

**Tags:** Feedback


**Request Body Example:**


**Responses:**

- `201` — Successful Response

- `422` — Validation Error


---

### GET: List Feedbacks

**Description:** 

**Tags:** Feedback


**Parameters:**

- `skip` (query) — 

- `limit` (query) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---


## `/feedbacks/{feedback_id}`

### GET: Get Feedback

**Description:** 

**Tags:** Feedback


**Parameters:**

- `feedback_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### PATCH: Update Feedback

**Description:** 

**Tags:** Feedback


**Parameters:**

- `feedback_id` (path) — 


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---

### DELETE: Delete Feedback

**Description:** 

**Tags:** Feedback


**Parameters:**

- `feedback_id` (path) — 


**Responses:**

- `204` — Successful Response

- `422` — Validation Error


---


## `/feedbacks/{feedback_id}/reply`

### POST: Reply To Feedback

**Description:** 

**Tags:** Feedback


**Parameters:**

- `feedback_id` (path) — 


**Request Body Example:**


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


---
