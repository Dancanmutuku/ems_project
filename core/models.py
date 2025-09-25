from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from .utils import calc_nssf, calc_sha, calc_paye

# --------------------------
# HR Model
# --------------------------
class HR(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.user.username

# --------------------------
# Choices
# --------------------------
GENDER_CHOICES = (('M', 'Male'), ('F', 'Female'), ('O', 'Other'))
LEAVE_STATUS = (('P', 'Pending'), ('A', 'Approved'), ('R', 'Rejected'))

# --------------------------
# Department Model
# --------------------------
class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

# --------------------------
# Employee Model
# --------------------------
class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    contact = models.CharField(max_length=20, blank=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    address = models.TextField(blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    hire_date = models.DateField(null=True, blank=True)
    is_active_employee = models.BooleanField(default=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    annual_leave_balance = models.IntegerField(default=20)
    sick_leave_balance = models.IntegerField(default=10)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"

    def calculate_net_salary(self):
        gross = self.salary
        nssf = calc_nssf(gross)
        sha = calc_sha(gross)
        paye = calc_paye(gross)
        other = Decimal('0.00')
        net = gross - nssf - sha - paye - other
        return {"gross": gross, "nssf": nssf, "sha": sha, "paye": paye, "other": other, "net": net}

# --------------------------
# Employee Document
# --------------------------
class EmployeeDocument(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    doc = models.FileField(upload_to='employee_docs/%Y/%m/')
    doc_type = models.CharField(max_length=50, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee} - {self.doc_type}"

# --------------------------
# Attendance
# --------------------------
class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance')
    date = models.DateField(auto_now_add=True)
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    STATUS_CHOICES = [('Present', 'Present'), ('Absent', 'Absent'), ('Leave', 'Leave')]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Present')

    def __str__(self):
        return f"{self.employee.user.username} - {self.date}"

# --------------------------
# Leave Requests
# --------------------------
class LeaveRequest(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leaves')
    leave_type = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=1, choices=LEAVE_STATUS, default='P')
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    processed_at = models.DateTimeField(null=True, blank=True)

    def duration(self):
        return (self.end_date - self.start_date).days + 1

    def __str__(self):
        return f"{self.employee} {self.leave_type} {self.start_date}→{self.end_date} [{self.status}]"

class Leave(models.Model):
    STATUS_CHOICES = [
        ("P", "Pending"),
        ("A", "Approved"),
        ("R", "Rejected"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="P")
    applied_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # to track who applied
    created_at = models.DateTimeField(auto_now_add=True)

# --------------------------
# Payroll
# --------------------------
class Payroll(models.Model):
    STATUS_PENDING = 'Pending'
    STATUS_PAID = 'Paid'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PAID, 'Paid'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payrolls')
    period_start = models.DateField()
    period_end = models.DateField()
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    paye = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    sha = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    nssf = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    net_pay = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)

    # ----- PAYE Calculation -----
    def calculate_paye(self, taxable_income: Decimal) -> Decimal:
        tax = Decimal('0.00')
        bands = [
            (Decimal('24000'), Decimal('0.10')),
            (Decimal('8333'), Decimal('0.25')),
            (Decimal('999999999'), Decimal('0.30')),
        ]
        remaining = taxable_income
        for band_limit, rate in bands:
            if remaining <= 0:
                break
            taxable = min(remaining, band_limit)
            tax += taxable * rate
            remaining -= taxable
        return tax.quantize(Decimal('0.01'))

    # ----- NHIF / SHA Calculation -----
    def calculate_nhif(self, gross: Decimal) -> Decimal:
        sha_brackets = [
            (Decimal("5999"), 150), (Decimal("7999"), 300), (Decimal("11999"), 400),
            (Decimal("14999"), 500), (Decimal("19999"), 600), (Decimal("24999"), 750),
            (Decimal("29999"), 850), (Decimal("34999"), 900), (Decimal("39999"), 950),
            (Decimal("44999"), 1000), (Decimal("49999"), 1100), (Decimal("59999"), 1200),
            (Decimal("69999"), 1300), (Decimal("79999"), 1400), (Decimal("89999"), 1500),
            (Decimal("99999"), 1600), (Decimal("999999999"), 1700)
        ]
        for limit, amount in sha_brackets:
            if gross <= limit:
                return Decimal(amount)
        return Decimal('0.00')

    def calculate_sha(self, gross: Decimal) -> Decimal:
        return self.calculate_nhif(gross)

    # ----- NSSF Calculation -----
    def calculate_nssf(self, gross: Decimal) -> Decimal:
        tier1 = min(gross, Decimal("7000")) * Decimal("0.06")
        tier2 = max(Decimal('0.00'), min(gross - Decimal("7000"), Decimal("29000")) * Decimal("0.06")
                    if gross > Decimal("7000") else Decimal("0.00"))
        return (tier1 + tier2).quantize(Decimal('0.01'))

    # ----- Override save -----
    def save(self, *args, **kwargs):
        # Ensure Decimal types
        self.basic_salary = Decimal(self.basic_salary)
        self.allowances = Decimal(self.allowances)

        # Gross salary
        self.gross_salary = self.basic_salary + self.allowances

        # NSSF deduction
        self.nssf = self.calculate_nssf(self.gross_salary)

        # PAYE deduction
        taxable_income = self.gross_salary - self.nssf
        self.paye = self.calculate_paye(taxable_income)

        # SHA / NHIF deduction
        self.sha = self.calculate_sha(self.gross_salary)

        # Net pay
        self.net_pay = (self.gross_salary - (self.paye + self.nssf + self.sha)).quantize(Decimal('0.01'))

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} [{self.period_start} - {self.period_end}] - {self.get_status_display()}"
# --------------------------
# KPI
# --------------------------
class KPI(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='kpis')
    name = models.CharField(max_length=200)
    target = models.FloatField()
    actual = models.FloatField(null=True, blank=True)
    review_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def rating(self):
        if self.actual is None:
            return None
        try:
            return round((self.actual / self.target) * 5, 2)
        except:
            return None

    def __str__(self):
        return f"{self.employee} KPI: {self.name}"

# --------------------------
# Notifications
# --------------------------
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"To {self.user}: {self.title}"
