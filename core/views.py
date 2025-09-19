# core/views.py
from decimal import Decimal
from datetime import date
import calendar

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import models

from .models import Employee, Attendance, LeaveRequest, Payroll, Notification, Department
from .forms import LeaveRequestForm, AttendanceForm
from .utils import calc_nssf, calc_nhif, calc_paye

from django.shortcuts import render, get_object_or_404
from .models import Employee
from django.contrib.auth.decorators import login_required
from .models import Department

def department_list(request):
    departments = Department.objects.all()
    return render(request, "department_list.html", {"departments": departments})
@login_required
def employee_list(request):
    employees = Employee.objects.all()
    return render(request, "employee/employee_list.html", {"employees": employees})

# ================================================================
# Helper: Role & Group Check
# ================================================================
def group_required(group_name):
    """Custom decorator to check if user is in a specific group."""
    def check(user):
        return user.is_superuser or user.groups.filter(name=group_name).exists()
    return user_passes_test(check)


def is_hr(user):
    """Shortcut: Check if user is HR or superuser"""
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name="HR").exists())


# ================================================================
# HR LOGIN
# ================================================================
def hr_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user and is_hr(user):
            login(request, user)
            return redirect("hr_dashboard")
        else:
            messages.error(request, "Invalid HR credentials or not authorized.")

    return render(request, "registration/hr_login.html")


# ================================================================
# Employee LOGIN
# ================================================================
def employee_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            if is_hr(user):
                return redirect('hr_dashboard')
            else:
                return redirect('employee_dashboard')
        else:
            messages.error(request, "Invalid username or password")

    return render(request, 'registration/login.html')


def employee_logout(request):
    logout(request)
    return redirect("login")


# ================================================================
# Employee Dashboard
# ================================================================
@login_required
def employee_dashboard(request):
    employee = get_object_or_404(Employee, user=request.user)

    context = {
        "employee": employee,
        "payrolls": Payroll.objects.filter(employee=employee).order_by('-period_end')[:6],
        "leaves": LeaveRequest.objects.filter(employee=employee).order_by('-requested_at')[:5],
        "notifications": Notification.objects.filter(user=request.user).order_by('-created_at')[:5],
        "attendance_records": Attendance.objects.filter(employee=employee).order_by('-date')[:10],
        "total_present": Attendance.objects.filter(employee=employee, status="Present").count(),
        "total_absent": Attendance.objects.filter(employee=employee, status="Absent").count(),
        "total_leave": Attendance.objects.filter(employee=employee, status="Leave").count(),
    }
    return render(request, "core/employee_dashboard.html", context)


# ================================================================
# Profile
# ================================================================
@login_required
def my_profile(request):
    emp = get_object_or_404(Employee, user=request.user)
    return render(request, 'core/my_profile.html', {'employee': emp})


# ================================================================
# HR Employee/Department/Leave Management
# ================================================================
@login_required
@group_required('HR')
def hr_employee_list(request):
    employees = Employee.objects.select_related('user', 'department').all()
    return render(request, 'core/hr_employee_list.html', {'employees': employees})


@login_required
@group_required('HR')
def hr_department_list(request):
    departments = Department.objects.all()
    return render(request, 'core/hr_department_list.html', {'departments': departments})


@login_required
@group_required('HR')
def hr_leave_list(request):
    leaves = LeaveRequest.objects.select_related("employee").all().order_by("-requested_at")
    return render(request, 'core/hr_leave_list.html', {"leaves": leaves})


