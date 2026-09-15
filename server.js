import express from 'express';
import session from 'express-session';
import cookieParser from 'cookie-parser';
import path from 'path';
import { fileURLToPath } from 'url';
import {
  departments,
  users,
  employees,
  attendances,
  leaveRequests,
  payrolls,
  notifications,
  getNextId,
  computePayrollBreakdown
} from './data.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;

// Setup EJS template engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Middlewares
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(cookieParser());
app.use(express.static(path.join(__dirname, 'public')));
app.use('/assets', express.static(path.join(__dirname, 'src/assets')));

app.use(session({
  secret: process.env.SESSION_SECRET || 'ems_super_secret_session_key_2026',
  resave: false,
  saveUninitialized: true,
  cookie: { maxAge: 24 * 60 * 60 * 1000 }
}));

// Provide defaults & flash messages to templates
app.use((req, res, next) => {
  if (!req.session.user) {
    // Default to HR admin for instant preview experience
    req.session.user = users[0];
  }

  res.locals.currentUser = req.session.user || null;
  res.locals.currentPath = req.path;
  res.locals.successMessage = req.session.successMessage || null;
  res.locals.errorMessage = req.session.errorMessage || null;

  delete req.session.successMessage;
  delete req.session.errorMessage;
  next();
});

// Helper functions to enrich data
function getEnrichedEmployees() {
  return employees.map(emp => {
    const dept = departments.find(d => Number(d.id) === Number(emp.departmentId));
    return {
      ...emp,
      departmentName: dept ? dept.name : 'Unassigned'
    };
  });
}

function getEnrichedPayrolls() {
  return payrolls.map(p => {
    const emp = employees.find(e => Number(e.id) === Number(p.employeeId));
    return {
      ...p,
      employeeName: emp ? emp.fullName : 'Unknown Employee',
      employeeId: emp ? emp.employeeId : 'N/A'
    };
  });
}

function getEnrichedLeaves() {
  return leaveRequests.map(l => {
    const emp = employees.find(e => Number(e.id) === Number(l.employeeId));
    const start = new Date(l.startDate);
    const end = new Date(l.endDate);
    const diffTime = Math.abs(end - start);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
    return {
      ...l,
      employeeName: emp ? emp.fullName : 'Unknown Employee',
      leaveBalance: emp ? emp.annualLeaveBalance : 0,
      days: isNaN(diffDays) ? 1 : diffDays
    };
  });
}

function getEnrichedAttendances() {
  return attendances.map(a => {
    const emp = employees.find(e => Number(e.id) === Number(a.employeeId));
    return {
      ...a,
      employeeName: emp ? emp.fullName : 'Unknown Employee'
    };
  });
}

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', time: new Date().toISOString() });
});

// Quick Switcher between demo roles
app.get('/quick-switch', (req, res) => {
  const targetRole = req.query.role || 'HR';
  if (targetRole === 'HR') {
    req.session.user = users.find(u => u.role === 'HR') || users[0];
    req.session.successMessage = `Switched to HR Admin (${req.session.user.fullName})`;
    return res.redirect('/hr/dashboard');
  } else {
    req.session.user = users.find(u => u.role === 'Employee') || users[1];
    req.session.successMessage = `Switched to Employee View (${req.session.user.fullName})`;
    return res.redirect('/dashboard');
  }
});

// Auth Routes
app.get('/login', (req, res) => {
  res.render('login', { isHr: false });
});

app.get('/employee/login', (req, res) => {
  res.render('login', { isHr: false });
});

app.get('/hr/login', (req, res) => {
  res.render('login', { isHr: true });
});

app.post('/login', (req, res) => {
  const { username, password } = req.body;
  const user = users.find(u => u.username === username);
  if (user && user.password === password) {
    req.session.user = user;
    req.session.successMessage = `Welcome back, ${user.fullName}!`;
    return res.redirect(user.role === 'HR' ? '/hr/dashboard' : '/dashboard');
  }
  req.session.errorMessage = 'Invalid username or password';
  res.redirect('/login');
});

app.post('/hr/login', (req, res) => {
  const { username, password } = req.body;
  const user = users.find(u => u.username === username && u.role === 'HR');
  if (user && user.password === password) {
    req.session.user = user;
    req.session.successMessage = `Welcome back, ${user.fullName}!`;
    return res.redirect('/hr/dashboard');
  }
  req.session.errorMessage = 'Invalid HR credentials';
  res.redirect('/hr/login');
});

