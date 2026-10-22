// Content tree for the guided help chatbot (ChatbotWidget.vue).
// Every fact here mirrors real app behavior, see api/seed.js and the
// citizen/staff/admin views. Nothing here is invented.
//
// Each node: { id, question, answer, related: [ids], action?: { label, path } }
// `related` is curated per-node (not strict parent/child), so the follow-up
// list shown after an answer can point across categories when relevant.

export const FAQ_NODES = {
  // Citizen: complaints
  "cit-file": {
    question: "How do I file a complaint?",
    answer: "Go to Submit Complaint and fill in the category, title, location, and description. AI can even suggest a category based on what you type, and you can scan a paper complaint too if you have one. You'll need an active Premium subscription to file.",
    related: ["cit-categories", "cit-ai-scan", "cit-ward", "cit-premium"],
    action: { label: "Submit a Complaint", path: "/submit" },
  },
  "cit-categories": {
    question: "What complaint categories are there?",
    answer: "Road, Water, Electricity, Sanitation, Waste, Parks & Public Spaces, Maintenance, General Complaint, and Other. Each one routes straight to the matching department.",
    related: ["cit-file", "cit-status"],
  },
  "cit-ai-scan": {
    question: "Can AI help me fill the complaint form?",
    answer: "Definitely. Click AI Suggest and it'll pick a category based on your description, or use Scan Paper to photograph a handwritten complaint and have the form filled in automatically.",
    related: ["cit-file", "cit-duplicate"],
    action: { label: "Submit a Complaint", path: "/submit" },
  },
  "cit-duplicate": {
    question: "What if someone already reported the same issue?",
    answer: "Good question. When you file a complaint, we check for similar ones already reported nearby. If we find one, you can just upvote it instead of creating a duplicate.",
    related: ["cit-file", "cit-all-complaints", "cit-status"],
    action: { label: "Submit a Complaint", path: "/submit" },
  },
  "cit-all-complaints": {
    question: "Can I see complaints reported by other people?",
    answer: "Yes. Open All Complaints from the sidebar, under Complaints. It shows every complaint in the city, and you can search by complaint ID, title or location, and filter by category and status. If you find one you are also facing, click Upvote instead of filing the same thing again. Upvoting works like a switch, so clicking it a second time removes your vote, and there is a My Upvoted filter to see the ones you backed. You cannot upvote your own complaint.",
    related: ["cit-duplicate", "cit-file", "cit-track-own"],
    action: { label: "Browse All Complaints", path: "/complaints/all" },
  },
  "cit-status": {
    question: "What do complaint statuses mean?",
    answer: "Pending means it's been submitted but not assigned yet. In Progress means an officer is actively working on it. Resolved means the issue has been fixed.",
    related: ["cit-track-own", "cit-rate", "cit-notif"],
    action: { label: "View My Requests", path: "/complaints" },
  },
  "cit-track-own": {
    question: "How do I check my complaint's progress?",
    answer: "Open My Requests from the sidebar to see every complaint you've filed and its current status, or click into one for full details. My Requests shows only your own complaints. To see everyone else's, use All Complaints.",
    related: ["cit-status", "cit-all-complaints", "cit-rate", "cit-notif"],
    action: { label: "View My Requests", path: "/complaints" },
  },
  "cit-rate": {
    question: "How do I rate the work done on my complaint?",
    answer: "When your complaint is marked Resolved, open it from My Requests. You will be asked if the work was done properly. Click Confirm and Close to give it a star rating out of 5 and write what you thought. If the problem is still not fixed, contact the department directly.",
    related: ["cit-status", "cit-track-own", "cit-support"],
    action: { label: "View My Requests", path: "/complaints" },
  },
  "cit-ward": {
    question: "What is my ward used for?",
    answer: "Your ward, like Ward-1, Ward-2, or Ward-3, gives local context to your complaints. You can set it from your profile.",
    related: ["cit-file"],
  },

  // Citizen: premium
  "cit-premium": {
    question: "What is Premium and why do I need it?",
    answer: "Cyber Panchayat Premium is ₹100 a month and it's what lets you file complaints. It renews automatically and you can cancel anytime. The Community Feed and tracking always stay free either way.",
    related: ["cit-premium-billing", "cit-premium-cancel", "cit-file"],
    action: { label: "View Premium", path: "/subscription" },
  },
  "cit-premium-billing": {
    question: "How does billing work?",
    answer: "It's auto-pay. Your saved payment method gets charged ₹100 automatically every month from your join date, and every paid cycle shows up in your Billing History with a downloadable invoice.",
    related: ["cit-premium-cancel", "cit-payments"],
    action: { label: "View Premium", path: "/subscription" },
  },
  "cit-premium-cancel": {
    question: "How do I cancel my subscription?",
    answer: "Open My Subscription and hit Cancel. You'll still keep filing access for a 3-day grace period just in case it was a mis-click, and after that it ends. You can resubscribe whenever you like.",
    related: ["cit-premium-billing", "cit-premium"],
    action: { label: "View Premium", path: "/subscription" },
  },

  // Citizen: community
  "cit-community": {
    question: "What can I do on the Community Feed?",
    answer: "You can post updates, comment, like posts, and share your location or photos. It's open to citizens, staff, and admins, and you don't need a subscription for it.",
    related: ["cit-announcements"],
    action: { label: "Open Community Feed", path: "/feed" },
  },
  "cit-announcements": {
    question: "Where do official announcements show up?",
    answer: "Check the Announcements page. Admins post official notices there, separate from the regular community feed.",
    related: ["cit-community"],
    action: { label: "View Announcements", path: "/announcements" },
  },

  // Citizen: facilities, payments, notifications
  "cit-facilities": {
    question: "Can I book a community facility?",
    answer: "Yes! Browse Facilities to see parks, community halls, sports grounds, and libraries, then book a slot. You can manage everything from My Bookings.",
    related: ["cit-bookings", "cit-payments"],
    action: { label: "Browse Facilities", path: "/facilities" },
  },
  "cit-bookings": {
    question: "Where do I see my facility bookings?",
    answer: "My Bookings shows every facility you've reserved along with its status.",
    related: ["cit-facilities", "cit-payments", "cit-rate-facility"],
    action: { label: "My Bookings", path: "/bookings" },
  },
  "cit-rate-facility": {
    question: "How do I rate a facility I booked?",
    answer: "Once the booking date has passed and it's paid for (or free), open My Bookings and click Mark as Complete to confirm the visit happened. You'll be prompted right away to give it a star rating and an optional comment. Already rated it? Click Edit Rating on that booking anytime to change it.",
    related: ["cit-bookings", "cit-facilities"],
    action: { label: "My Bookings", path: "/bookings" },
  },
  "cit-payments": {
    question: "Where do I see my payment history?",
    answer: "Facility booking payments show up on each booking card in My Bookings. You will see the status, the amount, and a Pay Now button if money is due. Subscription payments are on the Premium Subscription page.",
    related: ["cit-bookings", "cit-premium-billing"],
    action: { label: "My Bookings", path: "/bookings" },
  },
  "cit-notif": {
    question: "How do notifications work?",
    answer: "You'll get notified whenever a complaint's status changes, a booking is confirmed, or a payment goes through. Check the bell icon or the Notifications page.",
    related: ["cit-status"],
    action: { label: "Notifications", path: "/notifications" },
  },

  // Troubleshooting and support
  "cit-troubleshoot": {
    question: "Something is not working. What should I check?",
    answer: "These are the four things people get stuck on most. If the Submit Complaint form will not let you through, check that your Premium plan is still active, because you need it to file a complaint. If your booking still says Pending, that is normal, an admin has to approve it first. If a booking shows money due, open My Bookings and click Pay Now on that booking. And if you cannot find an official notice in the Community Feed, look on the Announcements page instead, because notices are kept there.",
    related: ["cit-premium", "cit-bookings", "cit-announcements", "cit-support"],
  },
  "cit-support": {
    question: "How do I talk to a real person?",
    answer: "Go to the home page and scroll down to Contact Us. You will find the admin office email and phone number there. If your question is about one complaint, open it from My Requests first. It shows you which department and officer is handling it, so you know who to ask for.",
    related: ["cit-troubleshoot", "cit-track-own"],
    action: { label: "Contact Us", path: "/#contact" },
  },

  // Staff
  "staff-dashboard": {
    question: "What's on my Staff Dashboard?",
    answer: "You'll see how many complaints are assigned to you in total, plus a breakdown of pending, in progress, and resolved, along with your most recent assignments.",
    related: ["staff-assign", "staff-all-complaints", "staff-dept"],
    action: { label: "Staff Dashboard", path: "/staff/dashboard" },
  },
  "staff-all-complaints": {
    question: "Can I see complaints outside my department?",
    answer: "Yes. Open All Complaints from the sidebar to browse every complaint in the city, not just the ones routed to you. You can search by title or location and filter by category and status. It is the same privacy-safe view citizens get, so it is useful for checking whether an issue has already been reported elsewhere. To actually work on a complaint, use My Assignments instead.",
    related: ["staff-assign", "staff-update"],
    action: { label: "Browse All Complaints", path: "/staff/complaints/all" },
  },
  "staff-assign": {
    question: "How do I see my assigned complaints?",
    answer: "My Assignments lists every complaint routed to your department, with the newest ones first. It shows only your department's work. To see every complaint in the city, use All Complaints.",
    related: ["staff-update", "staff-all-complaints", "staff-dept"],
    action: { label: "My Assignments", path: "/staff/complaints" },
  },
  "staff-update": {
    question: "How do I update a complaint's status?",
    answer: "Open the complaint from My Assignments and move it to In Progress or Resolved. You can add a note for the citizen too.",
    related: ["staff-assign", "cit-status"],
    action: { label: "My Assignments", path: "/staff/complaints" },
  },
  "staff-dept": {
    question: "Which department am I assigned to?",
    answer: "Cyber Panchayat has 5 departments: Road Maintenance, Electricity, Water Supply, Sanitation, and Parks & Public Spaces. Each staff account belongs to exactly one.",
    related: ["staff-assign"],
  },
  "staff-community": {
    question: "Can I post on the Community Feed as staff?",
    answer: "Yep, staff can post, comment, and like just like citizens, and you can share department updates straight to the feed too.",
    related: ["staff-assign"],
    action: { label: "Staff Community Posts", path: "/staff/community" },
  },

  // Admin
  "admin-overview": {
    question: "What can I do from the Admin Dashboard?",
    answer: "You'll see system-wide stats like total, pending, and resolved complaints, citizen satisfaction, and Premium subscription revenue, plus quick links to every management area.",
    related: ["admin-reports", "admin-subs", "admin-facilities", "admin-bookings", "admin-community"],
    action: { label: "Admin Dashboard", path: "/admin/dashboard" },
  },
  "admin-officers": {
    question: "How do I manage officers?",
    answer: "Manage Officers lets you view, add, or reassign the officer in charge of each department.",
    related: ["admin-dept", "admin-users"],
    action: { label: "Manage Officers", path: "/admin/officers" },
  },
  "admin-dept": {
    question: "How do I manage departments?",
    answer: "Manage Departments lists all 5 departments along with their assigned officer and contact info, and you can edit them from there.",
    related: ["admin-officers"],
    action: { label: "Manage Departments", path: "/admin/departments" },
  },
  "admin-complaints": {
    question: "How do I oversee all complaints?",
    answer: "Manage Requests shows every complaint on the platform. You can reassign, reject, or budget-tag any of them.",
    related: ["admin-officers", "admin-reports"],
    action: { label: "Manage Requests", path: "/admin/complaints" },
  },
  "admin-subs": {
    question: "How do I view subscription revenue?",
    answer: "Manage Subscriptions shows your active and cancelled counts, Monthly Recurring Revenue, total collected, and the full billing history for each citizen.",
    related: ["admin-overview", "admin-users"],
    action: { label: "Manage Subscriptions", path: "/admin/subscriptions" },
  },
  "admin-users": {
    question: "How do I manage user accounts?",
    answer: "Manage Users lists every citizen, staff, and admin account. You can enable, disable, or edit any of them.",
    related: ["admin-officers", "admin-subs"],
    action: { label: "Manage Users", path: "/admin/users" },
  },

  "admin-reports": {
    question: "How do I see complaint analytics?",
    answer: "The Admin Dashboard shows the live breakdown. You get total, pending, in progress, on hold, and resolved complaints, plus the average citizen satisfaction score. To see complaints one by one, open Manage Requests.",
    related: ["admin-overview", "admin-complaints"],
    action: { label: "Admin Dashboard", path: "/admin/dashboard" },
  },
  "admin-facilities": {
    question: "How do I manage community facilities?",
    answer: "Manage Facilities lets you oversee every parks, hall, ground, or library listing on the platform.",
    related: ["admin-bookings", "admin-overview"],
    action: { label: "Manage Facilities", path: "/admin/facilities" },
  },
  "admin-bookings": {
    question: "How do I manage facility bookings?",
    answer: "Manage Bookings shows every booking request platform-wide, whether it's pending, confirmed, completed, or cancelled, so you can review each one.",
    related: ["admin-facilities", "admin-overview"],
    action: { label: "Manage Bookings", path: "/admin/bookings" },
  },
  "admin-community": {
    question: "How do I moderate the Community Feed?",
    answer: "Community Management lets admins review posts and publish official Announcements.",
    related: ["cit-announcements"],
    action: { label: "Community Management", path: "/admin/community" },
  },
}

