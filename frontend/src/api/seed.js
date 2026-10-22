// Mock database seed data for the Cyber Panchayat platform
// Contains all initial data: users, departments, officers, requests, facilities, bookings, etc.
// Mirrors backend seed data structure from backend/__init__.py
// Images are served at /uploads/x (backend uses /api/uploads/x)
// Reference date for all timestamps: 2026-07-01 (used to generate relative dates)

// Helper function to generate timestamps relative to reference date (2026-07-01)
// Used for creating realistic data that appears to have historical progression
function daysAgo(n, hour = 10, min = 0) {
  const d = new Date("2026-07-01T00:00:00Z")
  d.setDate(d.getDate() - n)
  d.setHours(hour, min, 0, 0)
  return d.toISOString()
}

// User accounts: 1 admin, 5 staff (one per department), 5 citizens
// Password hashes are not stored; mock API accepts any password and uses email to look up users
export const USERS = {
  "admin@civic.gov": {
    id: 1, name: "Preetam Nagar Admin", email: "admin@civic.gov",
    role: "admin", phone: "9000000001", ward: "Central", department: "Administration",
    is_active: true, created_at: daysAgo(60),
  },
  "rajesh@civic.gov": {
    id: 2, name: "Rajesh Kumar", email: "rajesh@civic.gov",
    role: "staff", phone: "9876543210", department: "Road Maintenance",
    is_active: true, created_at: daysAgo(60),
  },
  "priya@civic.gov": {
    id: 3, name: "Priya Singh", email: "priya@civic.gov",
    role: "staff", phone: "9876543212", department: "Electricity Department",
    is_active: true, created_at: daysAgo(60),
  },
  "imran@civic.gov": {
    id: 4, name: "Imran Khan", email: "imran@civic.gov",
    role: "staff", phone: "9876543213", department: "Water Supply Department",
    is_active: true, created_at: daysAgo(60),
  },
  "sandeep@civic.gov": {
    id: 5, name: "Sandeep Yadav", email: "sandeep@civic.gov",
    role: "staff", phone: "9876543214", department: "Sanitation Department",
    is_active: true, created_at: daysAgo(60),
  },
  "kavita@civic.gov": {
    id: 6, name: "Kavita Sharma", email: "kavita@civic.gov",
    role: "staff", phone: "9876543215", department: "Parks & Public Spaces",
    is_active: true, created_at: daysAgo(60),
  },
  "amit@gmail.com": {
    id: 7, name: "Amit Sharma", email: "amit@gmail.com",
    role: "citizen", phone: "9111111101", ward: "Ward-1",
    is_active: true, created_at: daysAgo(45),
  },
  "neha@gmail.com": {
    id: 8, name: "Neha Verma", email: "neha@gmail.com",
    role: "citizen", phone: "9111111102", ward: "Ward-2",
    is_active: true, created_at: daysAgo(40),
  },
  "ravi.g@gmail.com": {
    id: 9, name: "Ravi Gupta", email: "ravi.g@gmail.com",
    role: "citizen", phone: "9111111103", ward: "Ward-3",
    is_active: true, created_at: daysAgo(35),
  },
  "sunita@gmail.com": {
    id: 10, name: "Sunita Mehta", email: "sunita@gmail.com",
    role: "citizen", phone: "9111111104", ward: "Ward-2",
    is_active: true, created_at: daysAgo(30),
  },
  "arjun@gmail.com": {
    id: 11, name: "Arjun Singh", email: "arjun@gmail.com",
    role: "citizen", phone: "9111111105", ward: "Ward-3",
    is_active: true, created_at: daysAgo(25),
  },
}

// Civic departments responsible for handling different categories of complaints
// Each department is led by an officer with contact information
// Used to route complaints to the appropriate department and assign to officers
export const DEPARTMENTS = [
  { id: 1, dept_id: "DPT01", name: "Road Maintenance",        description: "Handles road repairs, potholes, and street maintenance",                       officer_incharge_id: 2, officer_name: "Rajesh Kumar",  officer_phone: "9876543210", created_at: daysAgo(60) },
  { id: 2, dept_id: "DPT02", name: "Electricity Department",  description: "Manages streetlights, electrical poles, and power supply issues",              officer_incharge_id: 3, officer_name: "Priya Singh",   officer_phone: "9876543212", created_at: daysAgo(60) },
  { id: 3, dept_id: "DPT03", name: "Water Supply Department", description: "Handles water supply, pipeline leakage, and drainage issues",                  officer_incharge_id: 4, officer_name: "Imran Khan",    officer_phone: "9876543213", created_at: daysAgo(60) },
  { id: 4, dept_id: "DPT04", name: "Sanitation Department",   description: "Manages garbage collection, sewage, and cleanliness",                          officer_incharge_id: 5, officer_name: "Sandeep Yadav", officer_phone: "9876543214", created_at: daysAgo(60) },
  { id: 5, dept_id: "DPT05", name: "Parks & Public Spaces",   description: "Maintains parks, public gardens, and recreational areas",                      officer_incharge_id: 6, officer_name: "Kavita Sharma", officer_phone: "9876543215", created_at: daysAgo(60) },
]