app.get('/logout', (req, res) => {
  req.session.user = null;
  res.redirect('/login');
});

app.get('/hr/logout', (req, res) => {
  req.session.user = null;
  res.redirect('/hr/login');
});

// Root Route
app.get('/', (req, res) => {
  if (req.session.user && req.session.user.role === 'HR') {
    return res.redirect('/hr/dashboard');
  }
  res.redirect('/dashboard');
});

// Employee Portal Routes
app.get(['/dashboard', '/employee_dashboard'], (req, res) => {
  const user = req.session.user;
  // Match employee record by userId or default to first employee
  let emp = employees.find(e => e.userId === user.id) || employees[0];
  const dept = departments.find(d => Number(d.id) === Number(emp.departmentId));
  const myPayrolls = payrolls.filter(p => Number(p.employeeId) === Number(emp.id));
  const myAttendances = attendances.filter(a => Number(a.employeeId) === Number(emp.id));
  const myLeaves = getEnrichedLeaves().filter(l => Number(l.employeeId) === Number(emp.id));
  const myNotifications = notifications.filter(n => Number(n.userId) === Number(user.id));
  const totalPresent = myAttendances.filter(a => a.status === 'Present').length;

  res.render('employee/dashboard', {
    employee: emp,
    department: dept,
    payrolls: myPayrolls,
    attendanceRecords: myAttendances,
    leaves: myLeaves,
    notifications: myNotifications,
    totalPresent
  });
});

app.get(['/profile', '/my_profile'], (req, res) => {
  const user = req.session.user;
  const emp = employees.find(e => e.userId === user.id) || employees[0];
  const dept = departments.find(d => Number(d.id) === Number(emp.departmentId));
  res.render('employee/profile', { employee: emp, department: dept });
});

app.get(['/attendance/view', '/attendance/mark'], (req, res) => {
  const user = req.session.user;
  const emp = employees.find(e => e.userId === user.id) || employees[0];
  const myAttendances = attendances.filter(a => Number(a.employeeId) === Number(emp.id));
  res.render('employee/attendance', {
    attendances: myAttendances,
    todayDate: new Date().toISOString().split('T')[0]
  });
});

app.post('/attendance/mark', (req, res) => {
  const user = req.session.user;
  const emp = employees.find(e => e.userId === user.id) || employees[0];
  const { date, checkIn, checkOut, status } = req.body;

  attendances.unshift({
    id: getNextId(),
    employeeId: emp.id,
    date: date || new Date().toISOString().split('T')[0],
    checkIn: checkIn || '08:30',
    checkOut: checkOut || '17:00',
    status: status || 'Present'
  });

  req.session.successMessage = `Attendance logged successfully for ${date}!`;
  res.redirect('/attendance/view');
});

app.get(['/leaves/list', '/leaves/add'], (req, res) => {
  const user = req.session.user;
  const emp = employees.find(e => e.userId === user.id) || employees[0];
  const myLeaves = getEnrichedLeaves().filter(l => Number(l.employeeId) === Number(emp.id));
  res.render('employee/leaves', {
    employee: emp,
    leaves: myLeaves
  });
});

app.post('/leaves/add', (req, res) => {
  const user = req.session.user;
  const emp = employees.find(e => e.userId === user.id) || employees[0];
  const { leaveType, startDate, endDate, reason } = req.body;

  leaveRequests.unshift({
    id: getNextId(),
    employeeId: emp.id,
    leaveType,
    startDate,
    endDate,
    reason,
    status: 'P',
    requestedAt: new Date().toISOString().replace('T', ' ').substring(0, 16)
  });

  req.session.successMessage = 'Leave request submitted successfully for HR approval!';
  res.redirect('/leaves/list');
});

app.get('/employee/payroll', (req, res) => {
  const user = req.session.user;
  const emp = employees.find(e => e.userId === user.id) || employees[0];
  const myPayrolls = payrolls.filter(p => Number(p.employeeId) === Number(emp.id));
  res.render('employee/payroll', { payrolls: myPayrolls });
});