// Troubleshooting is on the main menu for every role. Those questions (plan
// expired, booking still pending, payment due) are the ones people arrive with,
// so they shouldn't have to dig through a category to find them.
export const FAQ_ROOTS = {
  citizen: ["cit-file", "cit-status", "cit-premium", "cit-community", "cit-facilities", "cit-troubleshoot"],
  staff: ["staff-dashboard", "staff-assign", "staff-community", "staff-dept", "cit-troubleshoot"],
  admin: ["admin-overview", "admin-officers", "admin-subs", "admin-users", "admin-reports", "cit-troubleshoot"],
}

// Topic grouping for the /faq page.
//
// FAQ_ROOTS above is keyed by role and decides where the chatbot starts a
// conversation. This one is keyed by subject and decides how a reader browses
// the whole list. Those are two different jobs, so they're kept separate.
//
// This is a lookup instead of a `category` field on each node, so the nodes
// stay exactly as the chatbot has always seen them and adding this page can't
// change how the chatbot behaves. It also keeps the whole layout in one place
// instead of spreading it across 34 objects.
//
// `audience` decides who sees a section. EVERYONE includes visitors who are not
// logged in. That's the point of the page, since the chatbot only shows for
// logged-in users.
export const AUDIENCE = {
  EVERYONE: "everyone",
  STAFF: "staff",
  ADMIN: "admin",
}