// Staff officers who handle complaint assignments
// One officer per department, can have multiple complaints assigned
// Tracked by assigned_count and is_active status
export const OFFICERS = [
  { id: 2,  officer_id: "OFF02", name: "Rajesh Kumar",  email: "rajesh@civic.gov",  department: "Road Maintenance",        phone: "9876543210", is_active: true, assigned_count: 2 },
  { id: 3,  officer_id: "OFF03", name: "Priya Singh",   email: "priya@civic.gov",   department: "Electricity Department",  phone: "9876543212", is_active: true, assigned_count: 2 },
  { id: 4,  officer_id: "OFF04", name: "Imran Khan",    email: "imran@civic.gov",   department: "Water Supply Department", phone: "9876543213", is_active: true, assigned_count: 2 },
  { id: 5,  officer_id: "OFF05", name: "Sandeep Yadav", email: "sandeep@civic.gov", department: "Sanitation Department",   phone: "9876543214", is_active: true, assigned_count: 1 },
  { id: 6,  officer_id: "OFF06", name: "Kavita Sharma", email: "kavita@civic.gov",  department: "Parks & Public Spaces",   phone: "9876543215", is_active: true, assigned_count: 1 },
]

// Citizen complaints/service requests (8 curated examples showing various statuses and workflows)
// Status flow: pending → assigned → in_progress → resolved → closed (or rejected)
// Each request shows realistic progression through the system with timestamps
// Evidence photos are distinct per complaint (not reused)
// Assignment object tracks who handled each complaint and when it was completed
export const REQUESTS = [
  {
    id: 1, cmp_id: "CMP0001",
    citizen_id: 7, citizen_name: "Amit Sharma", citizen_email: "amit@gmail.com", citizen_phone: "9111111101",
    category: "road", department: "Road Maintenance",
    title: "Large potholes on MG Road causing accidents",
    description: "There are multiple large potholes near the main junction on MG Road. Three vehicles have been damaged this week. Requires urgent repair.",
    address: "MG Road Junction, Preetam Nagar (Ward-1)", ward: "Ward-1",
    priority: "urgent", status: "in_progress",
    admin_notes: "Assigned to road repair team. Work started.",
    image_urls: ["/uploads/pothole.jpg", "/uploads/footpath.jpg"], evidence_urls: [],
    pending_funds: false, hold_reason: null,
    upvotes_count: 0, upvoted_by_me: false,
    assignment: { id: 1, request_id: 1, staff_id: 2, staff_name: "Rajesh Kumar", staff_department: "Road Maintenance", assigned_by: 1, notes: "Assigned to road repair team. Work started.", assigned_at: daysAgo(12, 12), completed_at: null },
    created_at: daysAgo(12), updated_at: daysAgo(12, 12), resolved_at: null, in_progress_at: daysAgo(12, 14),
    in_progress_notes: "Repair team is on site patching the potholes.", resolved_notes: null,
  },
  {
    id: 2, cmp_id: "CMP0002",
    citizen_id: 7, citizen_name: "Amit Sharma", citizen_email: "amit@gmail.com", citizen_phone: "9111111101",
    category: "electricity", department: "Electricity Department",
    title: "Street light not working near Block A park",
    description: "The street light near the Block A park has not been working for 3 days. It is very unsafe to walk at night. Children play in this area.",
    address: "Block A Park Gate, Preetam Nagar (Ward-1)", ward: "Ward-1",
    priority: "high", status: "in_progress",
    admin_notes: "Maintenance team assigned. Bulb replacement in progress.",
    image_urls: ["/uploads/streetlight.jpg", "/uploads/electric-pole.jpg"], evidence_urls: [],
    pending_funds: false, hold_reason: null,
    upvotes_count: 0, upvoted_by_me: false,
    assignment: { id: 2, request_id: 2, staff_id: 3, staff_name: "Priya Singh", staff_department: "Electricity Department", assigned_by: 1, notes: "Maintenance team assigned. Bulb replacement in progress.", assigned_at: daysAgo(3, 12), completed_at: null },
    created_at: daysAgo(3), updated_at: daysAgo(3, 12), resolved_at: null, in_progress_at: daysAgo(3, 15),
    in_progress_notes: "New bulb ordered, replacement scheduled for today.", resolved_notes: null,
  },
  {
    id: 3, cmp_id: "CMP0003",
    citizen_id: 9, citizen_name: "Ravi Gupta", citizen_email: "ravi.g@gmail.com", citizen_phone: "9111111103",
    category: "road", department: "Road Maintenance",
    title: "Road cave-in at Nehru Chowk",
    description: "A section of road near Nehru Chowk has caved in after recent rains. The hole is about 3 feet deep and very dangerous for traffic.",
    address: "Nehru Chowk, Preetam Nagar (Ward-3)", ward: "Ward-3",
    priority: "urgent", status: "resolved",
    admin_notes: "Road fully repaired and patched.",
    image_urls: ["/uploads/road-damage.jpg"], evidence_urls: ["/uploads/road-repaired.jpg"],
    pending_funds: false, hold_reason: null,
    upvotes_count: 0, upvoted_by_me: false,
    assignment: { id: 3, request_id: 3, staff_id: 2, staff_name: "Rajesh Kumar", staff_department: "Road Maintenance", assigned_by: 1, notes: "Road fully repaired and patched.", assigned_at: daysAgo(20, 12), completed_at: daysAgo(15) },
    created_at: daysAgo(20), updated_at: daysAgo(15), resolved_at: daysAgo(15), in_progress_at: daysAgo(19),
    in_progress_notes: "Road crew started patching the cave-in.", resolved_notes: "Road fully repaired and patched. Reopened for traffic.",
  },
  {
    id: 4, cmp_id: "CMP0004",
    citizen_id: 9, citizen_name: "Ravi Gupta", citizen_email: "ravi.g@gmail.com", citizen_phone: "9111111103",
    category: "electricity", department: "Electricity Department",
    title: "Power outage affecting entire block",
    description: "Our entire residential block has had no electricity for 2 days. The transformer may have blown. Please send a technician.",
    address: "Civil Lines Road, Preetam Nagar (Ward-3)", ward: "Ward-3",
    priority: "urgent", status: "closed",
    admin_notes: "Transformer replaced. Power restored.",
    image_urls: [], evidence_urls: ["/uploads/dark-street.jpg"],
    rating: 4, feedback: "Power was restored quickly once the team arrived. Good work.",
    pending_funds: false, hold_reason: null,
    upvotes_count: 0, upvoted_by_me: false,
    assignment: { id: 4, request_id: 4, staff_id: 3, staff_name: "Priya Singh", staff_department: "Electricity Department", assigned_by: 1, notes: "Transformer replaced. Power restored.", assigned_at: daysAgo(15, 12), completed_at: daysAgo(13) },
    created_at: daysAgo(15), updated_at: daysAgo(13), resolved_at: daysAgo(13), in_progress_at: daysAgo(14),
    in_progress_notes: "Technician dispatched to inspect the transformer.", resolved_notes: "Transformer replaced. Power restored to the block.",
  },
  {
    id: 5, cmp_id: "CMP0005",
    citizen_id: 9, citizen_name: "Ravi Gupta", citizen_email: "ravi.g@gmail.com", citizen_phone: "9111111103",
    category: "waste", department: "Sanitation Department",
    title: "Garbage not collected for a week",
    description: "Garbage has not been collected from our area for over a week. The garbage is piling up and causing health hazards. Rats and flies are increasing.",
    address: "Civil Lines Road, Preetam Nagar (Ward-3)", ward: "Ward-3",
    priority: "high", status: "pending",
    admin_notes: null,
    image_urls: ["/uploads/garbage.jpg", "/uploads/garbage-bins.jpg"], evidence_urls: [],
    pending_funds: false, hold_reason: null,
    upvotes_count: 0, upvoted_by_me: false, assignment: null,
    created_at: daysAgo(7), updated_at: daysAgo(7), resolved_at: null, in_progress_at: null,
    in_progress_notes: null, resolved_notes: null,
  },
  {
    id: 6, cmp_id: "CMP0006",
    citizen_id: 8, citizen_name: "Neha Verma", citizen_email: "neha@gmail.com", citizen_phone: "9111111102",
    category: "water", department: "Water Supply Department",
    title: "Clogged drainage causing flooding",
    description: "The main drainage channel near our colony is completely blocked. Rainwater is flooding homes. Please clear immediately.",
    address: "Colony Gate, Preetam Nagar (Ward-2)", ward: "Ward-2",
    priority: "high", status: "resolved",
    admin_notes: "Drainage cleared. Good for monsoon season.",
    image_urls: ["/uploads/manhole.jpg"], evidence_urls: ["/uploads/garbage-collected.jpg"],
    pending_funds: false, hold_reason: null,
    upvotes_count: 0, upvoted_by_me: false,
    assignment: { id: 6, request_id: 6, staff_id: 4, staff_name: "Imran Khan", staff_department: "Water Supply Department", assigned_by: 1, notes: "Drainage cleared. Good for monsoon season.", assigned_at: daysAgo(18, 12), completed_at: daysAgo(16) },
    created_at: daysAgo(18), updated_at: daysAgo(16), resolved_at: daysAgo(16), in_progress_at: daysAgo(17),
    in_progress_notes: "Drain clearing crew dispatched.", resolved_notes: "Drainage cleared. Flooding risk resolved ahead of monsoon.",
  },
  {
    id: 7, cmp_id: "CMP0007",
    citizen_id: 7, citizen_name: "Amit Sharma", citizen_email: "amit@gmail.com", citizen_phone: "9111111101",
    category: "parks", department: "Parks & Public Spaces",
    title: "Broken playground equipment in Block A park",
    description: "The slides and swings in the Block A park are broken and rusted. Children have been injured. Please repair or replace the equipment.",
    address: "Block A Park, Preetam Nagar (Ward-1)", ward: "Ward-1",
    priority: "medium", status: "closed",
    admin_notes: "Old equipment removed and new playset installed.",
    image_urls: ["/uploads/playground.jpg"], evidence_urls: ["/uploads/playground-repaired.jpg"],
    rating: 5, feedback: "Great work — the new playset is wonderful, kids love it!",
    pending_funds: false, hold_reason: null,
    upvotes_count: 0, upvoted_by_me: false,
    assignment: { id: 7, request_id: 7, staff_id: 6, staff_name: "Kavita Sharma", staff_department: "Parks & Public Spaces", assigned_by: 1, notes: "Old equipment removed and new playset installed.", assigned_at: daysAgo(10, 12), completed_at: daysAgo(4) },
    created_at: daysAgo(10), updated_at: daysAgo(4), resolved_at: daysAgo(4), in_progress_at: daysAgo(8),
    in_progress_notes: "Old equipment removal started.", resolved_notes: "New playset installed and safety-checked.",
  },
  {
    id: 8, cmp_id: "CMP0008",
    citizen_id: 11, citizen_name: "Arjun Singh", citizen_email: "arjun@gmail.com", citizen_phone: "9111111105",
    category: "sanitation", department: "Sanitation Department",
    title: "Blocked sewage drain overflowing in Nehru Colony",
    description: "The open sewage drain in Nehru Colony is completely blocked with rags and plastic waste. Dirty water is stagnating and overflowing near homes, and the foul smell is unbearable. Needs urgent cleaning.",
    address: "Nehru Colony, Preetam Nagar (Ward-3)", ward: "Ward-3",
    priority: "high", status: "assigned",
    admin_notes: "Sanitation crew scheduled to clear the blocked drain this week.",
    image_urls: ["/uploads/sewage-drain.jpg"], evidence_urls: [],
    pending_funds: false, hold_reason: null,
    upvotes_count: 0, upvoted_by_me: false,
    assignment: { id: 8, request_id: 8, staff_id: 5, staff_name: "Sandeep Yadav", staff_department: "Sanitation Department", assigned_by: 1, notes: "Sanitation crew scheduled to clear the blocked drain this week.", assigned_at: daysAgo(2, 12), completed_at: null },
    created_at: daysAgo(2), updated_at: daysAgo(2, 12), resolved_at: null, in_progress_at: null,
    in_progress_notes: null, resolved_notes: null,
  },
]

