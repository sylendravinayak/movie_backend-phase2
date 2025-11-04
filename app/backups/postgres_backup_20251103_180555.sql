--
-- PostgreSQL database dump
--

\restrict e2IEZ0Gie3xhocZxIYhu0coITdiolaNK7syJ3wYX0JXKUlAh1K9tVRo08filqGQ

-- Dumped from database version 17.6
-- Dumped by pg_dump version 17.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY public.shows DROP CONSTRAINT IF EXISTS shows_screen_id_fkey;
ALTER TABLE IF EXISTS ONLY public.shows DROP CONSTRAINT IF EXISTS shows_movie_id_fkey;
ALTER TABLE IF EXISTS ONLY public.show_category_pricing DROP CONSTRAINT IF EXISTS show_category_pricing_category_id_fkey;
ALTER TABLE IF EXISTS ONLY public.seats DROP CONSTRAINT IF EXISTS seats_screen_id_fkey;
ALTER TABLE IF EXISTS ONLY public.seats DROP CONSTRAINT IF EXISTS seats_category_id_fkey;
ALTER TABLE IF EXISTS ONLY public.seat_locks DROP CONSTRAINT IF EXISTS seat_locks_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.seat_locks DROP CONSTRAINT IF EXISTS seat_locks_show_id_fkey;
ALTER TABLE IF EXISTS ONLY public.seat_locks DROP CONSTRAINT IF EXISTS seat_locks_seat_id_fkey;
ALTER TABLE IF EXISTS ONLY public.food_items DROP CONSTRAINT IF EXISTS food_items_category_id_fkey;
ALTER TABLE IF EXISTS ONLY public.booked_seats DROP CONSTRAINT IF EXISTS booked_seats_booking_id_fkey;
DROP INDEX IF EXISTS public.ix_users_user_id;
DROP INDEX IF EXISTS public.ix_users_email;
DROP INDEX IF EXISTS public.ix_shows_show_id;
DROP INDEX IF EXISTS public.ix_shows_show_date;
DROP INDEX IF EXISTS public.ix_shows_screen_id;
DROP INDEX IF EXISTS public.ix_shows_movie_id;
DROP INDEX IF EXISTS public.ix_show_category_pricing_pricing_id;
DROP INDEX IF EXISTS public.ix_seats_seat_id;
DROP INDEX IF EXISTS public.ix_seats_screen_id;
DROP INDEX IF EXISTS public.ix_seats_category_id;
DROP INDEX IF EXISTS public.ix_seat_locks_seat_show;
DROP INDEX IF EXISTS public.ix_seat_locks_lock_id;
DROP INDEX IF EXISTS public.ix_seat_locks_expires_at;
DROP INDEX IF EXISTS public.ix_seat_categories_category_id;
DROP INDEX IF EXISTS public.ix_screens_screen_id;
DROP INDEX IF EXISTS public.ix_pricing_show_id;
DROP INDEX IF EXISTS public.ix_pricing_category_id;
DROP INDEX IF EXISTS public.ix_payments_transaction_code;
DROP INDEX IF EXISTS public.ix_payments_payment_id;
DROP INDEX IF EXISTS public.ix_movies_movie_id;
DROP INDEX IF EXISTS public.ix_gst_gst_id;
DROP INDEX IF EXISTS public.ix_gst_category;
DROP INDEX IF EXISTS public.ix_food_items_food_id;
DROP INDEX IF EXISTS public.ix_food_items_category_id;
DROP INDEX IF EXISTS public.ix_food_categories_category_id;
DROP INDEX IF EXISTS public.ix_discounts_discount_id;
DROP INDEX IF EXISTS public.ix_bookings_user_id;
DROP INDEX IF EXISTS public.ix_bookings_show_id;
DROP INDEX IF EXISTS public.ix_bookings_payment_id;
DROP INDEX IF EXISTS public.ix_bookings_discount_id;
DROP INDEX IF EXISTS public.ix_bookings_booking_reference;
DROP INDEX IF EXISTS public.ix_bookings_booking_id;
DROP INDEX IF EXISTS public.ix_booking_status_status_log_id;
DROP INDEX IF EXISTS public.ix_booking_status_changed_at;
DROP INDEX IF EXISTS public.ix_booking_status_booking_id;
DROP INDEX IF EXISTS public.ix_booked_seats_show_id;
DROP INDEX IF EXISTS public.ix_booked_seats_seat_id;
DROP INDEX IF EXISTS public.ix_booked_seats_gst_id;
DROP INDEX IF EXISTS public.ix_booked_seats_booking_id;
DROP INDEX IF EXISTS public.ix_booked_seats_booked_seat_id;
DROP INDEX IF EXISTS public.ix_booked_food_gst_id;
DROP INDEX IF EXISTS public.ix_booked_food_food_id;
DROP INDEX IF EXISTS public.ix_booked_food_booking_id;
DROP INDEX IF EXISTS public.ix_booked_food_booked_food_id;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_phone_key;
ALTER TABLE IF EXISTS ONLY public.seats DROP CONSTRAINT IF EXISTS uq_seat_screen_seatnum;
ALTER TABLE IF EXISTS ONLY public.shows DROP CONSTRAINT IF EXISTS uq_screen_date_time;
ALTER TABLE IF EXISTS ONLY public.show_category_pricing DROP CONSTRAINT IF EXISTS uq_pricing_show_category;
ALTER TABLE IF EXISTS ONLY public.booked_seats DROP CONSTRAINT IF EXISTS uq_booked_seat_seat_show;
ALTER TABLE IF EXISTS ONLY public.booked_seats DROP CONSTRAINT IF EXISTS uq_booked_seat_booking_seat;
ALTER TABLE IF EXISTS ONLY public.shows DROP CONSTRAINT IF EXISTS shows_pkey;
ALTER TABLE IF EXISTS ONLY public.show_category_pricing DROP CONSTRAINT IF EXISTS show_category_pricing_pkey;
ALTER TABLE IF EXISTS ONLY public.seats DROP CONSTRAINT IF EXISTS seats_pkey;
ALTER TABLE IF EXISTS ONLY public.seat_locks DROP CONSTRAINT IF EXISTS seat_locks_pkey;
ALTER TABLE IF EXISTS ONLY public.seat_categories DROP CONSTRAINT IF EXISTS seat_categories_pkey;
ALTER TABLE IF EXISTS ONLY public.screens DROP CONSTRAINT IF EXISTS screens_pkey;
ALTER TABLE IF EXISTS ONLY public.payments DROP CONSTRAINT IF EXISTS payments_pkey;
ALTER TABLE IF EXISTS ONLY public.movies DROP CONSTRAINT IF EXISTS movies_pkey;
ALTER TABLE IF EXISTS ONLY public.gst DROP CONSTRAINT IF EXISTS gst_pkey;
ALTER TABLE IF EXISTS ONLY public.food_items DROP CONSTRAINT IF EXISTS food_items_pkey;
ALTER TABLE IF EXISTS ONLY public.food_categories DROP CONSTRAINT IF EXISTS food_categories_pkey;
ALTER TABLE IF EXISTS ONLY public.food_categories DROP CONSTRAINT IF EXISTS food_categories_category_name_key;
ALTER TABLE IF EXISTS ONLY public.discounts DROP CONSTRAINT IF EXISTS discounts_promo_code_key;
ALTER TABLE IF EXISTS ONLY public.discounts DROP CONSTRAINT IF EXISTS discounts_pkey;
ALTER TABLE IF EXISTS ONLY public.bookings DROP CONSTRAINT IF EXISTS bookings_pkey;
ALTER TABLE IF EXISTS ONLY public.booking_status DROP CONSTRAINT IF EXISTS booking_status_pkey;
ALTER TABLE IF EXISTS ONLY public.booked_seats DROP CONSTRAINT IF EXISTS booked_seats_pkey;
ALTER TABLE IF EXISTS ONLY public.booked_food DROP CONSTRAINT IF EXISTS booked_food_pkey;
ALTER TABLE IF EXISTS public.users ALTER COLUMN user_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.shows ALTER COLUMN show_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.show_category_pricing ALTER COLUMN pricing_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.seats ALTER COLUMN seat_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.seat_locks ALTER COLUMN lock_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.seat_categories ALTER COLUMN category_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.screens ALTER COLUMN screen_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.payments ALTER COLUMN payment_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.movies ALTER COLUMN movie_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.gst ALTER COLUMN gst_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.food_items ALTER COLUMN food_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.food_categories ALTER COLUMN category_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.discounts ALTER COLUMN discount_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.bookings ALTER COLUMN booking_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.booking_status ALTER COLUMN status_log_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.booked_seats ALTER COLUMN booked_seat_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.booked_food ALTER COLUMN booked_food_id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.users_user_id_seq;
DROP TABLE IF EXISTS public.users;
DROP SEQUENCE IF EXISTS public.shows_show_id_seq;
DROP TABLE IF EXISTS public.shows;
DROP SEQUENCE IF EXISTS public.show_category_pricing_pricing_id_seq;
DROP TABLE IF EXISTS public.show_category_pricing;
DROP SEQUENCE IF EXISTS public.seats_seat_id_seq;
DROP TABLE IF EXISTS public.seats;
DROP SEQUENCE IF EXISTS public.seat_locks_lock_id_seq;
DROP TABLE IF EXISTS public.seat_locks;
DROP SEQUENCE IF EXISTS public.seat_categories_category_id_seq;
DROP TABLE IF EXISTS public.seat_categories;
DROP SEQUENCE IF EXISTS public.screens_screen_id_seq;
DROP TABLE IF EXISTS public.screens;
DROP SEQUENCE IF EXISTS public.payments_payment_id_seq;
DROP TABLE IF EXISTS public.payments;
DROP SEQUENCE IF EXISTS public.movies_movie_id_seq;
DROP TABLE IF EXISTS public.movies;
DROP SEQUENCE IF EXISTS public.gst_gst_id_seq;
DROP TABLE IF EXISTS public.gst;
DROP SEQUENCE IF EXISTS public.food_items_food_id_seq;
DROP TABLE IF EXISTS public.food_items;
DROP SEQUENCE IF EXISTS public.food_categories_category_id_seq;
DROP TABLE IF EXISTS public.food_categories;
DROP SEQUENCE IF EXISTS public.discounts_discount_id_seq;
DROP TABLE IF EXISTS public.discounts;
DROP SEQUENCE IF EXISTS public.bookings_booking_id_seq;
DROP TABLE IF EXISTS public.bookings;
DROP SEQUENCE IF EXISTS public.booking_status_status_log_id_seq;
DROP TABLE IF EXISTS public.booking_status;
DROP SEQUENCE IF EXISTS public.booked_seats_booked_seat_id_seq;
DROP TABLE IF EXISTS public.booked_seats;
DROP SEQUENCE IF EXISTS public.booked_food_booked_food_id_seq;
DROP TABLE IF EXISTS public.booked_food;
DROP TYPE IF EXISTS public.status_changed_by_enum;
DROP TYPE IF EXISTS public.show_status_enum;
DROP TYPE IF EXISTS public.seat_lock_status_enum;
DROP TYPE IF EXISTS public.payment_status_enum;
DROP TYPE IF EXISTS public.payment_method_enum;
DROP TYPE IF EXISTS public.booking_status_enum;
--
-- Name: booking_status_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.booking_status_enum AS ENUM (
    'PENDING',
    'CONFIRMED',
    'CANCELLED'
);


