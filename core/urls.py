from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ==============================================================
    # Authentication
    # ==============================================================
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),

    # Custom logins
    path("hr/login/", views.hr_login, name="hr_login"),
    path("employee/login/", views.employee_login, name="employee_login"),

    # ==============================================================
    # Dashboards
    # ==============================================================
    path("dashboard/", views.employee_dashboard, name="employee_dashboard"),
    path("hr/dashboard/", views.hr_dashboard, name="hr_dashboard"),

    # ==============================================================
    # Profile
    # ==============================================================
    path("profile/", views.my_profile, name="my_profile"),

    # ==============================================================
    # Employee & Department Management
    # ==============================================================
    path("employee/list/", views.employee_list, name="employee_list"),
    path("department/list/", views.department_list, name="department_list"),

    # ==============================================================
    # Attendance
    # ==============================================================
    path("attendance/add/", views.add_attendance, name="add_attendance"),
    path("attendance/mark/", views.mark_attendance, name="mark_attendance"),
    path("attendance/view/", views.attendance_view, name="attendance_view"),

    # ==============================================================
    # Leave Management
    # ==============================================================
    path("leaves/list/", views.leave_list, name="leave_list"),
    path("leaves/new/", views.leave_request_create, name="leave_request_create"),
    path("leaves/process/<int:pk>/<str:action>/", views.leave_process, name="leave_process"),

    # ==============================================================
    # Payroll
    # ==============================================================
    path("payroll/generate/<int:emp_id>/", views.generate_payroll_for_employee, name="generate_payroll"),
    path("payroll/<int:pk>/", views.payroll_detail, name="payroll_detail"),
    path("payroll/mark-paid/<int:pk>/", views.payroll_mark_paid, name="payroll_mark_paid"),

    # ==============================================================
    # Reports
    # ==============================================================
    path("reports/employees/", views.employee_report, name="employee_report"),
    path("reports/attendance/", views.attendance_report, name="attendance_report"),
    path("reports/salary/", views.salary_report, name="salary_report"),

    # ==============================================================
    # Default Landing
    # ==============================================================
    path("", views.employee_dashboard, name="home"),
]