// Civic facilities available for public booking (community halls, sports grounds, etc.)
// Each facility has capacity limits, hourly fees, amenities, and availability tracking
export const FACILITIES = [
  { id: 1, name: "City Community Hall",             facility_type: "Community Hall",   address: "1, Civic Center, Preetam Nagar (Central)",                         ward: "Central", capacity: 200, fee_per_hour: 500, description: "Large community hall for events",   amenities: "AC, Projector, Stage, Parking, Restrooms",    image_urls: ["/uploads/community-hall.jpg"],  is_active: true },
  { id: 2, name: "Ward-1 Sports Ground",            facility_type: "Sports Ground",    address: "Stadium Road, Preetam Nagar (Ward-1)",                              ward: "Ward-1", capacity: 100, fee_per_hour: 100, description: "Open ground for sports",           amenities: "Changing Rooms, Floodlights, Drinking Water",  image_urls: ["/uploads/sports-ground.jpg"],   is_active: true },
  { id: 3, name: "Public Library Conference Room",  facility_type: "Conference Room",  address: "Library Building, Civil Lines Road, Preetam Nagar (Ward-3)",        ward: "Ward-3", capacity: 50,  fee_per_hour: 200, description: "Quiet conference room",            amenities: "AC, WiFi, Whiteboard, Projector",              image_urls: ["/uploads/library-room.jpg"],    is_active: true },
  { id: 4, name: "Ward-2 Recreation Park",          facility_type: "Park",             address: "Colony Gate, Preetam Nagar (Ward-2)",                               ward: "Ward-2", capacity: 300, fee_per_hour: 50,  description: "Open park for community events",   amenities: "Open Space, Seating, Parking",                 image_urls: ["/uploads/recreation-park.jpg"], is_active: true },
]

