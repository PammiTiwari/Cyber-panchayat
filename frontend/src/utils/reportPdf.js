import jsPDF from "jspdf"

// jsPDF's built-in fonts only cover WinAnsi - the same reason invoicePdf.js
// swaps ₹ for "Rs.". Special characters outside that range don't just
// render blank, they can come out as an unrelated garbage glyph (a stray
// quote mark, "%Ë", etc.) since the byte gets reinterpreted through the
// wrong encoding. This is a defensive net for any *dynamic* text (a
// citizen's own complaint description, admin remarks, feedback) that might
// contain one - all the report's own template text avoids them at the
// source instead of relying on this.
function safe(text) {
  return String(text)
    .replace(/[•·]/g, ",")
    .replace(/[—–]/g, "-")
    .replace(/…/g, "...")
    .replace(/₹/g, "Rs. ")
}

const MARGIN_L = 18
const MARGIN_R = 192
const PAGE_BOTTOM = 280

function fmtDate(d) {
  if (!d) return "Not set"
  return new Date(d).toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "numeric" })
}
function fmtDateTime(d) {
  if (!d) return "Not set"
  return new Date(d).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })
}

// Starts a new page and resets to the top margin once the cursor gets too
// close to the bottom - the manual pagination jsPDF expects without a table
// plugin, so a long complaint list doesn't run off the page.
function ensureSpace(doc, y, needed = 8) {
  if (y + needed > PAGE_BOTTOM) {
    doc.addPage()
    return 20
  }
  return y
}

// `metaLines` renders one fact per line rather than one line joined with
// separator punctuation - reads cleaner, and sidesteps needing a bullet or
// dash glyph at all for the header.
function drawHeader(doc, title, metaLines) {
  let y = 22
  doc.setFont("helvetica", "bold")
  doc.setFontSize(16)
  doc.text(safe(title), MARGIN_L, y)
  y += 8
  doc.setFont("helvetica", "normal")
  doc.setFontSize(10)
  doc.setTextColor(100)
  metaLines.forEach(line => {
    doc.text(safe(line), MARGIN_L, y)
    y += 5
  })
  doc.setTextColor(20)
  y += 3
  doc.setDrawColor(220)
  doc.line(MARGIN_L, y, MARGIN_R, y)
  return y + 8
}

/**
 * Bulk complaint history report - used by MyRequests.vue. `complaints` is
 * whatever list is currently on screen (already respects the page's own
 * search/status/category/date-range filters), so exporting "the filtered
 * view" needs no separate date picker here.
 */
export function downloadComplaintsReportPdf({ citizenName, complaints, dateFrom, dateTo }) {
  const doc = new jsPDF({ unit: "mm", format: "a4" })
  const metaLines = [
    `Prepared for ${citizenName}`,
    `Generated ${fmtDate(new Date())}`,
    `${complaints.length} complaint${complaints.length === 1 ? "" : "s"}${
      dateFrom || dateTo ? `, from ${dateFrom || "the start"} to ${dateTo || "today"}` : ""
    }`,
  ]
  let y = drawHeader(doc, "Cyber Panchayat: Complaint History Report", metaLines)

  const cols = [
    { key: "cmp_id", label: "ID", x: MARGIN_L, w: 18 },
    { key: "category", label: "Category", x: MARGIN_L + 20, w: 20 },
    { key: "title", label: "Title", x: MARGIN_L + 42, w: 62 },
    { key: "status", label: "Status", x: MARGIN_L + 106, w: 26 },
    { key: "upvotes_count", label: "Upvotes", x: MARGIN_L + 134, w: 16 },
    { key: "created_at", label: "Filed", x: MARGIN_L + 152, w: 22 },
  ]

  doc.setFont("helvetica", "bold")
  doc.setFontSize(9)
  cols.forEach(c => doc.text(c.label, c.x, y))
  y += 2
  doc.setDrawColor(220)
  doc.line(MARGIN_L, y, MARGIN_R, y)
  y += 6

  doc.setFont("helvetica", "normal")
  if (!complaints.length) {
    doc.setTextColor(120)
    doc.text("No complaints match the current filters.", MARGIN_L, y)
    doc.setTextColor(20)
  }
  complaints.forEach(c => {
    // Title wraps across lines within its column instead of truncating with
    // an ellipsis, so the full title always makes it into the PDF - the row
    // height then grows to fit however many lines that takes.
    const titleLines = doc.splitTextToSize(safe(c.title || "Untitled"), cols[2].w - 2)
    const rowHeight = Math.max(titleLines.length * 5, 8)
    y = ensureSpace(doc, y, rowHeight + 2)
    doc.text(safe(c.cmp_id || "-"), cols[0].x, y)
    doc.text(safe(c.category || "-"), cols[1].x, y, { maxWidth: cols[1].w })
    doc.text(titleLines, cols[2].x, y)
    doc.text(safe(String(c.status || "-").replace(/_/g, " ")), cols[3].x, y, { maxWidth: cols[3].w })
    doc.text(String(c.upvotes_count || 0), cols[4].x, y)
    doc.text(fmtDate(c.created_at), cols[5].x, y)
    y += rowHeight
  })

  doc.save(`complaint-report-${Date.now()}.pdf`)
}