ALTER TYPE public.booking_status_enum OWNER TO postgres;

--
-- Name: payment_method_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.payment_method_enum AS ENUM (
    'UPI',
    'CARD',
    'WALLET'
);


ALTER TYPE public.payment_method_enum OWNER TO postgres;

--
-- Name: payment_status_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.payment_status_enum AS ENUM (
    'COMPLETED',
    'FAILED',
    'REFUNDED'
);


ALTER TYPE public.payment_status_enum OWNER TO postgres;

--
-- Name: seat_lock_status_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.seat_lock_status_enum AS ENUM (
    'LOCKED',
    'BOOKED'
);


ALTER TYPE public.seat_lock_status_enum OWNER TO postgres;

--
-- Name: show_status_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.show_status_enum AS ENUM (
    'UPCOMING',
    'ONGOING',
    'COMPLETED',
    'CANCELLED'
);


ALTER TYPE public.show_status_enum OWNER TO postgres;

--
-- Name: status_changed_by_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.status_changed_by_enum AS ENUM (
    'USER',
    'SYSTEM',
    'ADMIN',
    'PAYMENT_SERVICE'
);


ALTER TYPE public.status_changed_by_enum OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: booked_food; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.booked_food (
    booked_food_id integer NOT NULL,
    booking_id integer NOT NULL,
    food_id integer NOT NULL,
    quantity integer NOT NULL,
    unit_price numeric(10,2) NOT NULL,
    gst_id integer,
    CONSTRAINT ck_booked_food_quantity_gt_0 CHECK ((quantity > 0))
);