app.get('/employee/payroll/:id/pdf', (req, res) => {
  const pid = Number(req.params.id);
  const payroll = payrolls.find(p => p.id === pid);
  if (!payroll) {
    req.session.errorMessage = 'Payroll slip not found';
    return res.redirect('/employee/payroll');
  }
  const emp = employees.find(e => Number(e.id) === Number(payroll.employeeId)) || employees[0];
  const dept = departments.find(d => Number(d.id) === Number(emp.departmentId));
  res.render('employee/payslip', { payroll, employee: emp, department: dept });
});

// HR Portal Routes
app.get('/hr/dashboard', (req, res) => {
  const pendingLeaves = getEnrichedLeaves().filter(l => l.status === 'P');
  const recentPayrolls = getEnrichedPayrolls().slice(0, 5);

  res.render('hr/dashboard', {
    employeesCount: employees.length,
    departmentsCount: departments.length,
    pendingLeaves,
    recentPayrolls
  });
});

app.get('/hr/employees', (req, res) => {
  res.render('hr/employees', { employees: getEnrichedEmployees() });
});

app.get('/hr/employees/add', (req, res) => {
  res.render('hr/employee_form', { employee: null, departments });
});

app.post('/hr/employees/add', (req, res) => {
  const {
    fullName, email, username, password, employeeId,
    jobTitle, departmentId, salary, hireDate, contractEnd,
    contact, dob, gender, emergencyContactName, emergencyContactPhone, address
  } = req.body;

  const newUserId = getNextId();
  users.push({
    id: newUserId,
    username: username || email.split('@')[0],
    password: password || 'password123',
    email,
    role: 'Employee',
    fullName
  });

  employees.push({
    id: getNextId(),
    userId: newUserId,
    employeeId: employeeId || `EMP-${employees.length + 101}`,
    fullName,
    email,
    contact: contact || '',
    dob: dob || '',
    gender: gender || 'M',
    address: address || '',
    jobTitle: jobTitle || 'Staff Member',
    departmentId: Number(departmentId) || 1,
    hireDate: hireDate || new Date().toISOString().split('T')[0],
    contractStart: hireDate || new Date().toISOString().split('T')[0],
    contractEnd: contractEnd || '',
    isActiveEmployee: true,
    salary: Number(salary) || 50000,
    annualLeaveBalance: 21,
    sickLeaveBalance: 10,
    emergencyContactName: emergencyContactName || '',
    emergencyContactPhone: emergencyContactPhone || ''
  });

  req.session.successMessage = `Employee ${fullName} created successfully!`;
  res.redirect('/hr/employees');
});

app.get('/hr/employees/:id/edit', (req, res) => {
  const id = Number(req.params.id);
  const emp = employees.find(e => e.id === id);
  if (!emp) {
    req.session.errorMessage = 'Employee not found';
    return res.redirect('/hr/employees');
  }
  res.render('hr/employee_form', { employee: emp, departments });
});

app.post('/hr/employees/:id/edit', (req, res) => {
  const id = Number(req.params.id);
  const emp = employees.find(e => e.id === id);
  if (!emp) {
    req.session.errorMessage = 'Employee not found';
    return res.redirect('/hr/employees');
  }

  const {
    fullName, email, employeeId, jobTitle, departmentId,
    salary, hireDate, contractEnd, contact, dob, gender,
    emergencyContactName, emergencyContactPhone, address
  } = req.body;

  emp.fullName = fullName;
  emp.email = email;
  emp.employeeId = employeeId;
  emp.jobTitle = jobTitle;
  emp.departmentId = Number(departmentId);
  emp.salary = Number(salary);
  emp.hireDate = hireDate;
  emp.contractEnd = contractEnd;
  emp.contact = contact;
  emp.dob = dob;
  emp.gender = gender;
  emp.emergencyContactName = emergencyContactName;
  emp.emergencyContactPhone = emergencyContactPhone;
  emp.address = address;

  req.session.successMessage = `Employee ${fullName} updated successfully!`;
  res.redirect('/hr/employees');
});

app.post('/hr/employees/:id/delete', (req, res) => {
  const id = Number(req.params.id);
  const index = employees.findIndex(e => e.id === id);
  if (index !== -1) {
    const deleted = employees.splice(index, 1)[0];
    req.session.successMessage = `Employee ${deleted.fullName} deleted successfully.`;
  }
  res.redirect('/hr/employees');
});

