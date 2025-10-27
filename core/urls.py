from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ==========================================================
    # Authentication
    # ==========================================================
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", views.employee_logout, name="logout"),
    path("hr/logout/", views.hr_logout, name="hr_logout"),

    path("hr/login/", views.hr_login, name="hr_login"),
    path("employee/login/", views.employee_login, name="employee_login"),

    # ==========================================================
    # Dashboards
    # ==========================================================
    path("", views.employee_dashboard, name="home"),
    path("dashboard/", views.employee_dashboard, name="employee_dashboard"),
    path("hr/dashboard/", views.hr_dashboard, name="hr_dashboard"),
    path("hr/insights/", views.hr_insights, name="hr_insights"),


    # ==========================================================
    # Employee Profile
    # ==========================================================
    path("profile/", views.my_profile, name="employee_profile"),  # Updated name to match template

    # ==========================================================
    # HR Management (Employees & Departments)
    # ==========================================================
    # Employees
    path("hr/employees/", views.hr_employee_list, name="hr_employee_list"),
    path("hr/employees/add/", views.hr_employee_create, name="hr_employee_create"),
    path("hr/employees/<int:pk>/edit/", views.hr_employee_edit, name="hr_employee_edit"),
    path("hr/employees/<int:pk>/delete/", views.hr_employee_delete, name="hr_employee_delete"),

    # Departments
    path("hr/departments/", views.hr_department_list, name="hr_department_list"),
    path("hr/departments/add/", views.hr_department_create, name="hr_department_create"),
    path("hr/departments/<int:pk>/edit/", views.hr_department_edit, name="hr_department_edit"),
    path("hr/departments/<int:pk>/delete/", views.hr_department_delete, name="hr_department_delete"),

    # Leaves (HR)
    path("hr/leaves/", views.hr_leave_list, name="hr_leave_list"),

    # ==========================================================
    # Attendance
    # ==========================================================
    path("attendance/add/", views.add_attendance, name="add_attendance"),
    path("attendance/mark/", views.mark_attendance, name="mark_attendance"),
    path("attendance/view/", views.attendance_view, name="attendance_view"),

    # ==========================================================
    # Leave Management (Employee)
    # ==========================================================
    path("leaves/list/", views.leave_list, name="leave_list"),
    path("leaves/add/", views.leave_request_create, name="leave_request_create"),
    path("leaves/process/<int:pk>/<str:action>/", views.leave_process, name="leave_process"),

    # ==========================================================
    # Payroll
    # ==========================================================
    # HR Payroll Management
    path("hr/payrolls/", views.payroll_list, name="payroll_list"),
    path("hr/payrolls/add/", views.payroll_add, name="payroll_add"),
    path("hr/payrolls/edit/<int:pk>/", views.payroll_edit, name="payroll_edit"),
    path("hr/payrolls/delete/<int:pk>/", views.payroll_delete, name="payroll_delete"),

    # Employee Payroll
    path("employee/payroll/", views.employee_payroll, name="employee_payroll"),
    path("employee/payroll/<int:payroll_id>/pdf/", views.payroll_pdf, name="payroll_pdf"),
    path("payroll/generate/<int:emp_id>/", views.generate_payroll_for_employee, name="generate_payroll"),
    path("payroll/<int:pk>/", views.payroll_detail, name="payroll_detail"),
    path("payroll/mark-paid/<int:pk>/", views.payroll_mark_paid, name="payroll_mark_paid"),

    # ==========================================================
    # Reports (HR Only)
    # ==========================================================
    path("hr/reports/employees/", views.employee_report, name="employee_report"),
    path("hr/reports/employees/export/", views.export_employees, name="hr_export_employees"),
    path("hr/reports/payroll/export/", views.export_payroll, name="hr_export_payroll"),
    path("hr/reports/attendance/", views.attendance_report, name="attendance_report"),
    path("hr/reports/attendance/export/", views.export_attendance, name="hr_export_attendance"),
    path("hr/reports/salary/", views.salary_report, name="salary_report"),
    path("hr/reports/salary/export/", views.export_salary, name="hr_export_salary"),
    path("hr/reports/leave/export/", views.export_leave, name="hr_export_leave"),

    # ==========================================================
    # Notifications
    # ==========================================================
    path("notifications/delete/<int:pk>/", views.delete_notification, name="delete_notification"),
]