ALTER TABLE public.booked_food OWNER TO postgres;

--
-- Name: booked_food_booked_food_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.booked_food_booked_food_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.booked_food_booked_food_id_seq OWNER TO postgres;

--
-- Name: booked_food_booked_food_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.booked_food_booked_food_id_seq OWNED BY public.booked_food.booked_food_id;


--
-- Name: booked_seats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.booked_seats (
    booked_seat_id integer NOT NULL,
    booking_id integer NOT NULL,
    seat_id integer NOT NULL,
    price numeric(10,2) NOT NULL,
    show_id integer NOT NULL,
    gst_id integer
);


ALTER TABLE public.booked_seats OWNER TO postgres;

--
-- Name: booked_seats_booked_seat_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.booked_seats_booked_seat_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.booked_seats_booked_seat_id_seq OWNER TO postgres;

--
-- Name: booked_seats_booked_seat_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.booked_seats_booked_seat_id_seq OWNED BY public.booked_seats.booked_seat_id;


--
-- Name: booking_status; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.booking_status (
    status_log_id integer NOT NULL,
    booking_id integer NOT NULL,
    from_status public.booking_status_enum,
    to_status public.booking_status_enum NOT NULL,
    changed_at timestamp with time zone DEFAULT now() NOT NULL,
    changed_by public.status_changed_by_enum,
    reason text
);


ALTER TABLE public.booking_status OWNER TO postgres;

--
-- Name: booking_status_status_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.booking_status_status_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.booking_status_status_log_id_seq OWNER TO postgres;

--
-- Name: booking_status_status_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.booking_status_status_log_id_seq OWNED BY public.booking_status.status_log_id;


--
-- Name: bookings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bookings (
    booking_id integer NOT NULL,
    user_id integer NOT NULL,
    show_id integer NOT NULL,
    booking_date timestamp with time zone DEFAULT now() NOT NULL,
    booking_reference character varying(20) NOT NULL,
    booking_status public.booking_status_enum DEFAULT 'PENDING'::public.booking_status_enum NOT NULL,
    payment_id integer,
    discount_id integer,
    booking_time timestamp with time zone NOT NULL,
    amount integer
);


ALTER TABLE public.bookings OWNER TO postgres;

--
-- Name: bookings_booking_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.bookings_booking_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bookings_booking_id_seq OWNER TO postgres;

--
-- Name: bookings_booking_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.bookings_booking_id_seq OWNED BY public.bookings.booking_id;


--
-- Name: discounts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.discounts (
    discount_id integer NOT NULL,
    promo_code character varying(50) NOT NULL,
    discount_percent integer NOT NULL
);


ALTER TABLE public.discounts OWNER TO postgres;

--
-- Name: discounts_discount_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.discounts_discount_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.discounts_discount_id_seq OWNER TO postgres;

--
-- Name: discounts_discount_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.discounts_discount_id_seq OWNED BY public.discounts.discount_id;


--
-- Name: food_categories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.food_categories (
    category_id integer NOT NULL,
    category_name character varying(50) NOT NULL
);


ALTER TABLE public.food_categories OWNER TO postgres;

--
-- Name: food_categories_category_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.food_categories_category_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.food_categories_category_id_seq OWNER TO postgres;

--
-- Name: food_categories_category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.food_categories_category_id_seq OWNED BY public.food_categories.category_id;


--
-- Name: food_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.food_items (
    food_id integer NOT NULL,
    item_name character varying(100) NOT NULL,
    description text,
    price numeric(10,2) NOT NULL,
    category_id integer,
    is_available boolean DEFAULT true NOT NULL,
    image_url character varying(255)
);


ALTER TABLE public.food_items OWNER TO postgres;

--
-- Name: food_items_food_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.food_items_food_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.food_items_food_id_seq OWNER TO postgres;

--
-- Name: food_items_food_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.food_items_food_id_seq OWNED BY public.food_items.food_id;


--
-- Name: gst; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.gst (
    gst_id integer NOT NULL,
    s_gst integer NOT NULL,
    c_gst integer NOT NULL,
    gst_category character varying(100) NOT NULL
);


ALTER TABLE public.gst OWNER TO postgres;

--
-- Name: gst_gst_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.gst_gst_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gst_gst_id_seq OWNER TO postgres;

--
-- Name: gst_gst_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.gst_gst_id_seq OWNED BY public.gst.gst_id;


--
-- Name: movies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.movies (
    movie_id integer NOT NULL,
    title character varying(200) NOT NULL,
    description character varying(1000),
    duration integer NOT NULL,
    genre character varying(50)[],
    language character varying(50)[],
    release_date timestamp without time zone,
    rating double precision,
    certificate character varying(10),
    poster_url character varying(255),
    background_image_url character varying(255),
    is_active boolean,
    "cast" json,
    crew json
);


ALTER TABLE public.movies OWNER TO postgres;

--
-- Name: movies_movie_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.movies_movie_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.movies_movie_id_seq OWNER TO postgres;

