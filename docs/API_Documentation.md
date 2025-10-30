# FastAPI API Documentation

**Version:** 0.1.0

**Generated on:** 2025-10-28 12:10:45


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

### DELETE: Delete User

**Description:** 

**Tags:** users


**Parameters:**

- `user_id` (path) — 


**Responses:**

- `200` — Successful Response

- `422` — Validation Error


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