// Departments
app.get('/hr/departments', (req, res) => {
  const deptList = departments.map(d => ({
    ...d,
    employeeCount: employees.filter(e => Number(e.departmentId) === Number(d.id)).length
  }));
  res.render('hr/departments', { departments: deptList });
});

app.get('/hr/departments/add', (req, res) => {
  res.render('hr/department_form', { department: null });
});

app.post('/hr/departments/add', (req, res) => {
  const { name, description } = req.body;
  departments.push({
    id: getNextId(),
    name,
    description
  });
  req.session.successMessage = `Department ${name} added!`;
  res.redirect('/hr/departments');
});

app.get('/hr/departments/:id/edit', (req, res) => {
  const id = Number(req.params.id);
  const dept = departments.find(d => d.id === id);
  if (!dept) return res.redirect('/hr/departments');
  res.render('hr/department_form', { department: dept });
});

app.post('/hr/departments/:id/edit', (req, res) => {
  const id = Number(req.params.id);
  const dept = departments.find(d => d.id === id);
  if (dept) {
    dept.name = req.body.name;
    dept.description = req.body.description;
    req.session.successMessage = `Department updated!`;
  }
  res.redirect('/hr/departments');
});

app.post('/hr/departments/:id/delete', (req, res) => {
  const id = Number(req.params.id);
  const idx = departments.findIndex(d => d.id === id);
  if (idx !== -1) {
    departments.splice(idx, 1);
    req.session.successMessage = `Department deleted.`;
  }
  res.redirect('/hr/departments');
});

// Leaves Review
app.get('/hr/leaves', (req, res) => {
  res.render('hr/leaves', { leaves: getEnrichedLeaves() });
});

app.post('/leaves/process/:id/:action', (req, res) => {
  const id = Number(req.params.id);
  const action = req.params.action;
  const leave = leaveRequests.find(l => l.id === id);
  if (leave) {
    leave.status = action === 'approve' ? 'A' : 'R';
    if (action === 'approve') {
      const emp = employees.find(e => e.id === leave.employeeId);
      if (emp && emp.annualLeaveBalance > 0) {
        emp.annualLeaveBalance = Math.max(0, emp.annualLeaveBalance - 2);
      }
    }
    req.session.successMessage = `Leave request marked as ${action === 'approve' ? 'Approved' : 'Rejected'}.`;
  }
  res.redirect(req.headers.referer || '/hr/leaves');
});

// Payroll Management
app.get('/hr/payrolls', (req, res) => {
  res.render('hr/payrolls', { payrolls: getEnrichedPayrolls() });
});

app.get('/hr/payrolls/add', (req, res) => {
  const today = new Date();
  const firstDay = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
  const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().split('T')[0];
  res.render('hr/payroll_form', {
    employees,
    defaultStart: firstDay,
    defaultEnd: lastDay
  });
});

app.post('/hr/payrolls/add', (req, res) => {
  const { employeeId, periodStart, periodEnd, basicSalary, allowances } = req.body;
  const breakdown = computePayrollBreakdown(basicSalary, allowances);

  payrolls.unshift({
    id: getNextId(),
    employeeId: Number(employeeId),
    periodStart,
    periodEnd,
    ...breakdown,
    status: 'Pending'
  });

  req.session.successMessage = 'Payroll generated and calculated with Kenya statutory tax deductions!';
  res.redirect('/hr/payrolls');
});

app.post('/payroll/mark-paid/:id', (req, res) => {
  const id = Number(req.params.id);
  const p = payrolls.find(pay => pay.id === id);
  if (p) {
    p.status = 'Paid';
    req.session.successMessage = 'Payroll marked as Paid.';
  }
  res.redirect(req.headers.referer || '/hr/payrolls');
});

app.post('/hr/payrolls/delete/:id', (req, res) => {
  const id = Number(req.params.id);
  const idx = payrolls.findIndex(p => p.id === id);
  if (idx !== -1) {
    payrolls.splice(idx, 1);
    req.session.successMessage = 'Payroll record removed.';
  }
  res.redirect('/hr/payrolls');
});

// Reports & Analytics
app.get(['/hr/reports', '/hr/reports/employees', '/employee_report'], (req, res) => {
  const pendingLeavesCount = leaveRequests.filter(l => l.status === 'P').length;
  const monthlyPayrollTotal = payrolls.reduce((sum, p) => sum + (Number(p.grossSalary) || 0), 0);
  const activeContractsCount = employees.filter(e => e.isActiveEmployee).length;

  res.render('hr/reports', {
    employees: getEnrichedEmployees(),
    payrolls: getEnrichedPayrolls(),
    attendances: getEnrichedAttendances(),
    leaves: getEnrichedLeaves(),
    pendingLeavesCount,
    monthlyPayrollTotal,
    activeContractsCount
  });
});