// Which answer explains which page.
//
// The assistant uses this to put the current page's question at the top of its
// menu, so opening it on the Bookings page leads with the bookings answer. That
// is the contextual help, handled by the widget that is already on every page
// rather than by another Help link competing with the one in the sidebar.
//
// A page that isn't listed simply gets the normal menu.
export const HELP_FOR_ROUTE = {
  "new-request": "cit-file",
  "my-requests": "cit-status",
  "complaint-detail": "cit-rate",
  "track-citizen": "cit-track-own",
  "my-subscription": "cit-premium",
  "facilities": "cit-facilities",
  "my-bookings": "cit-bookings",
  "community-feed": "cit-community",
  "announcements": "cit-announcements",
  "notifications": "cit-notif",
  "staff-complaints": "staff-assign",
  "staff-update-status": "staff-update",
  "staff-community": "staff-community",
  "staff-dashboard": "staff-dashboard",
  "admin-dashboard": "admin-overview",
  "admin-complaints": "admin-complaints",
  "admin-officers": "admin-officers",
  "admin-departments": "admin-dept",
  "admin-users": "admin-users",
  "admin-subscriptions": "admin-subs",
  "admin-facilities": "admin-facilities",
  "admin-bookings": "admin-bookings",
  "admin-community": "admin-community",
}

