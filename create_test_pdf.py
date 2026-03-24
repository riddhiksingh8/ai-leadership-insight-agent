"""Run this once to generate sample leadership report PDFs for testing."""

import os
from fpdf import FPDF, XPos, YPos

os.makedirs("backend/documents", exist_ok=True)

def make_pdf(filename):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    def heading(text):
        pdf.set_font("Helvetica", "B", 14)
        pdf.ln(4)
        pdf.cell(0, 10, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def body(text):
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 7, text)
        pdf.ln(2)

    def title(line1, line2):
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 20)
        pdf.cell(0, 12, line1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 8, line2, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        pdf.ln(6)

    return pdf, heading, body, title


# ── Report 1: Q1 2025 Financial ───────────────────────────────────────────────
pdf, H, B, T = make_pdf("q1_2025_report.pdf")
T("Acme Corp - Q1 2025 Leadership Report", "Confidential | Prepared for Executive Leadership")

H("1. Financial Performance")
B("Total revenue for Q1 2025 reached $5.2M, a 12% year-over-year increase. "
  "The cloud services division grew 25% YoY, contributing $1.8M. "
  "Operating margin improved to 18% from 15% in Q1 2024. "
  "EBITDA stands at $940K, up from $720K last year. "
  "Customer acquisition cost decreased 8% to $320 per customer.")

H("2. Sales & Growth")
B("The sales team exceeded Q1 target by 8%, closing 142 new accounts. "
  "Average deal size grew from $28K to $36K. Enterprise segment (deals > $100K) "
  "now represents 34% of new bookings, up from 22% a year ago. "
  "Pipeline coverage ratio is 3.8x, giving strong Q2 visibility.")

H("3. Customer Success")
B("Net Revenue Retention reached 118%, driven by strong expansion in existing accounts. "
  "Customer churn reduced from 4.1% to 3.2% quarter-over-quarter. "
  "NPS improved to 62, up 7 points from Q4 2024. "
  "Support ticket resolution time decreased 22% after the new triage rollout.")

H("4. Operations & Headcount")
B("Total headcount is 214, with 18 new hires in Q1: Engineering (8), Sales (6), CS (4). "
  "Voluntary attrition was 6.2% annualised, below industry benchmark of 9%. "
  "Infrastructure costs as a percentage of revenue dropped to 11% from 14%.")

H("5. Key Risks")
B("Supply chain delays could impact the on-prem product line (Low probability, High impact). "
  "Increased competition from two well-funded SMB market entrants. "
  "EU data residency regulatory review may require architecture changes.")

H("6. Outlook - Q2 2025")
B("Q2 revenue guidance is $5.6M-$5.9M (8-13% QoQ growth). "
  "Three product releases scheduled: Analytics 2.0 (April), Mobile App v3 (May), AI Assistant beta (June). "
  "Series B funding round board approval expected in May.")

pdf.output("backend/documents/q1_2025_report.pdf")
print("Created: backend/documents/q1_2025_report.pdf")


# ── Report 2: Annual Strategy 2025 ───────────────────────────────────────────
pdf, H, B, T = make_pdf("strategy_2025.pdf")
T("Acme Corp - 2025 Annual Strategy & OKRs", "Internal Strategy Document | CEO Office")

H("Executive Summary")
B("2025 is a pivotal year for Acme Corp. Following three consecutive years of 20%+ growth, "
  "we are shifting from hypergrowth to efficient growth. Our target is $24M ARR by year-end, "
  "representing 18% growth at a Rule of 40 score above 35. "
  "The board has approved a $12M operating budget with a clear path to profitability in Q4.")

H("Strategic Pillar 1 - AI-First Product")
B("Every core product feature will be enhanced with AI by Q3 2025. "
  "We are integrating LLM capabilities into our analytics dashboard (Q2), "
  "automated report generation (Q3), and predictive alerts (Q4). "
  "Dedicated AI team of 12 engineers will be fully staffed by end of March. "
  "Target: AI features to contribute 15% of new ARR by Q4.")

H("Strategic Pillar 2 - Geographic Expansion")
B("We will enter Japan and Brazil in H2 2025. Japan launch scheduled for August with a local partner. "
  "Brazil launch in October via direct sales with 3 quota-carrying reps. "
  "Combined target for new markets: $1.2M ARR by December 2025. "
  "Localisation (language, compliance, payments) budget: $400K.")

H("Strategic Pillar 3 - Partner Ecosystem")
B("Target: 25 certified reseller partners by year-end, up from 6 today. "
  "Partner portal and training program launching in April. "
  "Expected partner-sourced revenue: 20% of new bookings by Q4. "
  "Two anchor global SIs (System Integrators) in active contract negotiation.")

H("Company OKRs - 2025")
B("O1: Achieve $24M ARR. KRs: $5.5M Q1, $6M Q2, $6.2M Q3, $6.3M Q4. "
  "O2: Improve gross margin to 72%. KR: Reduce hosting costs by 18% via architecture refactor. "
  "O3: Launch in 2 new markets. KR: First paying customer in Japan by Sep, Brazil by Nov. "
  "O4: Reach NPS of 70. KR: Reduce P1 bug resolution time to under 4 hours.")

H("Budget Allocation")
B("Engineering: $4.8M (40%). Sales & Marketing: $3.6M (30%). "
  "Customer Success: $1.44M (12%). G&A: $1.2M (10%). "
  "International Expansion: $960K (8%). Total OpEx: $12M.")

H("Risks & Assumptions")
B("Key assumption: macroeconomic conditions remain stable in H2. "
  "Risk 1: Delayed AI feature release could impact competitive positioning (Medium/High). "
  "Risk 2: Japan partner dependency - single partner failure would delay market entry. "
  "Risk 3: Series B close delayed beyond Q2 could trigger a hiring freeze in Q3.")

pdf.output("backend/documents/strategy_2025.pdf")
print("Created: backend/documents/strategy_2025.pdf")


# ── Report 3: HR & Culture Report ────────────────────────────────────────────
pdf, H, B, T = make_pdf("hr_culture_report.pdf")
T("Acme Corp - People & Culture Report Q1 2025", "HR Department | Confidential")

H("Headcount Summary")
B("Total employees: 214 (full-time). Contractors: 18. "
  "Breakdown by department: Engineering 98, Sales 52, Customer Success 31, "
  "Marketing 14, G&A 19. "
  "Gender split: 54% male, 43% female, 3% non-binary. "
  "Management layer: 28 people managers, avg team size of 6.6.")

H("Hiring & Attrition")
B("Q1 hires: 18 total. Time-to-hire averaged 34 days, down from 41 days in Q4 2024. "
  "Offer acceptance rate: 87%, up from 79% last quarter. "
  "Voluntary attrition: 6.2% annualised. Involuntary attrition: 1.1%. "
  "Top reasons for voluntary departure: compensation (38%), career growth (31%), relocation (18%).")

H("Compensation & Benefits")
B("Annual compensation review completed in February. Average merit increase: 5.2%. "
  "Equity refresh grants issued to 61 employees rated Exceeds Expectations or above. "
  "Benefits utilisation: 91% enrolled in health plan, 67% contributing to 401(k), "
  "42% using the $1,200 annual learning & development stipend.")

H("Performance & Engagement")
B("Q1 performance reviews completed by 96% of managers on time. "
  "Rating distribution: Exceeds 18%, Meets 71%, Below 11%. "
  "Employee engagement score: 74/100, up 3 points from Q4 2024. "
  "Lowest scoring areas: cross-functional collaboration (61) and career clarity (65). "
  "Highest scoring areas: team belonging (84) and manager quality (81).")

H("Learning & Development")
B("1,240 hours of training logged in Q1 across all departments. "
  "Top programs: Leadership Foundations (22 participants), "
  "AWS Certification prep (15), and Sales Methodology bootcamp (18). "
  "Internal mentorship program launched in February with 34 mentor-mentee pairs. "
  "L&D budget utilisation: 38% YTD.")

H("DEI Initiatives")
B("Women in Leadership: 31% of director+ roles, target is 40% by end of 2025. "
  "Underrepresented groups in Engineering: 22%, up from 17% a year ago. "
  "Three ERGs active: WomenInTech (67 members), Pride@Acme (41), and Roots (28). "
  "Blind resume screening rolled out company-wide in January.")

H("Q2 People Priorities")
B("Hire 16 net new employees: 12 in Engineering, 4 in Sales. "
  "Launch manager effectiveness training for all 28 people managers. "
  "Complete compensation benchmarking against updated Radford survey data. "
  "Pilot 4-day work week for one Engineering team and measure productivity impact.")

pdf.output("backend/documents/hr_culture_report.pdf")
print("Created: backend/documents/hr_culture_report.pdf")
