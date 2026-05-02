--Star schema for enrollment data
DROP TABLE IF EXISTS fact_enrollments CASCADE;
DROP TABLE IF EXISTS dim_student CASCADE;
DROP TABLE IF EXISTS dim_course CASCADE;
DROP TABLE IF EXISTS dim_economics CASCADE;

--Dimensional tables- student demographics
CREATE TABLE dim_student (
    student_id        SERIAL PRIMARY KEY,
    marital_status    INTEGER,
    gender            INTEGER,
    age_at_enrollment INTEGER,
    international     INTEGER,
    displaced         INTEGER,
    educational_special_needs INTEGER,
    debtor            INTEGER,
    tuition_fees_up_to_date   INTEGER,
    scholarship_holder        INTEGER,
    previous_qualification    INTEGER,
    nacionality               INTEGER,
    mother_qualification      INTEGER,
    father_qualification      INTEGER,
    mother_occupation         INTEGER,
    father_occupation         INTEGER
);

--Dimensional tables- course information
CREATE TABLE dim_course (
    course_id                   SERIAL PRIMARY KEY,
    course                      INTEGER,
    daytime_evening_attendance  INTEGER,
    application_mode            INTEGER,
    application_order           INTEGER
);

--Dimensional tables- economic indicators
CREATE TABLE dim_economics (
    economics_id      SERIAL PRIMARY KEY,
    unemployment_rate FLOAT,
    inflation_rate    FLOAT,
    gdp               FLOAT
);

--Fact table- enrollment outcomes and performance
CREATE TABLE fact_enrollments (
    enrollment_id       SERIAL PRIMARY KEY,
    student_id          INTEGER REFERENCES dim_student(student_id),
    course_id           INTEGER REFERENCES dim_course(course_id),
    economics_id        INTEGER REFERENCES dim_economics(economics_id),
    -- Semester 1
    cu1_credited        INTEGER,
    cu1_enrolled        INTEGER,
    cu1_evaluations     INTEGER,
    cu1_approved        INTEGER,
    cu1_grade           FLOAT,
    cu1_without_eval    INTEGER,
    -- Semester 2
    cu2_credited        INTEGER,
    cu2_enrolled        INTEGER,
    cu2_evaluations     INTEGER,
    cu2_approved        INTEGER,
    cu2_grade           FLOAT,
    cu2_without_eval    INTEGER,
    -- Outcome
    enrollment_status   TEXT
);

--Insert data into dimensional tables and fact table
INSERT INTO dim_student (
    marital_status, gender, age_at_enrollment, international,
    displaced, educational_special_needs, debtor,
    tuition_fees_up_to_date, scholarship_holder,
    previous_qualification, nacionality,
    mother_qualification, father_qualification,
    mother_occupation, father_occupation
)
SELECT DISTINCT
    marital_status, gender, age_at_enrollment, international,
    displaced, educational_special_needs, debtor,
    tuition_fees_up_to_date, scholarship_holder,
    previous_qualification, nacionality,
    "mother's_qualification", "father's_qualification",
    "mother's_occupation", "father's_occupation"
FROM students;

--Insert data into the dim_course table
INSERT INTO dim_course (
    course, daytime_evening_attendance,
    application_mode, application_order
)
SELECT DISTINCT
    course, daytime_evening_attendance,
    application_mode, application_order
FROM students;

--Insert data into the dim_economics table
INSERT INTO dim_economics (
    unemployment_rate, inflation_rate, gdp
)
SELECT DISTINCT
    unemployment_rate, inflation_rate, gdp
FROM students;

--Insert data into the fact_enrollments table
INSERT INTO fact_enrollments (
    student_id, course_id, economics_id,
    cu1_credited, cu1_enrolled, cu1_evaluations,
    cu1_approved, cu1_grade, cu1_without_eval,
    cu2_credited, cu2_enrolled, cu2_evaluations,
    cu2_approved, cu2_grade, cu2_without_eval,
    enrollment_status
)
SELECT
    ds.student_id,
    dc.course_id,
    de.economics_id,
    s."curricular_units_1st_sem_(credited)",
    s."curricular_units_1st_sem_(enrolled)",
    s."curricular_units_1st_sem_(evaluations)",
    s."curricular_units_1st_sem_(approved)",
    s."curricular_units_1st_sem_(grade)",
    s."curricular_units_1st_sem_(without_evaluations)",
    s."curricular_units_2nd_sem_(credited)",
    s."curricular_units_2nd_sem_(enrolled)",
    s."curricular_units_2nd_sem_(evaluations)",
    s."curricular_units_2nd_sem_(approved)",
    s."curricular_units_2nd_sem_(grade)",
    s."curricular_units_2nd_sem_(without_evaluations)",
    s.target
FROM students s
JOIN dim_student ds ON
    s.marital_status = ds.marital_status AND
    s.gender = ds.gender AND
    s.age_at_enrollment = ds.age_at_enrollment AND
    s.international = ds.international AND
    s.displaced = ds.displaced AND
    s.educational_special_needs = ds.educational_special_needs AND
    s.debtor = ds.debtor AND
    s.tuition_fees_up_to_date = ds.tuition_fees_up_to_date AND
    s.scholarship_holder = ds.scholarship_holder AND
    s.previous_qualification = ds.previous_qualification AND
    s.nacionality = ds.nacionality AND
    s."mother's_qualification" = ds.mother_qualification AND
    s."father's_qualification" = ds.father_qualification AND
    s."mother's_occupation" = ds.mother_occupation AND
    s."father's_occupation" = ds.father_occupation
JOIN dim_course dc ON
    s.course = dc.course AND
    s.daytime_evening_attendance = dc.daytime_evening_attendance AND
    s.application_mode = dc.application_mode AND
    s.application_order = dc.application_order
JOIN dim_economics de ON
    s.unemployment_rate = de.unemployment_rate AND
    s.inflation_rate = de.inflation_rate AND
    s.gdp = de.gdp;