// Facility bookings with payment tracking
// Each booking may have associated payment object if facility has fees
// Status flow: pending → confirmed/cancelled → completed
// Attendee count is validated against facility capacity at booking time
export const BOOKINGS = [
  { id: 1, facility_id: 1, facility_name: "City Community Hall",            facility_type: "Community Hall",  citizen_id: 7,  citizen_name: "Amit Sharma",  booking_date: "2026-07-10", start_time: "10:00", end_time: "13:00", purpose: "Ward-1 Community Meeting",  attendees: 80,  status: "confirmed", fee: 1500, admin_notes: "Confirmed. Please arrive 15 mins early.", payment: { id: 1, booking_id: 1, citizen_id: 7,  citizen_name: "Amit Sharma",  amount: 1500, status: "paid",    method: "upi",        transaction_ref: "TXN4A9F2E1B8C", created_at: daysAgo(10), paid_at: daysAgo(10) }, created_at: daysAgo(11) },
  { id: 2, facility_id: 2, facility_name: "Ward-1 Sports Ground",           facility_type: "Sports Ground",   citizen_id: 8,  citizen_name: "Neha Verma",   booking_date: "2026-07-15", start_time: "07:00", end_time: "09:00", purpose: "Youth Cricket Practice",    attendees: 22,  status: "pending",   fee: 200,  admin_notes: null, payment: { id: 2, booking_id: 2, citizen_id: 8,  citizen_name: "Neha Verma",   amount: 200,  status: "pending", method: "online",     transaction_ref: null,            created_at: daysAgo(4),  paid_at: null      }, created_at: daysAgo(4)  },
  { id: 3, facility_id: 3, facility_name: "Public Library Conference Room", facility_type: "Conference Room", citizen_id: 9,  citizen_name: "Ravi Gupta",   booking_date: "2026-07-20", start_time: "14:00", end_time: "16:00", purpose: "NGO Workshop",              attendees: 30,  status: "confirmed", fee: 400,  admin_notes: "Please bring your ID proof.", payment: { id: 3, booking_id: 3, citizen_id: 9,  citizen_name: "Ravi Gupta",   amount: 400,  status: "paid",    method: "netbanking", transaction_ref: "TXNB2D8F3A1C7", created_at: daysAgo(5),  paid_at: daysAgo(5)  }, created_at: daysAgo(6)  },
  { id: 4, facility_id: 4, facility_name: "Ward-2 Recreation Park",         facility_type: "Park",            citizen_id: 10, citizen_name: "Sunita Mehta", booking_date: "2026-07-25", start_time: "09:00", end_time: "11:00", purpose: "Yoga & Fitness Camp",       attendees: 50,  status: "pending",   fee: 100,  admin_notes: null, payment: { id: 5, booking_id: 4, citizen_id: 10, citizen_name: "Sunita Mehta", amount: 100,  status: "pending", method: "online",     transaction_ref: null,            created_at: daysAgo(3),  paid_at: null      }, created_at: daysAgo(3) },
  { id: 5, facility_id: 1, facility_name: "City Community Hall",            facility_type: "Community Hall",  citizen_id: 11, citizen_name: "Arjun Singh",  booking_date: "2026-06-05", start_time: "18:00", end_time: "21:00", purpose: "Cultural Evening Event",    attendees: 150, status: "completed", fee: 1500, admin_notes: "Event completed successfully.", payment: { id: 4, booking_id: 5, citizen_id: 11, citizen_name: "Arjun Singh",  amount: 1500, status: "paid",    method: "card",       transaction_ref: "TXNC9E7D4B6A2", created_at: daysAgo(35), paid_at: daysAgo(35) }, created_at: daysAgo(36) },
  { id: 6, facility_id: 3, facility_name: "Public Library Conference Room", facility_type: "Conference Room", citizen_id: 7,  citizen_name: "Amit Sharma",  booking_date: "2026-07-05", start_time: "10:00", end_time: "12:00", purpose: "Ward Budget Review Meeting", attendees: 25,  status: "cancelled", cancelled_by: "admin", fee: 400,  admin_notes: null, payment: { id: 6, booking_id: 6, citizen_id: 7,  citizen_name: "Amit Sharma",  amount: 400,  status: "refunded", method: "upi",        transaction_ref: "TXN7F3C9A2E1D", created_at: daysAgo(8),  paid_at: daysAgo(8), refund_reason: "Facility unavailable due to unscheduled maintenance work." }, created_at: daysAgo(9) },
  { id: 7, facility_id: 1, facility_name: "City Community Hall",            facility_type: "Community Hall",  citizen_id: 8,  citizen_name: "Neha Verma",   booking_date: "2026-06-12", start_time: "17:00", end_time: "19:00", purpose: "Ward-2 Cultural Night",     attendees: 90,  status: "completed", fee: 1000, admin_notes: "Event completed successfully.", payment: { id: 7, booking_id: 7, citizen_id: 8,  citizen_name: "Neha Verma",   amount: 1000, status: "paid",    method: "upi",        transaction_ref: "TXND1A6E9B4F2", created_at: daysAgo(30), paid_at: daysAgo(30) }, created_at: daysAgo(31) },
  { id: 8, facility_id: 4, facility_name: "Ward-2 Recreation Park",         facility_type: "Park",            citizen_id: 10, citizen_name: "Sunita Mehta", booking_date: "2026-06-18", start_time: "08:00", end_time: "10:00", purpose: "Morning Walkathon",         attendees: 40,  status: "completed", fee: 100,  admin_notes: "Event completed successfully.", payment: { id: 8, booking_id: 8, citizen_id: 10, citizen_name: "Sunita Mehta", amount: 100,  status: "paid",    method: "online",     transaction_ref: "TXNE7C4F1A9D3", created_at: daysAgo(24), paid_at: daysAgo(24) }, created_at: daysAgo(25) },
]

