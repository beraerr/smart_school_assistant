--
-- PostgreSQL database dump
--

\restrict cAQIUtAkeYTHKPRhcsbh7YalPU8bAmGFtScmQ10S09oiFIiDwjlVAudQZzsZS0J

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

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

--
-- Name: userrole; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.userrole AS ENUM (
    'PRINCIPAL',
    'TEACHER',
    'PARENT',
    'STUDENT'
);


--
-- Name: class_teacher(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.class_teacher() RETURNS TABLE(name text)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public', 'pg_temp'
    AS $$
    SELECT t.name
    FROM public.teachers AS t
    JOIN public.students AS s
        ON s.class_name = t.class_name
    WHERE current_setting('app.role', true) IN ('parent', 'student')
      AND s.id = CAST(NULLIF(current_setting('app.student_id', true), '') AS integer)
$$;


--
-- Name: student_rank(text, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.student_rank(p_scope text, p_subject text DEFAULT NULL::text) RETURNS TABLE(scope text, subject text, rank integer, total_students integer, student_avg numeric, group_avg numeric)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public', 'pg_temp'
    AS $$
    WITH params AS (
        SELECT
            CAST(NULLIF(current_setting('app.student_id', true), '') AS integer) AS me,
            current_setting('app.role', true) AS role,
            CAST(NULLIF(current_setting('app.today', true), '') AS date) AS today,
            CASE
                WHEN p_scope IN ('class', 'school') THEN p_scope
                ELSE NULL
            END AS scope,
            NULLIF(btrim(p_subject), '') AS subject
    ),
    me_row AS (
        SELECT s.id, s.class_name
        FROM public.students AS s
        CROSS JOIN params AS p
        WHERE p.me IS NOT NULL
          AND p.role IN ('parent', 'student')
          AND p.scope IS NOT NULL
          AND s.id = p.me
    ),
    averages AS (
        SELECT
            s.id,
            CAST(AVG(g.grade) AS numeric) AS student_avg
        FROM public.students AS s
        CROSS JOIN params AS p
        JOIN me_row AS m ON TRUE
        LEFT JOIN public.grades AS g
            ON g.student_id = s.id
           AND g.date <= p.today
           AND (
                p.subject IS NULL
                OR lower(g.subject) = lower(p.subject)
           )
        WHERE p.scope = 'school'
           OR s.class_name = m.class_name
        GROUP BY s.id
    ),
    ranked AS (
        SELECT
            a.id,
            a.student_avg,
            RANK() OVER (ORDER BY a.student_avg DESC NULLS LAST) AS placement,
            COUNT(*) OVER () AS total_students,
            AVG(a.student_avg) OVER () AS group_avg
        FROM averages AS a
    )
    SELECT
        p.scope,
        p.subject,
        CAST(r.placement AS integer),
        CAST(r.total_students AS integer),
        r.student_avg,
        r.group_avg
    FROM ranked AS r
    CROSS JOIN params AS p
    WHERE r.id = p.me
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: attendance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.attendance (
    id integer NOT NULL,
    student_id integer NOT NULL,
    date date NOT NULL,
    status character varying NOT NULL
);


--
-- Name: attendance_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.attendance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: attendance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.attendance_id_seq OWNED BY public.attendance.id;


--
-- Name: grades; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.grades (
    id integer NOT NULL,
    student_id integer NOT NULL,
    subject character varying NOT NULL,
    grade double precision NOT NULL,
    date date NOT NULL
);


--
-- Name: grades_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.grades_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: grades_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.grades_id_seq OWNED BY public.grades.id;


--
-- Name: students; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.students (
    id integer NOT NULL,
    name character varying NOT NULL,
    class_name character varying NOT NULL,
    parent_id integer
);


--
-- Name: students_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.students_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: students_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.students_id_seq OWNED BY public.students.id;


--
-- Name: teachers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teachers (
    id integer NOT NULL,
    name character varying NOT NULL,
    class_name character varying NOT NULL
);


--
-- Name: teachers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teachers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teachers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teachers_id_seq OWNED BY public.teachers.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying NOT NULL,
    password_hash character varying NOT NULL,
    role public.userrole NOT NULL,
    related_id integer,
    related_class character varying
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: attendance id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance ALTER COLUMN id SET DEFAULT nextval('public.attendance_id_seq'::regclass);


--
-- Name: grades id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grades ALTER COLUMN id SET DEFAULT nextval('public.grades_id_seq'::regclass);


--
-- Name: students id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.students ALTER COLUMN id SET DEFAULT nextval('public.students_id_seq'::regclass);


--
-- Name: teachers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teachers ALTER COLUMN id SET DEFAULT nextval('public.teachers_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: attendance attendance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_pkey PRIMARY KEY (id);


--
-- Name: grades grades_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_pkey PRIMARY KEY (id);


--
-- Name: students students_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.students
    ADD CONSTRAINT students_pkey PRIMARY KEY (id);


--
-- Name: teachers teachers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teachers
    ADD CONSTRAINT teachers_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_attendance_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_attendance_id ON public.attendance USING btree (id);


--
-- Name: ix_grades_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_grades_id ON public.grades USING btree (id);


--
-- Name: ix_students_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_students_id ON public.students USING btree (id);


--
-- Name: ix_teachers_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teachers_id ON public.teachers USING btree (id);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: attendance attendance_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(id);


--
-- Name: grades grades_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(id);


--
-- Name: students students_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.students
    ADD CONSTRAINT students_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.users(id);


--
-- Name: attendance; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.attendance ENABLE ROW LEVEL SECURITY;

--
-- Name: attendance attendance_via_students; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY attendance_via_students ON public.attendance FOR SELECT USING ((student_id IN ( SELECT students.id
   FROM public.students)));


--
-- Name: attendance attendance_zaman_kapisi; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY attendance_zaman_kapisi ON public.attendance AS RESTRICTIVE FOR SELECT TO school_app USING ((date <= (NULLIF(current_setting('app.today'::text, true), ''::text))::date));


--
-- Name: grades; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.grades ENABLE ROW LEVEL SECURITY;

--
-- Name: grades grades_via_students; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY grades_via_students ON public.grades FOR SELECT USING ((student_id IN ( SELECT students.id
   FROM public.students)));


--
-- Name: grades grades_zaman_kapisi; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY grades_zaman_kapisi ON public.grades AS RESTRICTIVE FOR SELECT TO school_app USING ((date <= (NULLIF(current_setting('app.today'::text, true), ''::text))::date));


--
-- Name: students; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.students ENABLE ROW LEVEL SECURITY;

--
-- Name: students students_role_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY students_role_access ON public.students FOR SELECT USING (((current_setting('app.role'::text, true) = 'principal'::text) OR ((current_setting('app.role'::text, true) = 'teacher'::text) AND ((class_name)::text = current_setting('app.class'::text, true))) OR ((current_setting('app.role'::text, true) = ANY (ARRAY['parent'::text, 'student'::text])) AND (id = (NULLIF(current_setting('app.student_id'::text, true), ''::text))::integer))));


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: -
--

GRANT USAGE ON SCHEMA public TO school_app;


--
-- Name: FUNCTION class_teacher(); Type: ACL; Schema: public; Owner: -
--

REVOKE ALL ON FUNCTION public.class_teacher() FROM PUBLIC;
GRANT ALL ON FUNCTION public.class_teacher() TO school_app;


--
-- Name: FUNCTION student_rank(p_scope text, p_subject text); Type: ACL; Schema: public; Owner: -
--

REVOKE ALL ON FUNCTION public.student_rank(p_scope text, p_subject text) FROM PUBLIC;
GRANT ALL ON FUNCTION public.student_rank(p_scope text, p_subject text) TO school_app;


--
-- Name: TABLE attendance; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT ON TABLE public.attendance TO school_app;


--
-- Name: TABLE grades; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT ON TABLE public.grades TO school_app;


--
-- Name: TABLE students; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT ON TABLE public.students TO school_app;


--
-- PostgreSQL database dump complete
--

\unrestrict cAQIUtAkeYTHKPRhcsbh7YalPU8bAmGFtScmQ10S09oiFIiDwjlVAudQZzsZS0J

