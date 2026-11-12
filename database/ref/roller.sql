--
-- PostgreSQL database cluster dump
--

\restrict KVzRK69zNefLOXnuZfFU0WrXbIBW82KP9rmgLnIQP5vk9RKTMZZxDR1LS92kAbY

SET default_transaction_read_only = off;

SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

--
-- Roles
--

CREATE ROLE beraer;
ALTER ROLE beraer WITH SUPERUSER INHERIT CREATEROLE CREATEDB LOGIN NOREPLICATION NOBYPASSRLS;
CREATE ROLE postgres;
ALTER ROLE postgres WITH SUPERUSER INHERIT CREATEROLE CREATEDB LOGIN REPLICATION BYPASSRLS;
CREATE ROLE school_app;
ALTER ROLE school_app WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB LOGIN NOREPLICATION NOBYPASSRLS;

--
-- User Configurations
--






\unrestrict KVzRK69zNefLOXnuZfFU0WrXbIBW82KP9rmgLnIQP5vk9RKTMZZxDR1LS92kAbY

--
-- PostgreSQL database cluster dump complete
--