export const PAYMENTS = BOOKINGS.filter(b => b.payment).map(b => b.payment)

// Facility ratings — one per (facility, citizen), given after a completed booking
export const FACILITY_RATINGS = [
  { id: 1, facility_id: 1, booking_id: 5, citizen_id: 11, citizen_name: "Arjun Singh", rating: 5, comment: "Beautiful hall, well-maintained and spacious — perfect for our cultural event.", created_at: daysAgo(34), updated_at: daysAgo(34) },
  { id: 2, facility_id: 1, booking_id: 7, citizen_id: 8,  citizen_name: "Neha Verma",  rating: 4, comment: "Great space for a large gathering, though parking filled up fast.", created_at: daysAgo(29), updated_at: daysAgo(29) },
  { id: 3, facility_id: 4, booking_id: 8, citizen_id: 10, citizen_name: "Sunita Mehta", rating: 3, comment: "Nice open park, but could use better lighting for early-morning events.", created_at: daysAgo(23), updated_at: daysAgo(23) },
]

// User notifications: complaint status updates, assignments, bookings,
// payments, and system alerts. Tracked per user_id with read/unread status,
// a severity (info/success/warning), and a category used for the
// Notifications Hub's filter tabs (complaints/bookings/payments).
// `archived` notifications are hidden from the panel but not deleted
// (see the Clear All endpoint in api/index.js).
export const NOTIFICATIONS = [
  { id: 1, user_id: 7, title: "Complaint Assigned",    message: "Your complaint CMP0001 (Large potholes on MG Road) has been assigned to Road Maintenance Department.", notif_type: "info",    category: "complaints", is_read: true,  archived: false, created_at: daysAgo(12, 12) },
  { id: 2, user_id: 7, title: "Complaint In Progress", message: "Work has started on your complaint CMP0001. Expected completion in 3-5 days.",                       notif_type: "info",    category: "complaints", is_read: true,  archived: false, created_at: daysAgo(11) },
  { id: 3, user_id: 9, title: "Complaint Resolved",    message: "Your complaint CMP0003 (Road cave-in at Nehru Chowk) has been resolved. Please verify and close.",  notif_type: "success", category: "complaints", is_read: false, archived: false, created_at: daysAgo(15) },
  { id: 4, user_id: 7, title: "Complaint In Progress", message: "Work has started on your complaint CMP0002 (Street light not working). Our crew is on site.",         notif_type: "info",    category: "complaints", is_read: false, archived: false, created_at: daysAgo(3, 12) },
  { id: 5, user_id: 2, title: "New Assignment",        message: "You have been assigned complaint CMP0001 - Large potholes on MG Road. Please take action.",          notif_type: "warning", category: "complaints", is_read: true,  archived: false, created_at: daysAgo(12, 12) },
  { id: 6, user_id: 1, title: "New Complaints",        message: "A few new complaints have been submitted in the last 24 hours. Please review and assign.",          notif_type: "info",    category: "complaints", is_read: false, archived: false, created_at: daysAgo(1) },
  { id: 7, user_id: 7, title: "Booking Confirmed",     message: "Your facility booking has been confirmed by the admin. You can now complete payment.",               notif_type: "success", category: "bookings",   is_read: false, archived: false, created_at: daysAgo(2) },
  { id: 8, user_id: 7, title: "Payment Successful",    message: "Your payment for the community hall booking was received. A receipt is available in My Bookings.",  notif_type: "success", category: "payments",   is_read: false, archived: false, created_at: daysAgo(1, 9) },
]

