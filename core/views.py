# core/views.py
import csv
from decimal import Decimal
from datetime import date, timedelta
import calendar
import logging
import os

from django import forms
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import models
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.conf import settings
from django.views.decorators.http import require_POST
from django.forms import modelform_factory

from .models import Employee, Attendance, LeaveRequest, Payroll, Notification, Department
from .forms import EmployeeForm, LeaveRequestForm, AttendanceForm, DepartmentForm, UserForm
from .utils import calc_nssf, calc_sha, calc_paye
from .forms import PayrollForm  # we’ll create this next

def payroll_list(request):
    payrolls = Payroll.objects.all()  # <- fetch all payroll records
    return render(request, 'core/payroll_list.html', {'payrolls': payrolls})

def payroll_add(request):
    if request.method == 'POST':
        form = PayrollForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('payroll_list')
    else:
        form = PayrollForm()
    return render(request, 'core/payroll_form.html', {'form': form})

def payroll_edit(request, pk):
    payroll = get_object_or_404(Payroll, pk=pk)
    if request.method == 'POST':
        form = PayrollForm(request.POST, instance=payroll)
        if form.is_valid():
            form.save()
            return redirect('payroll_list')
    else:
        form = PayrollForm(instance=payroll)
    return render(request, 'core/payroll_form.html', {'form': form})
# ================================================================
# Logger
# ================================================================
logger = logging.getLogger(__name__)

# ================================================================
# PDF Helper
# ================================================================
def link_callback(uri, rel):
    """Convert HTML URIs to absolute system paths for xhtml2pdf."""
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    elif uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
    else:
        return uri
    if not os.path.exists(path):
        raise Exception(f"Media URI not found: {path}")
    return path

# ================================================================
# Role & Group Helpers
# ================================================================
def group_required(group_name):
    """Decorator to require user to belong to a specific group."""
    def check(user):
        return user.is_superuser or user.groups.filter(name=group_name).exists()
    return user_passes_test(check)

def is_hr(user):
    """Check if user is HR or superuser."""
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name="HR").exists())

# ================================================================
# Authentication
# ================================================================
def hr_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user and is_hr(user):
            login(request, user)
            return redirect("hr_dashboard")
        messages.error(request, "Invalid HR credentials or not authorized.")
    return render(request, "registration/hr_login.html")

def employee_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            Employee.objects.get_or_create(user=user)  # Ensure Employee profile exists
            return redirect('hr_dashboard') if is_hr(user) else redirect('employee_dashboard')
        messages.error(request, "Invalid username or password")
    return render(request, 'registration/login.html')