@login_required
@group_required('HR')
def approve_leave(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    leave.status = "A"
    leave.save()
    return redirect("hr_leave_list")


@login_required
@group_required('HR')
def reject_leave(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    leave.status = "R"
    leave.save()
    return redirect("hr_leave_list")


# ================================================================
# Attendance
# ================================================================
@login_required
def mark_attendance(request):
    emp = get_object_or_404(Employee, user=request.user)
    today = timezone.localdate()
    att, _ = Attendance.objects.get_or_create(employee=emp, date=today)

    if request.method == 'POST':
        action = request.POST.get('action')
        now = timezone.localtime()
        if action == 'checkin':
            att.check_in = now.time()
        elif action == 'checkout':
            att.check_out = now.time()
        att.save()
        return redirect('attendance_view')

    return render(request, 'core/attendance_mark.html', {'attendance': att})


@login_required
def add_attendance(request):
    employee = get_object_or_404(Employee, user=request.user)
    if request.method == "POST":
        form = AttendanceForm(request.POST)
        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.employee = employee
            attendance.save()
            return redirect("employee_dashboard")
    else:
        form = AttendanceForm()
    return render(request, "core/add_attendance.html", {"form": form})


@login_required
def attendance_view(request):
    emp = get_object_or_404(Employee, user=request.user)
    records = Attendance.objects.filter(employee=emp).order_by('-date')[:50]
    return render(request, 'core/attendance_view.html', {'records': records})


# ================================================================
# Leave Requests
# ================================================================
@login_required
def leave_request_create(request):
    emp = get_object_or_404(Employee, user=request.user)
    if request.method == "POST":
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = emp
            leave.status = 'P'
            leave.save()

            admins = User.objects.filter(groups__name__in=["HR", "Admin"])
            for a in admins:
                Notification.objects.create(
                    user=a,
                    title="New leave request",
                    message=f"{emp.user.username} requested leave {leave.start_date} → {leave.end_date}",
                )
            return redirect("leave_list")
    else:
        form = LeaveRequestForm()

    return render(request, "core/leave_request_form.html", {"form": form})


@login_required
def leave_list(request):
    if is_hr(request.user):
        leaves = LeaveRequest.objects.select_related("employee").all().order_by("-requested_at")
    else:
        emp = get_object_or_404(Employee, user=request.user)
        leaves = LeaveRequest.objects.filter(employee=emp).order_by("-requested_at")

    return render(request, "core/leave_list.html", {"leaves": leaves})


@login_required
@group_required('HR')
def leave_process(request, pk, action):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    leave.status = 'A' if action == 'approve' else 'R'
    leave.processed_by = request.user
    leave.processed_at = timezone.now()
    leave.save()

    Notification.objects.create(
        user=leave.employee.user,
        title='Leave update',
        message=f'Your leave request from {leave.start_date} to {leave.end_date} was {leave.get_status_display()}'
    )
    return redirect('leave_list')


# ================================================================
# Payroll
# ================================================================
@login_required
@group_required('HR')
def generate_payroll_for_employee(request, emp_id):
    employee = get_object_or_404(Employee, pk=emp_id)
    today = date.today()
    start = date(today.year, today.month, 1)
    end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])

    gross = employee.salary
    nssf = calc_nssf(gross)
    nhif = calc_nhif(gross)
    paye = calc_paye(gross)
    other = Decimal('0.00')
    net = gross - nssf - nhif - paye - other

    payroll = Payroll.objects.create(
        employee=employee,
        period_start=start,
        period_end=end,
        gross_salary=gross,
        nssf=nssf,
        nhif=nhif,
        paye=paye,
        other_deductions=other,
        net_pay=net,
        processed_by=request.user,
        status=request.POST.get("status", "Pending")
    )

    Notification.objects.create(
        user=employee.user,
        title='Payslip generated',
        message=f'Payslip for {start} to {end} generated.'
    )
    return redirect('payroll_detail', pk=payroll.pk)


@login_required
def payroll_detail(request, pk):
    payroll = get_object_or_404(Payroll, pk=pk)
    if request.user != payroll.employee.user and not is_hr(request.user):
        return redirect('employee_dashboard')
    return render(request, 'core/payroll_detail.html', {'payroll': payroll})


@login_required
@group_required('HR')
def payroll_mark_paid(request, pk):
    payroll = get_object_or_404(Payroll, pk=pk)
    payroll.status = "Paid"
    payroll.save()

    Notification.objects.create(
        user=payroll.employee.user,
        title="Salary Payment",
        message=f"Your salary for {payroll.period_start} → {payroll.period_end} has been marked as PAID."
    )
    return redirect("payroll_detail", pk=pk)


# ================================================================
# HR Dashboard
# ================================================================
@login_required
@group_required('HR')
def hr_dashboard(request):
    employees = Employee.objects.all()
    departments = Department.objects.all()
    pending_leaves = LeaveRequest.objects.filter(status='P')
    payrolls = Payroll.objects.all().order_by("-period_end")[:5]

    context = {
        "employees_count": employees.count(),
        "departments_count": departments.count(),
        "pending_leaves": pending_leaves,
        "recent_payrolls": payrolls,
    }
    return render(request, 'core/hr_dashboard.html', context)


# ================================================================
# Reports
# ================================================================
@login_required
@group_required('HR')
def employee_report(request):
    data = Employee.objects.values("department").annotate(total=models.Count("id"))
    return render(request, "reports/employee_report.html", {"data": data})


@login_required
@group_required('HR')
def attendance_report(request):
    data = Attendance.objects.values("date", "status").annotate(total=models.Count("id")).order_by("date")
    return render(request, "reports/attendance_report.html", {"data": data})


@login_required
@group_required('HR')
def salary_report(request):
    data = Employee.objects.aggregate(total_salary=models.Sum("salary"))
    return render(request, "reports/salary_report.html", {"data": data})