// Community posts and announcements (6 total: 3 citizen posts, 1 staff official
// post, 2 admin announcements)
// Citizens can post in the community feed with images and comments
// Only admin role can create announcements; they appear in dedicated announcements page
// Both support likes and threaded comments
//
// The staff post is load-bearing for the feed's "Posted by → Department"
// filter: staff posts are the only ones that carry an author_department the
// feed can filter on (admin announcements are served from their own page and
// never reach the feed), so without one every department option returns zero.
export const POSTS = [
  {
    id: 1, citizen_id: 7, author_name: "Amit Sharma", author_role: "citizen", author_department: null,
    title: null, category: "general", is_official: false,
    content: "Street light not working near Block A park since 3 days. Very unsafe for evening walkers. Please fix it urgently! @ElectricityDept",
    location: "Block A Park, Preetam Nagar (Ward-1)", ward: "Ward-1",
    image_urls: ["/uploads/electric-pole.jpg", "/uploads/streetlight.jpg"],
    likes_count: 3, comments_count: 2, liked_by_me: false,
    created_at: daysAgo(0, 8),
    comments_list: [
      { id: 1, post_id: 1, user_id: 8, author_name: "Neha Verma",  author_role: "citizen", author_department: null,                     is_official: false, content: "Same problem in our area too! Three lights not working near the bus stop.",                                 created_at: daysAgo(0, 8, 30) },
      { id: 2, post_id: 1, user_id: 3, author_name: "Priya Singh", author_role: "staff",   author_department: "Electricity Department", is_official: true,  content: "We have received your complaint. Maintenance team has been assigned. Expected resolution within 48 hours.", created_at: daysAgo(0, 9) },
    ],
  },
  {
    id: 2, citizen_id: 8, author_name: "Neha Verma", author_role: "citizen", author_department: null,
    title: null, category: "general", is_official: false,
    content: "Garbage not collected from our area last 2 days. The smell is unbearable and we can see rats near the garbage dump. Please take action!",
    location: "Park Street, Preetam Nagar (Ward-2)", ward: "Ward-2",
    image_urls: ["/uploads/garbage.jpg", "/uploads/garbage-bins.jpg"],
    likes_count: 3, comments_count: 2, liked_by_me: false,
    created_at: daysAgo(0, 11),
    comments_list: [
      { id: 3, post_id: 2, user_id: 9, author_name: "Ravi Gupta",    author_role: "citizen", author_department: null,                   is_official: false, content: "Same issue in Ward-3! The garbage truck hasn't come for 5 days now.",                 created_at: daysAgo(0, 11, 30) },
      { id: 4, post_id: 2, user_id: 5, author_name: "Sandeep Yadav", author_role: "staff",   author_department: "Sanitation Department", is_official: true,  content: "Our team has been informed. Collection vehicle will reach your area today by 4 PM.", created_at: daysAgo(0, 12) },
    ],
  },
  {
    id: 6, citizen_id: 3, author_name: "Priya Singh", author_role: "staff", author_department: "Electricity Department",
    title: null, category: "electricity", is_official: true,
    content: "Streetlight repairs on the Block A stretch are scheduled for this Saturday, 6 AM to 12 PM. Eleven poles will be re-wired and four replaced. Expect brief outages on the connected line during the work.",
    location: "Block A, Preetam Nagar (Ward-1)", ward: "Ward-1",
    image_urls: [],
    likes_count: 4, comments_count: 1, liked_by_me: false,
    created_at: daysAgo(1, 10),
    comments_list: [
      { id: 5, post_id: 6, user_id: 7, author_name: "Amit Sharma", author_role: "citizen", author_department: null, is_official: false, content: "Finally! Thank you for the update and for sharing the timings in advance.", created_at: daysAgo(1, 13) },
    ],
  },
  {
    id: 3, citizen_id: 7, author_name: "Amit Sharma", author_role: "citizen", author_department: null,
    title: null, category: "general", is_official: false,
    content: "Successfully got the pothole repaired near my house in just 5 days after submitting the complaint. Thank you Road Maintenance team! Great initiative by the colony administration.",
    location: "Block A, Preetam Nagar (Ward-1)", ward: "Ward-1",
    image_urls: [],
    likes_count: 2, comments_count: 0, liked_by_me: false,
    created_at: daysAgo(3, 16),
    comments_list: [],
  },
  {
    id: 4, citizen_id: 1, author_name: "Preetam Nagar Admin", author_role: "admin", author_department: "Administration",
    title: "Water Supply Maintenance Notice", category: "announcement", topic: "water", is_official: true,
    content: "Dear Residents, water supply will be interrupted across Preetam Nagar on 18 May 2024 from 9 AM to 5 PM due to pipeline maintenance work. We apologize for the inconvenience. Emergency water tankers will be available.",
    location: "All of Preetam Nagar", ward: "Central",
    image_urls: [],
    likes_count: 0, comments_count: 0, liked_by_me: false,
    created_at: daysAgo(5, 9),
    comments_list: [],
  },
  {
    id: 5, citizen_id: 1, author_name: "Preetam Nagar Admin", author_role: "admin", author_department: "Administration",
    title: "Clean Colony Drive - Join Us!", category: "announcement", topic: "general", is_official: true,
    content: "Join us for a Clean Colony Drive on 25 May 2024 at Central Park, Preetam Nagar. Bring gloves and bags. Free refreshments for all participants. Let's make our colony cleaner together! Register at the civic center.",
    location: "Central Park, Preetam Nagar (Central)", ward: "Central",
    image_urls: [],
    likes_count: 0, comments_count: 0, liked_by_me: false,
    created_at: daysAgo(6, 10),
    comments_list: [],
  },
]