export const FAQ_CATEGORIES = [
  {
    id: "complaints",
    label: "Complaints",
    blurb: "How to report a problem, follow it, and close it.",
    audience: AUDIENCE.EVERYONE,
    nodes: [
      "cit-file", "cit-categories", "cit-ai-scan", "cit-duplicate",
      "cit-all-complaints", "cit-status", "cit-track-own", "cit-rate",
    ],
  },
  {
    id: "premium",
    label: "Premium and Payments",
    blurb: "What the plan gives you, how you are billed, and where to find your bills.",
    audience: AUDIENCE.EVERYONE,
    nodes: ["cit-premium", "cit-premium-billing", "cit-premium-cancel", "cit-payments"],
  },
  {
    id: "facilities",
    label: "Facilities and Bookings",
    blurb: "How to book a hall, ground, or library, and manage your bookings.",
    audience: AUDIENCE.EVERYONE,
    nodes: ["cit-facilities", "cit-bookings", "cit-rate-facility"],
  },
  {
    id: "community",
    label: "Community and Announcements",
    blurb: "How to post in the feed, and where to find official notices.",
    audience: AUDIENCE.EVERYONE,
    nodes: ["cit-community", "cit-announcements"],
  },
  {
    id: "account",
    label: "Your Account",
    blurb: "Your ward setting and how you get updates.",
    audience: AUDIENCE.EVERYONE,
    nodes: ["cit-ward", "cit-notif"],
  },
  {
    id: "troubleshooting",
    label: "Problems and Support",
    blurb: "Start here when something is not working.",
    audience: AUDIENCE.EVERYONE,
    nodes: ["cit-troubleshoot", "cit-support"],
  },
  {
    id: "staff",
    label: "For Staff",
    blurb: "Handling the complaints given to you, and posting department updates.",
    audience: AUDIENCE.STAFF,
    nodes: ["staff-dashboard", "staff-assign", "staff-all-complaints", "staff-update", "staff-dept", "staff-community"],
  },
  {
    id: "admin",
    label: "For Admins",
    blurb: "Managing departments, officers, users, and the whole platform.",
    audience: AUDIENCE.ADMIN,
    nodes: [
      "admin-overview", "admin-complaints", "admin-officers", "admin-dept",
      "admin-users", "admin-subs", "admin-reports",
      "admin-facilities", "admin-bookings", "admin-community",
    ],
  },
]