--
-- Name: movies_movie_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.movies_movie_id_seq OWNED BY public.movies.movie_id;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.payments (
    payment_id integer NOT NULL,
    payment_status public.payment_status_enum NOT NULL,
    payment_method public.payment_method_enum NOT NULL,
    transaction_code character varying(50) NOT NULL,
    amount integer NOT NULL,
    refund_amount integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.payments OWNER TO postgres;

--
-- Name: payments_payment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.payments_payment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payments_payment_id_seq OWNER TO postgres;

--
-- Name: payments_payment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.payments_payment_id_seq OWNED BY public.payments.payment_id;


--
-- Name: screens; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.screens (
    screen_id integer NOT NULL,
    screen_name character varying(100) NOT NULL,
    total_seats integer NOT NULL,
    screen_type character varying(50) NOT NULL,
    is_available boolean
);


ALTER TABLE public.screens OWNER TO postgres;

--
-- Name: screens_screen_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.screens_screen_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.screens_screen_id_seq OWNER TO postgres;

--
-- Name: screens_screen_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.screens_screen_id_seq OWNED BY public.screens.screen_id;


--
-- Name: seat_categories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.seat_categories (
    category_id integer NOT NULL,
    category_name character varying(100) NOT NULL,
    screen_id integer NOT NULL,
    rows integer NOT NULL,
    cols integer NOT NULL,
    base_price double precision NOT NULL
);


ALTER TABLE public.seat_categories OWNER TO postgres;

--
-- Name: seat_categories_category_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seat_categories_category_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.seat_categories_category_id_seq OWNER TO postgres;

--
-- Name: seat_categories_category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.seat_categories_category_id_seq OWNED BY public.seat_categories.category_id;


--
-- Name: seat_locks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.seat_locks (
    lock_id integer NOT NULL,
    seat_id integer NOT NULL,
    show_id integer NOT NULL,
    user_id integer NOT NULL,
    status public.seat_lock_status_enum DEFAULT 'LOCKED'::public.seat_lock_status_enum NOT NULL,
    locked_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL
);


ALTER TABLE public.seat_locks OWNER TO postgres;

--
-- Name: seat_locks_lock_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seat_locks_lock_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.seat_locks_lock_id_seq OWNER TO postgres;

--
-- Name: seat_locks_lock_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.seat_locks_lock_id_seq OWNED BY public.seat_locks.lock_id;


--
-- Name: seats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.seats (
    seat_id integer NOT NULL,
    screen_id integer NOT NULL,
    row_number integer NOT NULL,
    col_number integer NOT NULL,
    category_id integer,
    seat_number character varying(10) NOT NULL,
    is_available boolean NOT NULL
);


ALTER TABLE public.seats OWNER TO postgres;

--
-- Name: seats_seat_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seats_seat_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.seats_seat_id_seq OWNER TO postgres;

--
-- Name: seats_seat_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.seats_seat_id_seq OWNED BY public.seats.seat_id;


--
-- Name: show_category_pricing; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.show_category_pricing (
    pricing_id integer NOT NULL,
    show_id integer NOT NULL,
    category_id integer NOT NULL,
    price numeric(10,2) NOT NULL
);


ALTER TABLE public.show_category_pricing OWNER TO postgres;

--
-- Name: show_category_pricing_pricing_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.show_category_pricing_pricing_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.show_category_pricing_pricing_id_seq OWNER TO postgres;

--
-- Name: show_category_pricing_pricing_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.show_category_pricing_pricing_id_seq OWNED BY public.show_category_pricing.pricing_id;


--
-- Name: shows; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.shows (
    show_id integer NOT NULL,
    movie_id integer NOT NULL,
    screen_id integer NOT NULL,
    show_date date NOT NULL,
    show_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    status public.show_status_enum DEFAULT 'UPCOMING'::public.show_status_enum NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.shows OWNER TO postgres;

--
-- Name: shows_show_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.shows_show_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.shows_show_id_seq OWNER TO postgres;

--
-- Name: shows_show_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.shows_show_id_seq OWNED BY public.shows.show_id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    name character varying(100) NOT NULL,
    email character varying(100) NOT NULL,
    phone character varying(15) NOT NULL,
    password character varying(255) NOT NULL,
    created_at timestamp without time zone,
    role character varying(15) NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_user_id_seq OWNER TO postgres;

--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- Name: booked_food booked_food_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booked_food ALTER COLUMN booked_food_id SET DEFAULT nextval('public.booked_food_booked_food_id_seq'::regclass);


--
-- Name: booked_seats booked_seat_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booked_seats ALTER COLUMN booked_seat_id SET DEFAULT nextval('public.booked_seats_booked_seat_id_seq'::regclass);


--
-- Name: booking_status status_log_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booking_status ALTER COLUMN status_log_id SET DEFAULT nextval('public.booking_status_status_log_id_seq'::regclass);


--
-- Name: bookings booking_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings ALTER COLUMN booking_id SET DEFAULT nextval('public.bookings_booking_id_seq'::regclass);


--
-- Name: discounts discount_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discounts ALTER COLUMN discount_id SET DEFAULT nextval('public.discounts_discount_id_seq'::regclass);


--
-- Name: food_categories category_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.food_categories ALTER COLUMN category_id SET DEFAULT nextval('public.food_categories_category_id_seq'::regclass);


--
-- Name: food_items food_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.food_items ALTER COLUMN food_id SET DEFAULT nextval('public.food_items_food_id_seq'::regclass);


--
-- Name: gst gst_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gst ALTER COLUMN gst_id SET DEFAULT nextval('public.gst_gst_id_seq'::regclass);


--
-- Name: movies movie_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.movies ALTER COLUMN movie_id SET DEFAULT nextval('public.movies_movie_id_seq'::regclass);


--
-- Name: payments payment_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments ALTER COLUMN payment_id SET DEFAULT nextval('public.payments_payment_id_seq'::regclass);


--
-- Name: screens screen_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.screens ALTER COLUMN screen_id SET DEFAULT nextval('public.screens_screen_id_seq'::regclass);


--
-- Name: seat_categories category_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seat_categories ALTER COLUMN category_id SET DEFAULT nextval('public.seat_categories_category_id_seq'::regclass);


--
-- Name: seat_locks lock_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seat_locks ALTER COLUMN lock_id SET DEFAULT nextval('public.seat_locks_lock_id_seq'::regclass);


--
-- Name: seats seat_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seats ALTER COLUMN seat_id SET DEFAULT nextval('public.seats_seat_id_seq'::regclass);


--
-- Name: show_category_pricing pricing_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.show_category_pricing ALTER COLUMN pricing_id SET DEFAULT nextval('public.show_category_pricing_pricing_id_seq'::regclass);


--
-- Name: shows show_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shows ALTER COLUMN show_id SET DEFAULT nextval('public.shows_show_id_seq'::regclass);


--
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Data for Name: booked_food; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.booked_food (booked_food_id, booking_id, food_id, quantity, unit_price, gst_id) FROM stdin;
1	13	2	2	100.00	3
2	14	2	2	100.00	3
3	15	2	2	100.00	3
4	16	2	2	100.00	3
5	17	2	2	100.00	3
6	18	2	2	100.00	3
7	19	2	2	100.00	3
11	32	2	2	100.00	3
12	42	2	1	100.00	3
13	43	2	1	100.00	3
15	45	2	1	100.00	3
\.


--
-- Data for Name: booked_seats; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.booked_seats (booked_seat_id, booking_id, seat_id, price, show_id, gst_id) FROM stdin;
1	19	3	120.00	1	1
2	19	8	120.00	1	1
6	32	3	500.00	3	1
7	32	8	500.00	3	1
8	36	8	700.00	4	1
9	37	3	700.00	4	1
10	42	3	999.99	20	1
11	42	8	999.99	20	1
12	43	3	999.99	19	1
13	43	8	999.99	19	1
15	45	3	999.99	18	1
16	45	8	999.99	18	1
\.


--
-- Data for Name: booking_status; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.booking_status (status_log_id, booking_id, from_status, to_status, changed_at, changed_by, reason) FROM stdin;
1	46	\N	PENDING	2025-11-03 19:37:43.640317+05:30	SYSTEM	Booking created
2	46	PENDING	CONFIRMED	2025-11-03 19:37:43.640317+05:30	PAYMENT_SERVICE	Payment succeeded
3	46	CONFIRMED	CANCELLED	2025-11-03 19:39:17.716384+05:30	USER	User-initiated cancellation
4	47	\N	PENDING	2025-11-03 19:47:16.393376+05:30	SYSTEM	Booking created
5	47	PENDING	CONFIRMED	2025-11-03 19:47:16.393376+05:30	PAYMENT_SERVICE	Payment succeeded
6	47	CONFIRMED	CANCELLED	2025-11-03 19:48:40.054638+05:30	USER	User-initiated cancellation
7	48	\N	PENDING	2025-11-03 20:43:06.76044+05:30	SYSTEM	Booking created
8	48	PENDING	CONFIRMED	2025-11-03 20:43:06.76044+05:30	PAYMENT_SERVICE	Payment succeeded
9	48	CONFIRMED	CANCELLED	2025-11-03 20:53:14.115816+05:30	USER	User-initiated cancellation
10	50	\N	PENDING	2025-11-03 20:54:54.178807+05:30	SYSTEM	Booking created
11	50	PENDING	CONFIRMED	2025-11-03 20:54:54.178807+05:30	PAYMENT_SERVICE	Payment succeeded
12	50	CONFIRMED	CANCELLED	2025-11-03 20:56:48.7336+05:30	USER	User-initiated cancellation
13	47	CANCELLED	CANCELLED	2025-11-03 20:59:31.633102+05:30	USER	User-initiated cancellation
14	46	CANCELLED	CANCELLED	2025-11-03 21:00:20.094425+05:30	USER	User-initiated cancellation
\.


--
-- Data for Name: bookings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.bookings (booking_id, user_id, show_id, booking_date, booking_reference, booking_status, payment_id, discount_id, booking_time, amount) FROM stdin;
48	1	22	2025-11-03 20:43:06.76044+05:30	BKNG-69037D5B	CANCELLED	12	2	2025-11-03 19:19:08.431+05:30	2294
50	1	23	2025-11-03 20:54:54.178807+05:30	BKNG-B19171C9	CANCELLED	13	2	2025-11-03 19:19:08.431+05:30	2294
14	1	1	2025-10-29 12:37:10.186329+05:30	BKNG-E3E985BC	PENDING	0	2	2025-10-29 11:22:09.832+05:30	475
15	1	1	2025-10-29 12:52:11.429377+05:30	BKNG-AE89AD42	PENDING	0	2	2025-10-29 11:22:09.832+05:30	527
16	1	1	2025-10-29 12:53:25.287824+05:30	BKNG-8763CA2D	PENDING	0	2	2025-10-29 11:22:09.832+05:30	527
17	1	1	2025-10-29 12:53:40.492283+05:30	BKNG-58DE7F84	PENDING	0	2	2025-10-29 11:22:09.832+05:30	527
18	1	1	2025-10-29 12:53:47.424883+05:30	BKNG-6BAF445F	PENDING	0	2	2025-10-29 11:22:09.832+05:30	527
19	1	1	2025-10-29 12:56:40.271618+05:30	BKNG-B1378B0D	PENDING	0	2	2025-10-29 11:22:09.832+05:30	527
36	3	4	2025-10-31 16:04:38.092235+05:30	BKNG-4FB7EBA6	CONFIRMED	4	2	2025-10-31 16:04:38.084+05:30	756
37	1	4	2025-10-31 16:05:08.598678+05:30	BKNG-98CF63EB	CONFIRMED	5	2	2025-10-31 16:05:08.591+05:30	756
13	1	1	2025-10-29 12:33:25.404591+05:30	BKNG-D01CEEF2	CANCELLED	0	2	2025-10-29 11:22:09.832+05:30	475
32	1	3	2025-10-31 11:21:55.358059+05:30	BKNG-7950C041	CANCELLED	3	2	2025-10-31 10:01:26.106+05:30	1348
42	1	20	2025-11-03 19:23:23.589109+05:30	BKNG-2D7A2458	CONFIRMED	6	2	2025-11-03 19:19:08.431+05:30	2294
43	1	19	2025-11-03 19:30:35.186719+05:30	BKNG-3150E537	CONFIRMED	7	2	2025-11-03 19:19:08.431+05:30	2294
45	1	18	2025-11-03 19:33:28.907204+05:30	BKNG-3BB6D972	CONFIRMED	9	2	2025-11-03 19:19:08.431+05:30	2294
46	1	17	2025-11-03 19:37:43.640317+05:30	BKNG-42F4C1AE	CANCELLED	10	2	2025-11-03 19:19:08.431+05:30	2294
47	1	21	2025-11-03 19:47:16.393376+05:30	BKNG-9F5B82EC	CANCELLED	11	2	2025-11-03 19:19:08.431+05:30	2294
\.


--
-- Data for Name: discounts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.discounts (discount_id, promo_code, discount_percent) FROM stdin;
2	diwali10	10
\.


--
-- Data for Name: food_categories; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.food_categories (category_id, category_name) FROM stdin;
1	bevarages
2	snacks
\.


--
-- Data for Name: food_items; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.food_items (food_id, item_name, description, price, category_id, is_available, image_url) FROM stdin;
2	coke	string	100.00	2	t	string
\.


--
-- Data for Name: gst; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.gst (gst_id, s_gst, c_gst, gst_category) FROM stdin;
1	10	10	ticket
2	12	12	snacks
3	15	14	bevarage
\.


--
-- Data for Name: movies; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.movies (movie_id, title, description, duration, genre, language, release_date, rating, certificate, poster_url, background_image_url, is_active, "cast", crew) FROM stdin;
1	Inception	A mind-bending thriller about dream invasion and manipulation.	148	{Sci-Fi}	{English,Japanese,French}	2010-07-16 00:00:00	8.8	A	https://example.com/inception-poster.jpg	\N	t	[{"name": "Leonardo DiCaprio", "role": "Hero"}, {"name": "Joseph Gordon-Levitt", "role": "Supporting"}]	[{"name": "Christopher Nolan", "role": "Director"}, {"name": "Hans Zimmer", "role": "Music"}]
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.payments (payment_id, payment_status, payment_method, transaction_code, amount, refund_amount, created_at) FROM stdin;
2	COMPLETED	UPI	TEST-REF-123	100	\N	2025-10-31 11:19:59.454316+05:30
4	COMPLETED	UPI	BKNG-4FB7EBA6	756	\N	2025-10-31 16:04:38.220441+05:30
5	COMPLETED	UPI	BKNG-98CF63EB	756	\N	2025-10-31 16:05:08.609998+05:30
3	REFUNDED	UPI	BKNG-7950C041	1347	0	2025-10-31 11:21:55.568027+05:30
6	COMPLETED	UPI	BKNG-2D7A2458	2293	\N	2025-11-03 19:23:23.798837+05:30
7	COMPLETED	UPI	BKNG-3150E537	2293	\N	2025-11-03 19:30:35.261897+05:30
8	COMPLETED	UPI	BKNG-81E140D2	2293	\N	2025-11-03 19:32:17.785538+05:30
9	COMPLETED	UPI	BKNG-3BB6D972	2293	\N	2025-11-03 19:33:28.927604+05:30
10	REFUNDED	UPI	BKNG-42F4C1AE	2293	1835	2025-11-03 19:37:43.701703+05:30
11	REFUNDED	UPI	BKNG-9F5B82EC	2293	1835	2025-11-03 19:47:16.493438+05:30
12	REFUNDED	UPI	BKNG-69037D5B	2293	1835	2025-11-03 20:43:06.951402+05:30
13	REFUNDED	UPI	BKNG-B19171C9	2293	1835	2025-11-03 20:54:54.40306+05:30
\.


--
-- Data for Name: screens; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.screens (screen_id, screen_name, total_seats, screen_type, is_available) FROM stdin;
1	1	100	3D	t
\.


--
-- Data for Name: seat_categories; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.seat_categories (category_id, category_name, screen_id, rows, cols, base_price) FROM stdin;
1	premium	1	10	10	999.99
\.


--
-- Data for Name: seat_locks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.seat_locks (lock_id, seat_id, show_id, user_id, status, locked_at, expires_at) FROM stdin;
\.


--
-- Data for Name: seats; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.seats (seat_id, screen_id, row_number, col_number, category_id, seat_number, is_available) FROM stdin;
3	1	1	1	1	A2	t
8	1	0	0	1	string	t
\.


--
-- Data for Name: show_category_pricing; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.show_category_pricing (pricing_id, show_id, category_id, price) FROM stdin;
2	1	1	120.00
3	3	1	500.00
4	4	1	700.00
5	20	1	999.99
6	19	1	999.99
7	18	1	999.99
8	17	1	999.99
9	21	1	999.99
10	22	1	999.99
11	23	1	999.99
\.


--
-- Data for Name: shows; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.shows (show_id, movie_id, screen_id, show_date, show_time, end_time, status, created_at) FROM stdin;
3	1	1	2025-10-28	09:00:00	11:28:00	UPCOMING	2025-10-28 10:00:11.257051+05:30
4	1	1	2025-10-29	09:00:00	11:28:00	UPCOMING	2025-10-28 10:00:11.257051+05:30
5	1	1	2025-10-30	09:00:00	11:28:00	UPCOMING	2025-10-28 10:00:11.257051+05:30
6	1	1	2025-10-31	09:00:00	11:28:00	UPCOMING	2025-10-28 10:00:11.257051+05:30
7	1	1	2025-11-01	09:00:00	11:28:00	UPCOMING	2025-10-28 10:00:11.257051+05:30
8	1	1	2025-11-02	09:00:00	11:28:00	UPCOMING	2025-10-28 10:00:11.257051+05:30
9	1	1	2025-11-03	09:00:00	11:28:00	UPCOMING	2025-10-28 10:00:11.257051+05:30
11	1	1	2025-11-07	09:00:00	11:28:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
12	1	1	2025-11-07	11:43:00	14:11:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
13	1	1	2025-11-07	14:26:00	16:54:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
14	1	1	2025-11-07	17:09:00	19:37:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
15	1	1	2025-11-07	19:52:00	22:20:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
16	1	1	2025-11-08	09:00:00	11:28:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
17	1	1	2025-11-08	11:43:00	14:11:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
18	1	1	2025-11-08	14:26:00	16:54:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
19	1	1	2025-11-08	17:09:00	19:37:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
20	1	1	2025-11-08	19:52:00	22:20:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
21	1	1	2025-11-09	09:00:00	11:28:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
22	1	1	2025-11-09	11:43:00	14:11:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
23	1	1	2025-11-09	14:26:00	16:54:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
24	1	1	2025-11-09	17:09:00	19:37:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
25	1	1	2025-11-09	19:52:00	22:20:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
26	1	1	2025-11-10	09:00:00	11:28:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
27	1	1	2025-11-10	11:43:00	14:11:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
28	1	1	2025-11-10	14:26:00	16:54:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
29	1	1	2025-11-10	17:09:00	19:37:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
30	1	1	2025-11-10	19:52:00	22:20:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
31	1	1	2025-11-11	09:00:00	11:28:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
32	1	1	2025-11-11	11:43:00	14:11:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
33	1	1	2025-11-11	14:26:00	16:54:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
34	1	1	2025-11-11	17:09:00	19:37:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
35	1	1	2025-11-11	19:52:00	22:20:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
36	1	1	2025-11-12	09:00:00	11:28:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
37	1	1	2025-11-12	11:43:00	14:11:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
38	1	1	2025-11-12	14:26:00	16:54:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
39	1	1	2025-11-12	17:09:00	19:37:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
40	1	1	2025-11-12	19:52:00	22:20:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
41	1	1	2025-11-13	09:00:00	11:28:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
42	1	1	2025-11-13	11:43:00	14:11:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
43	1	1	2025-11-13	14:26:00	16:54:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
44	1	1	2025-11-13	17:09:00	19:37:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
45	1	1	2025-11-13	19:52:00	22:20:00	UPCOMING	2025-11-03 03:49:04.553785+05:30
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (user_id, name, email, phone, password, created_at, role) FROM stdin;
1	sylendravinayak	sylendravinayak@gmail.com	9629807807	$2b$12$NOntl3Dqc7Z7IuyzDBGgjOfCt8rYUeIPZBPIgunjTuza5z3/hQT3e	2025-10-27 11:01:40.471154	user
3	barane	barane@example.com	string	$2b$12$E50fPxWgcae7HiqRdO9QH.YaMzyruCDXzRCWt8kQo86C3CsZbP/L6	2025-10-31 15:57:11.076828	user
\.


--
-- Name: booked_food_booked_food_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.booked_food_booked_food_id_seq', 19, true);


--
-- Name: booked_seats_booked_seat_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.booked_seats_booked_seat_id_seq', 24, true);


--
-- Name: booking_status_status_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.booking_status_status_log_id_seq', 14, true);


--
-- Name: bookings_booking_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.bookings_booking_id_seq', 50, true);


--
-- Name: discounts_discount_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.discounts_discount_id_seq', 2, true);


--
-- Name: food_categories_category_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.food_categories_category_id_seq', 3, true);


--
-- Name: food_items_food_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.food_items_food_id_seq', 2, true);


--
-- Name: gst_gst_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.gst_gst_id_seq', 3, true);


--
-- Name: movies_movie_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.movies_movie_id_seq', 1, true);


--
-- Name: payments_payment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.payments_payment_id_seq', 13, true);


--
-- Name: screens_screen_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.screens_screen_id_seq', 2, true);


--
-- Name: seat_categories_category_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.seat_categories_category_id_seq', 2, true);


--
-- Name: seat_locks_lock_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.seat_locks_lock_id_seq', 30, true);


--
-- Name: seats_seat_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.seats_seat_id_seq', 8, true);


--
-- Name: show_category_pricing_pricing_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.show_category_pricing_pricing_id_seq', 11, true);


--
-- Name: shows_show_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.shows_show_id_seq', 45, true);


--
-- Name: users_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_user_id_seq', 3, true);


--
-- Name: booked_food booked_food_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booked_food
    ADD CONSTRAINT booked_food_pkey PRIMARY KEY (booked_food_id);


--
-- Name: booked_seats booked_seats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booked_seats
    ADD CONSTRAINT booked_seats_pkey PRIMARY KEY (booked_seat_id);


--
-- Name: booking_status booking_status_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booking_status
    ADD CONSTRAINT booking_status_pkey PRIMARY KEY (status_log_id);


--
-- Name: bookings bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_pkey PRIMARY KEY (booking_id);


--
-- Name: discounts discounts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discounts
    ADD CONSTRAINT discounts_pkey PRIMARY KEY (discount_id);


--
-- Name: discounts discounts_promo_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discounts
    ADD CONSTRAINT discounts_promo_code_key UNIQUE (promo_code);


--
-- Name: food_categories food_categories_category_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.food_categories
    ADD CONSTRAINT food_categories_category_name_key UNIQUE (category_name);


--
-- Name: food_categories food_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.food_categories
    ADD CONSTRAINT food_categories_pkey PRIMARY KEY (category_id);


--
-- Name: food_items food_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.food_items
    ADD CONSTRAINT food_items_pkey PRIMARY KEY (food_id);


--
-- Name: gst gst_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gst
    ADD CONSTRAINT gst_pkey PRIMARY KEY (gst_id);


--
-- Name: movies movies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.movies
    ADD CONSTRAINT movies_pkey PRIMARY KEY (movie_id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (payment_id);


--
-- Name: screens screens_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.screens
    ADD CONSTRAINT screens_pkey PRIMARY KEY (screen_id);


--
-- Name: seat_categories seat_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seat_categories
    ADD CONSTRAINT seat_categories_pkey PRIMARY KEY (category_id);


--
-- Name: seat_locks seat_locks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seat_locks
    ADD CONSTRAINT seat_locks_pkey PRIMARY KEY (lock_id);


--
-- Name: seats seats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seats
    ADD CONSTRAINT seats_pkey PRIMARY KEY (seat_id);


--
-- Name: show_category_pricing show_category_pricing_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.show_category_pricing
    ADD CONSTRAINT show_category_pricing_pkey PRIMARY KEY (pricing_id);


--
-- Name: shows shows_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shows
    ADD CONSTRAINT shows_pkey PRIMARY KEY (show_id);


--
-- Name: booked_seats uq_booked_seat_booking_seat; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booked_seats
    ADD CONSTRAINT uq_booked_seat_booking_seat UNIQUE (booking_id, seat_id);


--
-- Name: booked_seats uq_booked_seat_seat_show; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booked_seats
    ADD CONSTRAINT uq_booked_seat_seat_show UNIQUE (seat_id, show_id);


--
-- Name: show_category_pricing uq_pricing_show_category; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.show_category_pricing
    ADD CONSTRAINT uq_pricing_show_category UNIQUE (show_id, category_id);


--
-- Name: shows uq_screen_date_time; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shows
    ADD CONSTRAINT uq_screen_date_time UNIQUE (screen_id, show_date, show_time);


--
-- Name: seats uq_seat_screen_seatnum; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seats
    ADD CONSTRAINT uq_seat_screen_seatnum UNIQUE (screen_id, seat_number);


--
-- Name: users users_phone_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_phone_key UNIQUE (phone);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: ix_booked_food_booked_food_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booked_food_booked_food_id ON public.booked_food USING btree (booked_food_id);


--
-- Name: ix_booked_food_booking_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booked_food_booking_id ON public.booked_food USING btree (booking_id);


--
-- Name: ix_booked_food_food_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booked_food_food_id ON public.booked_food USING btree (food_id);


--
-- Name: ix_booked_food_gst_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booked_food_gst_id ON public.booked_food USING btree (gst_id);


--
-- Name: ix_booked_seats_booked_seat_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booked_seats_booked_seat_id ON public.booked_seats USING btree (booked_seat_id);


--
-- Name: ix_booked_seats_booking_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booked_seats_booking_id ON public.booked_seats USING btree (booking_id);


--
-- Name: ix_booked_seats_gst_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booked_seats_gst_id ON public.booked_seats USING btree (gst_id);


--
-- Name: ix_booked_seats_seat_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booked_seats_seat_id ON public.booked_seats USING btree (seat_id);


--
-- Name: ix_booked_seats_show_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booked_seats_show_id ON public.booked_seats USING btree (show_id);


--
-- Name: ix_booking_status_booking_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booking_status_booking_id ON public.booking_status USING btree (booking_id);


--
-- Name: ix_booking_status_changed_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booking_status_changed_at ON public.booking_status USING btree (changed_at);


--
-- Name: ix_booking_status_status_log_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booking_status_status_log_id ON public.booking_status USING btree (status_log_id);


--
-- Name: ix_bookings_booking_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookings_booking_id ON public.bookings USING btree (booking_id);


--
-- Name: ix_bookings_booking_reference; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_bookings_booking_reference ON public.bookings USING btree (booking_reference);


--
-- Name: ix_bookings_discount_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookings_discount_id ON public.bookings USING btree (discount_id);


--
-- Name: ix_bookings_payment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookings_payment_id ON public.bookings USING btree (payment_id);


--
-- Name: ix_bookings_show_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookings_show_id ON public.bookings USING btree (show_id);


--
-- Name: ix_bookings_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookings_user_id ON public.bookings USING btree (user_id);


--
-- Name: ix_discounts_discount_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_discounts_discount_id ON public.discounts USING btree (discount_id);


--
-- Name: ix_food_categories_category_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_food_categories_category_id ON public.food_categories USING btree (category_id);


--
-- Name: ix_food_items_category_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_food_items_category_id ON public.food_items USING btree (category_id);


--
-- Name: ix_food_items_food_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_food_items_food_id ON public.food_items USING btree (food_id);


--
-- Name: ix_gst_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_gst_category ON public.gst USING btree (gst_category);


--
-- Name: ix_gst_gst_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_gst_gst_id ON public.gst USING btree (gst_id);


--
-- Name: ix_movies_movie_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_movies_movie_id ON public.movies USING btree (movie_id);


--
-- Name: ix_payments_payment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_payments_payment_id ON public.payments USING btree (payment_id);


--
-- Name: ix_payments_transaction_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_payments_transaction_code ON public.payments USING btree (transaction_code);


--
-- Name: ix_pricing_category_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_pricing_category_id ON public.show_category_pricing USING btree (category_id);


--
-- Name: ix_pricing_show_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_pricing_show_id ON public.show_category_pricing USING btree (show_id);


--
-- Name: ix_screens_screen_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_screens_screen_id ON public.screens USING btree (screen_id);


--
-- Name: ix_seat_categories_category_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seat_categories_category_id ON public.seat_categories USING btree (category_id);


--
-- Name: ix_seat_locks_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seat_locks_expires_at ON public.seat_locks USING btree (expires_at);


--
-- Name: ix_seat_locks_lock_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seat_locks_lock_id ON public.seat_locks USING btree (lock_id);


--
-- Name: ix_seat_locks_seat_show; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seat_locks_seat_show ON public.seat_locks USING btree (seat_id, show_id);


--
-- Name: ix_seats_category_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seats_category_id ON public.seats USING btree (category_id);


--
-- Name: ix_seats_screen_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seats_screen_id ON public.seats USING btree (screen_id);


--
-- Name: ix_seats_seat_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seats_seat_id ON public.seats USING btree (seat_id);


--
-- Name: ix_show_category_pricing_pricing_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_show_category_pricing_pricing_id ON public.show_category_pricing USING btree (pricing_id);


--
-- Name: ix_shows_movie_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shows_movie_id ON public.shows USING btree (movie_id);


--
-- Name: ix_shows_screen_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shows_screen_id ON public.shows USING btree (screen_id);


--
-- Name: ix_shows_show_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shows_show_date ON public.shows USING btree (show_date);


--
-- Name: ix_shows_show_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shows_show_id ON public.shows USING btree (show_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_user_id ON public.users USING btree (user_id);


--
-- Name: booked_seats booked_seats_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booked_seats
    ADD CONSTRAINT booked_seats_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(booking_id) ON DELETE CASCADE;


--
-- Name: food_items food_items_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.food_items
    ADD CONSTRAINT food_items_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.food_categories(category_id) ON DELETE SET NULL;


--
-- Name: seat_locks seat_locks_seat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seat_locks
    ADD CONSTRAINT seat_locks_seat_id_fkey FOREIGN KEY (seat_id) REFERENCES public.seats(seat_id) ON DELETE CASCADE;


--
-- Name: seat_locks seat_locks_show_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seat_locks
    ADD CONSTRAINT seat_locks_show_id_fkey FOREIGN KEY (show_id) REFERENCES public.shows(show_id) ON DELETE CASCADE;


--
-- Name: seat_locks seat_locks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seat_locks
    ADD CONSTRAINT seat_locks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: seats seats_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seats
    ADD CONSTRAINT seats_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.seat_categories(category_id) ON DELETE SET NULL;


--
-- Name: seats seats_screen_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seats
    ADD CONSTRAINT seats_screen_id_fkey FOREIGN KEY (screen_id) REFERENCES public.screens(screen_id) ON DELETE CASCADE;


--
-- Name: show_category_pricing show_category_pricing_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.show_category_pricing
    ADD CONSTRAINT show_category_pricing_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.seat_categories(category_id) ON DELETE CASCADE;


--
-- Name: shows shows_movie_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shows
    ADD CONSTRAINT shows_movie_id_fkey FOREIGN KEY (movie_id) REFERENCES public.movies(movie_id) ON DELETE CASCADE;


--
-- Name: shows shows_screen_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shows
    ADD CONSTRAINT shows_screen_id_fkey FOREIGN KEY (screen_id) REFERENCES public.screens(screen_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict e2IEZ0Gie3xhocZxIYhu0coITdiolaNK7syJ3wYX0JXKUlAh1K9tVRo08filqGQ