export const ANNOUNCEMENTS = POSTS.filter(p => p.category === "announcement")

// Cyber Panchayat Premium subscription data
// Monthly fee: Rs.100
// Citizens need active subscription to submit complaints and posts
// Only the initial subscription cycle is seeded; subsequent cycles are auto-generated by index.js
// Invoice generation happens automatically based on billing cycle dates
export const SUBSCRIPTION_FEE = 100

function addMonth(d) {
  const day = d.getDate()
  const next = new Date(d)
  next.setMonth(next.getMonth() + 1)
  if (next.getDate() !== day) next.setDate(0) // clamp overflow, e.g. Jan 31 -> Feb 28
  return next
}
function realDaysAgo(n) {
  const d = new Date()
  d.setDate(d.getDate() - n)
  d.setHours(10, 0, 0, 0)
  return d
}
function ymd(d) { return d.toISOString().split("T")[0] }

// Calculate subscription billing dates based on actual current date
// Shows realistic subscription lifecycle with different payment states.
// Simple pay-per-month: one payment buys exactly one month, no auto-renewal.
const amitStart = realDaysAgo(10)
const amitP1End = addMonth(amitStart)          // ~20 days from now — this month is still running
const raviStart = realDaysAgo(20)
const raviP1End = addMonth(raviStart)          // ~10 days from now — this month is still running
const arjunStart = realDaysAgo(50)
const arjunP1End = addMonth(arjunStart)        // ~20 days ago — that one paid month ran out, never resubscribed
const sunitaStart = realDaysAgo(70)            // original join date — stays fixed across every resubscribe
const sunitaP1End = addMonth(sunitaStart)      // ~40 days ago — her first month ran out
const sunitaRejoinedAt = realDaysAgo(15)       // resubscribed after a gap, starting a brand new month
const sunitaP2End = addMonth(sunitaRejoinedAt) // ~15 days from now — current month still running

