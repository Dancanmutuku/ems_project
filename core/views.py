# core/views.py
from decimal import Decimal
from datetime import date
import calendar
from itertools import count

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.models import User

from .models import Employee, Attendance, LeaveRequest, Payroll, Notification
from .forms import LeaveRequestForm
from .utils import calc_nssf, calc_nhif, calc_paye, group_required


# ================================================================
# Authentication
# ================================================================
def employee_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('employee_dashboard')
        else:
            messages.error(request, "Invalid username or password")
    return render(request, 'registration/login.html')


# ================================================================
# Employee Dashboard
# ================================================================
@login_required
def employee_dashboard(request):
    employee = get_object_or_404(Employee, user=request.user)
    payrolls = Payroll.objects.filter(employee=employee).order_by('-period_end')[:6]
    leaves = LeaveRequest.objects.filter(employee=employee).order_by('-requested_at')[:5]
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]

    return render(request, "core/employee_dashboard.html", {
        "employee": employee,
        "payrolls": payrolls,
        "leaves": leaves,
        "notifications": notifications
    })


# ================================================================
# Profile & Employee Management
# ================================================================
@login_required
def my_profile(request):
    emp = get_object_or_404(Employee, user=request.user)
    return render(request, 'core/my_profile.html', {'employee': emp})


@login_required
def employee_list(request):
    if not request.user.is_staff and not request.user.groups.filter(name__in=['HR', 'Admin']).exists():
        return redirect('my_profile')
    employees = Employee.objects.select_related('user', 'department').all()
    return render(request, 'core/employee_list.html', {'employees': employees})


# ================================================================
# Attendance
# ================================================================
@login_required
def mark_attendance(request):
    emp = get_object_or_404(Employee, user=request.user)
    today = timezone.localdate()
    att, created = Attendance.objects.get_or_create(employee=emp, date=today)

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
            leave.status = 'P'  # Pending by default
            leave.save()

            # Notify HR/Admin
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
    is_hr_admin = request.user.groups.filter(name__in=['HR', 'Admin']).exists()

    if is_hr_admin:
        leaves = LeaveRequest.objects.select_related("employee").all().order_by("-requested_at")
    else:
        emp = get_object_or_404(Employee, user=request.user)
        leaves = LeaveRequest.objects.filter(employee=emp).order_by("-requested_at")

    return render(request, "core/leave_list.html", {"leaves": leaves, "is_hr_admin": is_hr_admin})


@login_required
def leave_process(request, pk, action):
    if not request.user.groups.filter(name='HR').exists():
        return redirect('leave_list')

    leave = get_object_or_404(LeaveRequest, pk=pk)
    leave.status = 'A' if action == 'approve' else 'R'
    leave.processed_by = request.user
    leave.processed_at = timezone.now()
    leave.save()

    # Notify employee
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
def generate_payroll_for_employee(request, emp_id):
    if not request.user.groups.filter(name__in=['HR', 'Admin']).exists():
        return redirect('home')

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
    status=request.POST.get("status", "Pending")  # 🔹 Take from form if provided
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
    if request.user != payroll.employee.user and not request.user.groups.filter(name__in=['HR', 'Admin']).exists():
        return redirect('home')
    return render(request, 'core/payroll_detail.html', {'payroll': payroll})


@login_required
@group_required('HR')
def payroll_mark_paid(request, pk):
    """HR/Admin marks payroll as paid"""
    payroll = get_object_or_404(Payroll, pk=pk)
    payroll.status = "Paid"
    payroll.save()

    # Notify employee
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
    return render(request, 'hr_dashboard.html')


# ================================================================
# Reports
# ================================================================
@login_required
def employee_report(request):
    data = Employee.objects.values("department").annotate(total=count("id"))
    return render(request, "reports/employee_report.html", {"data": data})


@login_required
def attendance_report(request):
    data = Attendance.objects.values("date", "status").annotate(total=count("id")).order_by("date")
    return render(request, "reports/attendance_report.html", {"data": data})


@login_required
def salary_report(request):
    data = Employee.objects.aggregate(total_salary=sum("salary"))
    return render(request, "reports/salary_report.html", {"data": data})