// Mirrors ComplaintDetail.vue's .timeline-dot colors exactly (var(--primary),
// done-yellow, var(--warning), var(--success), var(--danger), var(--border)),
// so the PDF timeline matches what's on screen instead of a flat done/pending
// green. Drawn as vector shapes rather than a text glyph (a checkmark,
// bracket, etc.) so there is no font/encoding surface to break at all.
const STEP_COLORS = {
  blue: [0, 82, 255],
  yellow: [202, 138, 4],
  orange: [180, 83, 9],
  green: [21, 128, 61],
  red: [220, 38, 38],
  pending: [226, 232, 240],
}
function drawStepMarker(doc, x, y, color) {
  const [r, g, b] = STEP_COLORS[color] || STEP_COLORS.pending
  doc.setFillColor(r, g, b)
  doc.circle(x, y, 2, "F")
}

/**
 * Single-complaint report - used by ComplaintDetail.vue. Mirrors the same
 * fields and timeline steps shown on that page.
 */
export function downloadComplaintReportPdf({ complaint }) {
  const doc = new jsPDF({ unit: "mm", format: "a4" })
  let y = drawHeader(doc, "Cyber Panchayat: Complaint Report",
    [`Complaint ${complaint.cmp_id}`, `Generated ${fmtDate(new Date())}`])

  const rows = [
    ["Title", complaint.title || "-"],
    ["Status", (complaint.status || "-").replace(/_/g, " ")],
    ["Priority", complaint.priority || "-"],
    ["Category", complaint.category || "-"],
    ["Department", complaint.department || "-"],
    ["Location", complaint.address || "-"],
    ["Ward", complaint.ward || "-"],
    ["Description", complaint.description || "-"],
    ["Submitted By", complaint.citizen_name || "-"],
    ["Submitted On", fmtDateTime(complaint.created_at)],
  ]
  if (complaint.assignment) {
    rows.push(["Assigned To", `${complaint.assignment.staff_name}${complaint.assignment.staff_department ? ` (${complaint.assignment.staff_department})` : ""}`])
  }
  if (complaint.rating != null) rows.push(["Citizen Rating", `${complaint.rating} out of 5${complaint.feedback ? `: "${complaint.feedback}"` : ""}`])

  doc.setFontSize(10.5)
  rows.forEach(([label, value]) => {
    y = ensureSpace(doc, y, 14)
    doc.setFont("helvetica", "bold")
    doc.text(label, MARGIN_L, y)
    doc.setFont("helvetica", "normal")
    const lines = doc.splitTextToSize(safe(value), MARGIN_R - MARGIN_L - 45)
    doc.text(lines, MARGIN_L + 45, y)
    y += 7 * Math.max(lines.length, 1)
  })

  y = ensureSpace(doc, y, 16)
  y += 4
  doc.setDrawColor(220)
  doc.line(MARGIN_L, y, MARGIN_R, y)
  y += 8
  doc.setFont("helvetica", "bold")
  doc.setFontSize(12)
  doc.text("Timeline", MARGIN_L, y)
  y += 9

  const inProgressDone = ["in_progress", "resolved", "closed"].includes(complaint.status)
  const resolvedDone = ["resolved", "closed"].includes(complaint.status)
  const rejected = complaint.status === "rejected"
  const steps = [
    { label: "Complaint Submitted", color: "blue",
      at: fmtDateTime(complaint.created_at), remark: null },
    { label: "Assigned to Department", color: complaint.assignment ? "yellow" : "pending",
      at: complaint.assignment ? `${fmtDateTime(complaint.assignment.assigned_at)} - ${complaint.assignment.staff_department}` : "Pending assignment",
      remark: complaint.assignment?.notes },
    { label: "Work In Progress", color: inProgressDone ? "orange" : "pending",
      at: complaint.in_progress_at ? fmtDateTime(complaint.in_progress_at) : (inProgressDone ? "Status updated to in progress" : "Yet to start"),
      remark: complaint.in_progress_notes },
    rejected
      ? { label: "Rejected", color: "red", at: "This complaint was rejected", remark: complaint.admin_notes }
      : { label: "Resolved", color: resolvedDone ? "green" : "pending",
          at: complaint.resolved_at ? fmtDateTime(complaint.resolved_at) : "Yet to be resolved",
          remark: complaint.resolved_notes },
  ]
  doc.setFontSize(10.5)
  steps.forEach(s => {
    const remarkLines = s.remark ? doc.splitTextToSize(safe(s.remark), MARGIN_R - MARGIN_L - 10) : []
    y = ensureSpace(doc, y, 13 + remarkLines.length * 5)
    drawStepMarker(doc, MARGIN_L + 2, y - 1.5, s.color)
    doc.setFont("helvetica", "bold")
    doc.setTextColor(20)
    doc.text(safe(s.label), MARGIN_L + 10, y)
    doc.setFont("helvetica", "normal")
    doc.setTextColor(100)
    doc.text(safe(s.at), MARGIN_L + 10, y + 5)
    y += 10
    if (remarkLines.length) {
      doc.setFont("helvetica", "italic")
      doc.text(remarkLines, MARGIN_L + 10, y)
      y += remarkLines.length * 5
    }
    doc.setTextColor(20)
    y += 3
  })

  doc.save(`${complaint.cmp_id}-report.pdf`)
}