// Subscription records showing three different states
// - Active, this month still running
// - Expired — the one paid month ran out, hasn't resubscribed yet
// - Expired once, then resubscribed — shows multi-cycle history (original
//   "Member since" date preserved, plus a "Rejoined" event) while currently active
export const SUBSCRIPTIONS = [
  { id: 1, citizen_id: 7, citizen_name: "Amit Sharma", citizen_email: "amit@gmail.com", status: "active", monthly_fee: SUBSCRIPTION_FEE, started_at: amitStart.toISOString(), next_billing_date: ymd(amitP1End), payment_method: "upi", history: [] },
  { id: 2, citizen_id: 9, citizen_name: "Ravi Gupta", citizen_email: "ravi.g@gmail.com", status: "active", monthly_fee: SUBSCRIPTION_FEE, started_at: raviStart.toISOString(), next_billing_date: ymd(raviP1End), payment_method: "card", history: [] },
  // Still marked "active" here on purpose — next_billing_date is already in
  // the past, so syncSubscriptionBilling finalizes the expiry (and logs it)
  // the next time anything reads it, same as it would live.
  { id: 3, citizen_id: 11, citizen_name: "Arjun Singh", citizen_email: "arjun@gmail.com", status: "active", monthly_fee: SUBSCRIPTION_FEE, started_at: arjunStart.toISOString(), next_billing_date: ymd(arjunP1End), payment_method: "online", history: [] },
  { id: 4, citizen_id: 10, citizen_name: "Sunita Mehta", citizen_email: "sunita@gmail.com", status: "active", monthly_fee: SUBSCRIPTION_FEE, started_at: sunitaStart.toISOString(), next_billing_date: ymd(sunitaP2End), payment_method: "netbanking",
    history: [ { type: "expired", at: sunitaP1End.toISOString() }, { type: "rejoined", at: sunitaRejoinedAt.toISOString() } ] },
]

// Individual subscription payment invoices — one per paid month.
// Tracks payment status, method, and transaction reference for billing history
export const SUBSCRIPTION_PAYMENTS = [
  { id: 1, subscription_id: 1, citizen_id: 7, citizen_name: "Amit Sharma", amount: SUBSCRIPTION_FEE, period_start: ymd(amitStart), period_end: ymd(amitP1End), status: "paid", method: "upi", transaction_ref: "SUB-TXN-C0BAE1AB3E", created_at: amitStart.toISOString(), paid_at: amitStart.toISOString() },
  { id: 2, subscription_id: 2, citizen_id: 9, citizen_name: "Ravi Gupta", amount: SUBSCRIPTION_FEE, period_start: ymd(raviStart), period_end: ymd(raviP1End), status: "paid", method: "card", transaction_ref: "SUB-TXN-F5ACC0598F", created_at: raviStart.toISOString(), paid_at: raviStart.toISOString() },
  { id: 3, subscription_id: 3, citizen_id: 11, citizen_name: "Arjun Singh", amount: SUBSCRIPTION_FEE, period_start: ymd(arjunStart), period_end: ymd(arjunP1End), status: "paid", method: "online", transaction_ref: "SUB-TXN-DF2D3C7947", created_at: arjunStart.toISOString(), paid_at: arjunStart.toISOString() },
  { id: 4, subscription_id: 4, citizen_id: 10, citizen_name: "Sunita Mehta", amount: SUBSCRIPTION_FEE, period_start: ymd(sunitaStart), period_end: ymd(sunitaP1End), status: "paid", method: "netbanking", transaction_ref: "SUB-TXN-A19E7C3B02", created_at: sunitaStart.toISOString(), paid_at: sunitaStart.toISOString() },
  { id: 5, subscription_id: 4, citizen_id: 10, citizen_name: "Sunita Mehta", amount: SUBSCRIPTION_FEE, period_start: ymd(sunitaRejoinedAt), period_end: ymd(sunitaP2End), status: "paid", method: "netbanking", transaction_ref: "SUB-TXN-B7E14F0A2C", created_at: sunitaRejoinedAt.toISOString(), paid_at: sunitaRejoinedAt.toISOString() },
]
