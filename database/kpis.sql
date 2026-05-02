--Enrollment Outcome Breakdown
SELECT 
    enrollment_status,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM fact_enrollments
GROUP BY enrollment_status
ORDER BY total DESC;

--Dropout Rate by Age Group
SELECT 
    CASE 
        WHEN ds.age_at_enrollment < 20 THEN 'Under 20'
        WHEN ds.age_at_enrollment BETWEEN 20 AND 25 THEN '20-25'
        WHEN ds.age_at_enrollment BETWEEN 26 AND 35 THEN '26-35'
        ELSE 'Over 35'
    END as age_group,
    COUNT(*) as total,
    SUM(CASE WHEN fe.enrollment_status = 'Dropout' THEN 1 ELSE 0 END) as dropouts,
    ROUND(SUM(CASE WHEN fe.enrollment_status = 'Dropout' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as dropout_rate
FROM fact_enrollments fe
JOIN dim_student ds ON fe.student_id = ds.student_id
GROUP BY age_group
ORDER BY dropout_rate DESC;

--Dropout Rate by Gender
SELECT 
    CASE WHEN ds.gender = 1 THEN 'Male' ELSE 'Female' END as gender,
    COUNT(*) as total,
    SUM(CASE WHEN fe.enrollment_status = 'Dropout' THEN 1 ELSE 0 END) as dropouts,
    ROUND(SUM(CASE WHEN fe.enrollment_status = 'Dropout' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as dropout_rate
FROM fact_enrollments fe
JOIN dim_student ds ON fe.student_id = ds.student_id
GROUP BY ds.gender
ORDER BY dropout_rate DESC;

--Dropout Rate by Scholarship
SELECT 
    CASE WHEN ds.scholarship_holder = 1 THEN 'Scholarship' ELSE 'No Scholarship' END as scholarship,
    COUNT(*) as total,
    SUM(CASE WHEN fe.enrollment_status = 'Dropout' THEN 1 ELSE 0 END) as dropouts,
    ROUND(SUM(CASE WHEN fe.enrollment_status = 'Dropout' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as dropout_rate
FROM fact_enrollments fe
JOIN dim_student ds ON fe.student_id = ds.student_id
GROUP BY ds.scholarship_holder
ORDER BY dropout_rate DESC;

--Academic Performance vs Dropout
SELECT 
    enrollment_status,
    ROUND(AVG(cu1_grade)::numeric, 2) as avg_grade_sem1,
    ROUND(AVG(cu2_grade)::numeric, 2) as avg_grade_sem2,
    ROUND(AVG(cu1_approved)::numeric, 2) as avg_approved_sem1,
    ROUND(AVG(cu2_approved)::numeric, 2) as avg_approved_sem2
FROM fact_enrollments
GROUP BY enrollment_status
ORDER BY avg_grade_sem1 DESC;