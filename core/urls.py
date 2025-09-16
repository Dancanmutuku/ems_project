from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication (uses registration/login.html)
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),

    # Dashboard & Profile
    path("dashboard/", views.employee_dashboard, name="employee_dashboard"),
    

    # Attendance
    

    # Leave Management
    path("leaves/", views.leave_list, name="leave_list"),
    path("leaves/new/", views.leave_request_create, name="leave_request_create"),
    path("leaves/process/<int:pk>/<str:action>/", views.leave_process, name="leave_process"),

    # Payroll
    path("payroll/generate/<int:emp_id>/", views.generate_payroll_for_employee, name="generate_payroll"),
    path("payroll/<int:pk>/", views.payroll_detail, name="payroll_detail"),

    # Reports
    path("reports/employees/", views.employee_report, name="employee_report"),
    path("reports/attendance/", views.attendance_report, name="attendance_report"),
    path("reports/salary/", views.salary_report, name="salary_report"),

    # Default landing
    path("", views.employee_dashboard, name="home"),
]