// CSV Exports
app.get('/hr/reports/employees/export', (req, res) => {
  const emps = getEnrichedEmployees();
  let csv = 'ID,Full Name,Email,Department,Job Title,Salary,Hire Date,Status\n';
  emps.forEach(e => {
    csv += `"${e.employeeId}","${e.fullName}","${e.email}","${e.departmentName}","${e.jobTitle}",${e.salary},"${e.hireDate}","${e.isActiveEmployee ? 'Active' : 'Inactive'}"\n`;
  });
  res.setHeader('Content-Type', 'text/csv');
  res.setHeader('Content-Disposition', 'attachment; filename="employees_report.csv"');
  res.send(csv);
});

app.get('/hr/reports/payroll/export', (req, res) => {
  const pays = getEnrichedPayrolls();
  let csv = 'Employee,Period Start,Period End,Basic Salary,Allowances,Gross Salary,NSSF,SHA,PAYE,Net Pay,Status\n';
  pays.forEach(p => {
    csv += `"${p.employeeName}","${p.periodStart}","${p.periodEnd}",${p.basicSalary},${p.allowances},${p.grossSalary},${p.nssf},${p.sha},${p.paye},${p.netPay},"${p.status}"\n`;
  });
  res.setHeader('Content-Type', 'text/csv');
  res.setHeader('Content-Disposition', 'attachment; filename="payroll_report.csv"');
  res.send(csv);
});

app.get('/hr/reports/attendance/export', (req, res) => {
  const atts = getEnrichedAttendances();
  let csv = 'Date,Employee,Check In,Check Out,Status\n';
  atts.forEach(a => {
    csv += `"${a.date}","${a.employeeName}","${a.checkIn}","${a.checkOut}","${a.status}"\n`;
  });
  res.setHeader('Content-Type', 'text/csv');
  res.setHeader('Content-Disposition', 'attachment; filename="attendance_report.csv"');
  res.send(csv);
});

app.get('/hr/reports/leave/export', (req, res) => {
  const lvs = getEnrichedLeaves();
  let csv = 'Employee,Leave Type,Start Date,End Date,Days,Reason,Status\n';
  lvs.forEach(l => {
    csv += `"${l.employeeName}","${l.leaveType}","${l.startDate}","${l.endDate}",${l.days},"${l.reason}","${l.status}"\n`;
  });
  res.setHeader('Content-Type', 'text/csv');
  res.setHeader('Content-Disposition', 'attachment; filename="leave_report.csv"');
  res.send(csv);
});

// Insights & Analytics
app.get('/hr/insights', (req, res) => {
  const employeesCount = employees.length;
  const activeEmployeesCount = employees.filter(e => e.isActiveEmployee).length;
  const departmentsCount = departments.length;

  const totalAtt = attendances.length;
  const presentAtt = attendances.filter(a => a.status === 'Present').length;
  const avgAttendance = totalAtt > 0 ? Math.round((presentAtt / totalAtt) * 100) : 100;

  // Department counts
  const deptCounts = {};
  departments.forEach(d => {
    deptCounts[d.name] = employees.filter(e => Number(e.departmentId) === Number(d.id)).length;
  });

  // Attendance breakdown
  const attendanceBreakdown = {
    Present: attendances.filter(a => a.status === 'Present').length,
    Absent: attendances.filter(a => a.status === 'Absent').length,
    Leave: attendances.filter(a => a.status === 'Leave').length
  };

  res.render('hr/insights', {
    employeesCount,
    activeEmployeesCount,
    departmentsCount,
    avgAttendance,
    deptCounts,
    attendanceBreakdown
  });
});

// Catch-all unmigrated routes stub
app.all('/api/*', (req, res) => {
  res.status(501).json({ error: 'Endpoint not yet migrated' });
});

app.use((req, res) => {
  res.status(404).render('login', {
    isHr: false,
    errorMessage: 'Page not found. Redirected to portal home.'
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Server listening at http://0.0.0.0:${PORT}`);
});
