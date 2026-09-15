// In-memory data store for Employee Management System (EMS)

export function calculateNssf(gross) {
  const g = Number(gross) || 0;
  const tier1 = Math.min(g, 7000) * 0.06;
  const tier2 = g > 7000 ? Math.min(g - 7000, 29000) * 0.06 : 0;
  return Number((tier1 + tier2).toFixed(2));
}

export function calculateSha(gross) {
  const g = Number(gross) || 0;
  const brackets = [
    [5999, 150], [7999, 300], [11999, 400], [14999, 500],
    [19999, 600], [24999, 750], [29999, 850], [34999, 900],
    [39999, 950], [44999, 1000], [49999, 1100], [59999, 1200],
    [69999, 1300], [79999, 1400], [89999, 1500], [99999, 1600]
  ];
  for (const [limit, amount] of brackets) {
    if (g <= limit) return amount;
  }
  return 1700;
}

export function calculatePaye(taxableIncome) {
  let remaining = Number(taxableIncome) || 0;
  let tax = 0;
  const bands = [
    [24000, 0.10],
    [8333, 0.25],
    [Infinity, 0.30]
  ];
  for (const [bandLimit, rate] of bands) {
    if (remaining <= 0) break;
    const taxable = Math.min(remaining, bandLimit);
    tax += taxable * rate;
    remaining -= taxable;
  }
  return Number(tax.toFixed(2));
}

export function computePayrollBreakdown(basicSalary, allowances = 0) {
  const basic = Number(basicSalary) || 0;
  const allow = Number(allowances) || 0;
  const gross = basic + allow;
  const nssf = calculateNssf(gross);
  const taxable = Math.max(0, gross - nssf);
  const paye = calculatePaye(taxable);
  const sha = calculateSha(gross);
  const net = Number((gross - paye - nssf - sha).toFixed(2));
  return {
    basicSalary: basic,
    allowances: allow,
    grossSalary: gross,
    nssf,
    taxable,
    paye,
    sha,
    netPay: net
  };
}

export const departments = [
  { id: 1, name: "Engineering & IT", description: "Software development, network management and IT support" },
  { id: 2, name: "Human Resources", description: "Talent acquisition, employee welfare, and company policies" },
  { id: 3, name: "Finance & Accounting", description: "Financial reporting, payroll, budgeting, and taxation" },
  { id: 4, name: "Operations & Logistics", description: "Facilities, procurement, and daily logistics management" },
  { id: 5, name: "Sales & Marketing", description: "Brand promotion, client relations, and market expansion" }
];

export const users = [
  { id: 1, username: "admin", password: "password123", email: "hr@techpak.co.ke", role: "HR", fullName: "Sarah Wanjiku" },
  { id: 2, username: "dancan", password: "password123", email: "dancan@techpak.co.ke", role: "Employee", fullName: "Dancan Mutuku" },
  { id: 3, username: "jane", password: "password123", email: "jane.achieng@techpak.co.ke", role: "Employee", fullName: "Jane Achieng" },
  { id: 4, username: "kevin", password: "password123", email: "kevin.otieno@techpak.co.ke", role: "Employee", fullName: "Kevin Otieno" }
];

export const employees = [
  {
    id: 1,
    userId: 2,
    employeeId: "EMP-001",
    fullName: "Dancan Mutuku",
    email: "dancan@techpak.co.ke",
    contact: "+254 712 345 678",
    dob: "1994-05-18",
    gender: "M",
    address: "Westlands, Nairobi, Kenya",
    jobTitle: "Lead Software Engineer",
    departmentId: 1,
    hireDate: "2022-01-15",
    contractStart: "2022-01-15",
    contractEnd: "2027-01-15",
    isActiveEmployee: true,
    salary: 95000,
    annualLeaveBalance: 18,
    sickLeaveBalance: 10,
    emergencyContactName: "Faith Mutuku",
    emergencyContactPhone: "+254 722 987 654"
  },
  {
    id: 2,
    userId: 3,
    employeeId: "EMP-002",
    fullName: "Jane Achieng",
    email: "jane.achieng@techpak.co.ke",
    contact: "+254 723 456 789",
    dob: "1992-09-24",
    gender: "F",
    address: "Kilimani, Nairobi, Kenya",
    jobTitle: "Senior Accountant",
    departmentId: 3,
    hireDate: "2021-06-01",
    contractStart: "2021-06-01",
    contractEnd: "2026-06-01",
    isActiveEmployee: true,
    salary: 78000,
    annualLeaveBalance: 14,
    sickLeaveBalance: 8,
    emergencyContactName: "Peter Ochieng",
    emergencyContactPhone: "+254 733 112 233"
  },
  {
    id: 3,
    userId: 4,
    employeeId: "EMP-003",
    fullName: "Kevin Otieno",
    email: "kevin.otieno@techpak.co.ke",
    contact: "+254 734 567 890",
    dob: "1996-11-12",
    gender: "M",
    address: "South C, Nairobi, Kenya",
    jobTitle: "Operations Supervisor",
    departmentId: 4,
    hireDate: "2023-03-10",
    contractStart: "2023-03-10",
    contractEnd: "2025-03-10",
    isActiveEmployee: true,
    salary: 62000,
    annualLeaveBalance: 20,
    sickLeaveBalance: 10,
    emergencyContactName: "Grace Otieno",
    emergencyContactPhone: "+254 744 556 677"
  }
];