@login_required
@require_POST
def employee_logout(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect("login")

# ================================================================
# Employee Dashboard
# ================================================================
@login_required
def employee_dashboard(request):
    try:
        employee = get_object_or_404(Employee, user=request.user)
        payrolls = Payroll.objects.filter(employee=employee).order_by('-period_start')[:5]
        attendance_records = employee.attendance.order_by('-date')[:5] if hasattr(employee, 'attendance') else []
        leaves = employee.leaves.order_by('-start_date')[:5] if hasattr(employee, 'leaves') else []
        notifications = employee.user.notifications.order_by('-created_at')[:5] if hasattr(employee.user, 'notifications') else []
        total_present = employee.attendance.filter(status='Present').count() if hasattr(employee, 'attendance') else 0

        context = {
            "employee": employee,
            "payrolls": payrolls,
            "attendance_records": attendance_records,
            "leaves": leaves,
            "notifications": notifications,
            "total_present": total_present,
        }
        return render(request, "core/employee_dashboard.html", context)
    except Employee.DoesNotExist:
        logger.error(f"No Employee profile found for user {request.user.username}")
        messages.error(request, "Employee profile not found. Contact admin.")
        return redirect('login')
    except Exception as e:
        logger.exception(f"Error in employee_dashboard for user {request.user.username}: {e}")
        messages.error(request, "An unexpected error occurred. Try again later.")
        return redirect('login')

# ================================================================
# Profile
# ================================================================
@login_required
def my_profile(request):
    emp = get_object_or_404(Employee, user=request.user)
    return render(request, 'core/my_profile.html', {'employee': emp})

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
# HR Management: Employee CRUD
# ================================================================
@login_required
@group_required('HR')
def hr_employee_list(request):
    employees = Employee.objects.select_related('user', 'department').all()
    return render(request, 'hr/hr_employee_list.html', {'employees': employees})

@login_required
@group_required('HR')
def hr_employee_create(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
        else:
            # Create the Django User
            user = User.objects.create_user(username=username, email=email, password=password)
            
            # Create the Employee linked to the User
            employee_form = EmployeeForm(request.POST, request.FILES)
            if employee_form.is_valid():
                employee = employee_form.save(commit=False)
                employee.user = user
                employee.save()
                messages.success(request, "Employee created successfully!")
                return redirect('hr_employee_list')
            else:
                messages.error(request, "Please fix the errors below.")
    else:
        employee_form = EmployeeForm()

    return render(request, "hr/hr_employee_form.html", {
        "employee_form": employee_form
    })

@login_required
@group_required('HR')
def hr_employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    EmployeeFormClass = modelform_factory(Employee, exclude=['user'])
    if request.method == "POST":
        form = EmployeeFormClass(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, "Employee updated successfully.")
            return redirect("hr_employee_list")
    else:
        form = EmployeeFormClass(instance=employee)

    return render(request, "hr/hr_employee_form.html", {
        "employee_form": form,
        "employee": employee
    })

@login_required
@group_required('HR')
def hr_employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        employee.delete()
        messages.success(request, "Employee deleted successfully.")
        return redirect("hr_employee_list")
    return render(request, "core/confirm_delete.html", {"object": employee, "type": "Employee"})
# ================================================================
# HR Management: Department CRUD
# ================================================================
@login_required
@group_required('HR')
def hr_department_list(request):
    departments = Department.objects.all()
    return render(request, 'core/hr_department_list.html', {'departments': departments})

@login_required
@group_required('HR')
def hr_department_create(request):
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department created successfully.")
            return redirect("hr_department_list")
    else:
        form = DepartmentForm()
    return render(request, "core/hr_department_form.html", {"form": form, "title": "Add Department"})

@login_required
@group_required('HR')
def hr_department_edit(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated successfully.")
            return redirect("hr_department_list")
    else:
        form = DepartmentForm(instance=department)
    return render(request, "core/hr_department_form.html", {"form": form, "title": "Edit Department"})

@login_required
@group_required('HR')
def hr_department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        department.delete()
        messages.success(request, "Department deleted successfully.")
        return redirect("hr_department_list")
    return render(request, "core/confirm_delete.html", {"object": department, "type": "Department"})

# ================================================================
# Leave Management
# ================================================================
@login_required
@group_required('HR')
def hr_leave_list(request):
    status = request.GET.get("status")
    leaves = LeaveRequest.objects.select_related("employee", "employee__department").all().order_by("-requested_at")
    if status in ["P", "A", "R"]:
        leaves = leaves.filter(status=status)
    return render(request, "core/hr_leave_list.html", {"leaves": leaves})

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
@login_required
def leave_request_create(request):
    is_hr = request.user.groups.filter(name="HR").exists()

    if request.method == "POST":
        form = LeaveRequestForm(request.POST)

        if form.is_valid():
            leave = form.save(commit=False)

            if is_hr:
                # HR selects employee from dropdown
                selected_employee = form.cleaned_data.get('employee')
                if not selected_employee:
                    form.add_error('employee', 'Please select an employee.')
                    return render(request, "core/leave_request_form.html", {"form": form, "is_hr": is_hr})
                leave.employee = selected_employee
            else:
                # Regular employee: assign themselves
                leave.employee = get_object_or_404(Employee, user=request.user)

            leave.status = 'P'
            leave.requested_at = timezone.now()
            leave.save()

            return redirect('leave_list')

    else:
        form = LeaveRequestForm()
        if not is_hr:
            # Hide employee dropdown for regular employees
            form.fields['employee'].widget = forms.HiddenInput()

    return render(request, "core/leave_request_form.html", {"form": form, "is_hr": is_hr})
@login_required
def leave_list(request):
    if is_hr(request.user):
        leaves = LeaveRequest.objects.select_related("employee").all().order_by("-requested_at")
    else:
        emp = get_object_or_404(Employee, user=request.user)
        leaves = LeaveRequest.objects.filter(employee=emp).order_by("-requested_at")
    return render(request, "core/leave_list.html", {"leaves": leaves})

@login_required
@group_required("HR")
def leave_process(request, pk, action):
    """
    HR can approve, reject, or set a leave back to pending.
    Sends a notification to the employee.
    """
    leave = get_object_or_404(LeaveRequest, pk=pk)

    if action == "approve":
        leave.status = "A"
        messages.success(request, f"Leave for {leave.employee} approved.")
    elif action == "reject":
        leave.status = "R"
        messages.error(request, f"Leave for {leave.employee} rejected.")
    elif action == "pending":
        leave.status = "P"
        messages.info(request, f"Leave for {leave.employee} set back to pending.")
    else:
        messages.warning(request, "Invalid action.")
        return redirect("leave_list")

    leave.processed_by = request.user
    leave.processed_at = timezone.now()
    leave.save()

    # Notify employee of status change
    Notification.objects.create(
        user=leave.employee.user,
        title="Leave Request Update",
        message=f"Your leave request from {leave.start_date} to {leave.end_date} "
                f"was marked as {leave.get_status_display()}."
    )

    return redirect("leave_list")
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
    sha = calc_sha(gross)
    paye = calc_paye(gross)
    other = Decimal('0.00')
    net = gross - nssf - sha - paye - other

    payroll = Payroll.objects.create(
        employee=employee,
        period_start=start,
        period_end=end,
        gross_salary=gross,
        nssf=nssf,
        sha=sha,
        paye=paye,
        net_pay=net,
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

def payroll_delete(request, pk):
    payroll = get_object_or_404(Payroll, pk=pk)
    payroll.delete()
    messages.success(request, "Payroll deleted successfully.")
    return redirect("payroll_list")

# ================================================================
# Employee Payroll Views
# ================================================================
@login_required
def employee_payroll(request):
    employee = get_object_or_404(Employee, user=request.user)
    payrolls = Payroll.objects.filter(employee=employee).order_by('-period_end')
    return render(request, "employee/employee_payroll.html", {"payrolls": payrolls})

@login_required
def payroll_pdf(request, payroll_id):
    payroll = get_object_or_404(Payroll, id=payroll_id)
    employee = payroll.employee

    if request.user != employee.user and not is_hr(request.user):
        return HttpResponse("Unauthorized access", status=403)

    html = render_to_string("employee/payroll_pdf.html", {
        "payroll": payroll,
        "employee": employee,
        "generated_at": timezone.now(),
    })

    filename = f"payslip_{employee.user.username}_{payroll.period_start}_{payroll.period_end}.pdf"
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    try:
        pisa_status = pisa.CreatePDF(html, dest=response, link_callback=link_callback)
        if pisa_status.err:
            logger.error(f"PDF generation failed for payroll {payroll.id}: {pisa_status.err}")
            return HttpResponse("Error generating PDF.", status=500)
    except Exception as e:
        logger.exception(f"Exception during PDF generation: {e}")
        return HttpResponse("Error generating PDF.", status=500)

    return response

# ================================================================
# Reports
# ================================================================
@login_required
@group_required('HR')
def employee_report(request):
    """HR dashboard: Summary + detailed reports (Employees, Payroll, Attendance, Leaves)"""
    # Summary cards
    total_employees = Employee.objects.count()
    pending_leaves = LeaveRequest.objects.filter(status="Pending").count()
    monthly_payroll = Payroll.objects.filter(
        period_start__month=timezone.now().month,
        period_start__year=timezone.now().year
    ).aggregate(total=models.Sum('net_pay'))['total'] or 0
    expiring_contracts = Employee.objects.filter(
        contract_end__lte=timezone.now() + timedelta(days=30)
    ).count()

    # Table data
    employees = Employee.objects.select_related("user", "department")
    payrolls = Payroll.objects.select_related("employee", "employee__user").order_by("-period_start")
    attendance = Attendance.objects.select_related("employee", "employee__user").order_by("-date")[:50]
    leaves = LeaveRequest.objects.select_related("employee", "employee__user").order_by("-start_date")

    context = {
        "total_employees": total_employees,
        "pending_leaves": pending_leaves,
        "monthly_payroll": monthly_payroll,
        "expiring_contracts": expiring_contracts,
        "employees": employees,
        "payrolls": payrolls,
        "attendance": attendance,
        "leaves": leaves,
    }

    return render(request, "reports/employee_report.html", context)


@login_required
@group_required('HR')
def attendance_report(request):
    """Attendance summary by date"""
    data = Attendance.objects.values('date', 'status').annotate(total=models.Count('id')).order_by('date')
    return render(request, "reports/attendance_report.html", {"data": data})


@login_required
@group_required('HR')
def salary_report(request):
    """Full payroll list"""
    payrolls = Payroll.objects.select_related("employee__user").all()
    return render(request, "reports/salary_report.html", {"payrolls": payrolls})


# ================================================================
# Export Views
# ================================================================
@login_required
@group_required('HR')
def export_employees(request):
    """Export employees as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="employees.csv"'

    writer = csv.writer(response)
    writer.writerow(['Employee ID', 'Name', 'Department', 'Email'])

    employees = Employee.objects.select_related('department', 'user')
    for emp in employees:
        writer.writerow([
            emp.employee_id,
            emp.user.get_full_name(),
            emp.department.name if emp.department else '',
            emp.user.email
        ])
    return response


@login_required
@group_required('HR')
def export_attendance(request):
    """Export attendance as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendance.csv"'

    writer = csv.writer(response)
    writer.writerow(['Employee', 'Date', 'Check-in', 'Check-out', 'Status'])

    records = Attendance.objects.select_related('employee', 'employee__user')
    for record in records:
        writer.writerow([
            record.employee.user.get_full_name(),
            record.date,
            record.check_in,
            record.check_out,
            record.status
        ])
    return response


@login_required
@group_required('HR')
def export_salary(request):
    """Export salary report as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="salary_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Employee', 'Basic Pay', 'Allowances', 'Deductions', 'Net Pay'])

    payrolls = Payroll.objects.select_related('employee', 'employee__user')
    for p in payrolls:
        writer.writerow([
            p.employee.user.get_full_name(),
            p.basic_pay,
            p.allowances,
            p.deductions,
            p.net_pay
        ])
    return response

@login_required
@group_required('HR')
def export_payroll(request):
    """Export payroll data as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payroll_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Employee', 'Period Start', 'Period End', 'Gross Salary', 'Net Pay', 'Status'])

    payrolls = Payroll.objects.select_related('employee', 'employee__user')
    for p in payrolls:
        writer.writerow([
            p.employee.user.get_full_name(),
            p.period_start,
            p.period_end,
            p.gross_salary,
            p.net_pay,
            p.status
        ])
    return response
@login_required
@group_required('HR')
def export_leave(request):
    """Export leave requests as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="leave_requests.csv"'

    writer = csv.writer(response)
    writer.writerow(['Employee', 'Leave Type', 'Start Date', 'End Date', 'Status'])

    leaves = LeaveRequest.objects.select_related('employee', 'employee__user').all()
    for leave in leaves:
        writer.writerow([
            leave.employee.user.get_full_name(),
            leave.leave_type,
            leave.start_date,
            leave.end_date,
            leave.status
        ])
    return response