export const attendances = [
  { id: 1, employeeId: 1, date: "2026-09-15", checkIn: "08:15", checkOut: "17:05", status: "Present" },
  { id: 2, employeeId: 1, date: "2026-09-14", checkIn: "08:25", checkOut: "17:15", status: "Present" },
  { id: 3, employeeId: 1, date: "2026-09-13", checkIn: "08:30", checkOut: "16:55", status: "Present" },
  { id: 4, employeeId: 2, date: "2026-09-15", checkIn: "08:05", checkOut: "17:00", status: "Present" },
  { id: 5, employeeId: 2, date: "2026-09-14", checkIn: "08:10", checkOut: "17:00", status: "Present" },
  { id: 6, employeeId: 3, date: "2026-09-15", checkIn: "08:45", checkOut: "17:30", status: "Present" },
  { id: 7, employeeId: 3, date: "2026-09-14", checkIn: "", checkOut: "", status: "Absent" }
];

export const leaveRequests = [
  {
    id: 1,
    employeeId: 1,
    leaveType: "Annual",
    startDate: "2026-10-05",
    endDate: "2026-10-09",
    reason: "Annual family holiday in Mombasa",
    status: "P", // Pending
    requestedAt: "2026-09-12 10:30"
  },
  {
    id: 2,
    employeeId: 2,
    leaveType: "Sick",
    startDate: "2026-09-01",
    endDate: "2026-09-02",
    reason: "Doctor appointment and recovery",
    status: "A", // Approved
    requestedAt: "2026-08-30 09:15"
  },
  {
    id: 3,
    employeeId: 3,
    leaveType: "Annual",
    startDate: "2026-09-20",
    endDate: "2026-09-25",
    reason: "Personal commitment and family event",
    status: "P",
    requestedAt: "2026-09-14 14:00"
  }
];

export const payrolls = [
  {
    id: 1,
    employeeId: 1,
    periodStart: "2026-08-01",
    periodEnd: "2026-08-31",
    basicSalary: 95000,
    allowances: 10000,
    ...computePayrollBreakdown(95000, 10000),
    status: "Paid"
  },
  {
    id: 2,
    employeeId: 2,
    periodStart: "2026-08-01",
    periodEnd: "2026-08-31",
    basicSalary: 78000,
    allowances: 5000,
    ...computePayrollBreakdown(78000, 5000),
    status: "Paid"
  },
  {
    id: 3,
    employeeId: 3,
    periodStart: "2026-08-01",
    periodEnd: "2026-08-31",
    basicSalary: 62000,
    allowances: 4000,
    ...computePayrollBreakdown(62000, 4000),
    status: "Pending"
  },
  {
    id: 4,
    employeeId: 1,
    periodStart: "2026-07-01",
    periodEnd: "2026-07-31",
    basicSalary: 95000,
    allowances: 10000,
    ...computePayrollBreakdown(95000, 10000),
    status: "Paid"
  }
];

export const notifications = [
  { id: 1, userId: 2, title: "August Payslip Available", message: "Your August 2026 payslip has been processed and is ready for download.", createdAt: "2026-09-01", read: false },
  { id: 2, userId: 2, title: "Company Q3 Townhall", message: "All hands meeting scheduled for Friday at 3:00 PM in the main conference hall.", createdAt: "2026-09-10", read: false },
  { id: 3, userId: 3, title: "Leave Request Approved", message: "Your sick leave request for 2026-09-01 has been approved.", createdAt: "2026-08-31", read: true },
  { id: 4, userId: 4, title: "Welcome to Techpak EMS", message: "Welcome aboard! Please update your emergency contact details.", createdAt: "2026-09-01", read: true }
];

let nextId = 100;
export function getNextId() {
  return ++nextId;
}
