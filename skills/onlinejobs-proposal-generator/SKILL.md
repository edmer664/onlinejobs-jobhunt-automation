---
name: onlinejobs-proposal-generator
description: Evaluates job descriptions from OnlineJobs.ph (or similar remote platforms), verifies candidate qualifications against grounded facts, detects screening questions/code words, and crafts high-converting, tailored application letters and proposals.
version: 1.0.0
---

# OnlineJobs.ph Job Evaluator & High-Conversion Proposal Generator

## When to Use This Skill

Activate this skill whenever the user:
- Provides a job description (JD) from **OnlineJobs.ph** (or similar remote platforms like Upwork, LinkedIn, Facebook groups, or direct client job boards) and asks for an evaluation or proposal/application letter.
- Asks: *"Write me an application letter for this job"*, *"Evaluate this JD and create an OnlineJobs.ph proposal"*, *"Draft a cover letter for this VA role"*, or *"Check if I should apply and write the proposal"*.
- Wants to optimize response rates on remote job applications while ensuring **100% factual accuracy** with zero hallucinations.

---

## The Strategic Reality of OnlineJobs.ph (OLJ)

To achieve high conversion (interview callbacks of 20%+ vs. platform average of <3%), you must understand client psychology on OnlineJobs.ph:

1. **The Inundation Problem:** A standard OLJ posting receives **50 to 200+ applications** within 24 to 48 hours.
2. **The "Elimination Mode" Filter:** Employers do not read applications to find reasons to hire; they scan to **find reasons to reject**.
3. **The AI Slop Plague:** 80%+ of applicants submit generic, robotic cover letters (*"Dear Hiring Manager, I am writing to express my deepest enthusiasm for your esteemed organization..."*). Clients instantly discard them.
4. **The Mobile/Dashboard Snippet Preview:** In the employer's OLJ inbox, only the **first 50–70 characters** of the message are visible before clicking. If that snippet reads like boilerplate, the message stays unopened.
5. **The Fear of Ghosting & Downtime:** Western employers (US, UK, Australia, Canada) fear two things most with remote workers:
   - Power/internet outages causing sudden disappearance.
   - Overpromising skills that turn out to be fake.
6. **The "Attention Test" Trap:** Over 60% of savvy OLJ employers hide screening codes or specific questions to eliminate automated bots and lazy applicants.

---

## Two-Phase Operating Procedure

```
┌────────────────────────────────────────────────────────┐
│  PHASE 1: JOB DESCRIPTION EVALUATION & TRAP AUDIT      │
│  - Screener & Code Word Extraction                     │
│  - Core Pain Point & Deliverables Identification       │
│  - Candidate Fact-Grounding & Fit Scoring (0-100)      │
│  - Honest Gap Strategy & Go / No-Go Recommendation    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  PHASE 2: HIGH-CONVERSION PROPOSAL GENERATION          │
│  - Strategic Subject Line (with required codes)        │
│  - 2-Sentence Hook (Direct answer + Client's pain)     │
│  - 2-3 Fact-Grounded Proof Bullets with Metrics        │
│  - Remote Reliability & Tech Spec Anchor               │
│  - Frictionless Call-to-Action (150-250 Words Max)     │
└────────────────────────────────────────────────────────┘
```

---

## Phase 1: Job Description Evaluation Framework

Before drafting a single word of the application, thoroughly analyze the job description across these 4 checkpoints:

### 1. Screening Code & Attention Trap Audit
Scan the job description for:
- **Secret Code Words / Phrases:** (e.g., *"Put 'Blueberry' in your subject line"*, *"Start your proposal with 'Ready to Work'"*).
- **Mandatory Screening Questions:** (e.g., *"What is your typing speed?"*, *"Have you used Slack before?"*, *"What timezone can you work?"*).
- **Required Proof Attachments / Links:** (e.g., Speedtest screenshot, typing test link, portfolio link, Loom video intro).
- **Negative Filters:** (e.g., *"Do not apply if you cannot work US EST night shift"*, *"Must have 2+ years of Shopify experience"*).

> **CRITICAL RULE:** Any detected screening code or question **MUST** be answered at the very top of the application letter. Failure here means instant deletion.

### 2. Core Business Pain Point Extraction
Identify the root reason the client is spending their hard-earned money to hire:
- Are they overwhelmed by messy data/spreadsheets?
- Are they spending too many hours sourcing candidates or sending outreach?
- Do they need someone to guard their calendar and clear their inbox?
- Are they struggling with consistent social media graphics and video reels?
- Are customers waiting too long for replies in Messenger or email?

### 3. Candidate Ground Truth Verification
Verify every claimed skill, tool, and metric against the candidate's authentic source of truth (`config/profile.yaml` or user-supplied CV).

#### Candidate Ground Truth Matrix (Config-Driven):
| Category | Verified Candidate Facts (from `config/profile.yaml`) | What NOT to Claim |
|---|---|---|
| **Identity & Contact** | `candidate.display_name`, `candidate.email`, `candidate.location`, `candidate.linkedin` | Do NOT fabricate unlisted personal contact details. |
| **Education & Credentials** | `candidate.degree`, `candidate.certifications` | Do NOT claim unverified degrees or licenses. |
| **Experience & Metrics** | `verified_experience[*].role`, `company`, `metrics` | Do NOT inflate years of experience or invent roles. |
| **Core Skills** | `candidate_skills[*].label` | Do NOT claim unlisted tools (Shopify, HubSpot, QuickBooks, Python). |
| **Workstation & Specs** | `logistics.hardware`, `logistics.internet`, `logistics.available_hours` | Grounded specs: dedicated workspace, high-speed fiber + backup power/data. |

### 4. Fit Scoring & Go / No-Go Decision
Calculate candidate suitability:
- **Tier 1: Strong Fit (80–100%)** — Core target roles aligned with verified strengths.
  *Action:* Apply immediately with primary high-converting proposal.
- **Tier 2: Good / Transferable Fit (60–79%)** — Operations Assistant, E-commerce Admin, Customer/Inquiry Support.
  *Action:* Apply highlighting foundational systems (Excel, database management, fast learning).
- **Tier 3: Low Fit / Dealbreaker (<60%)** — Senior software developer, CPA/tax lawyer, fluent bilingual Spanish, cold-calling phone sales closer.
  *Action:* Explicitly advise the user **NOT to apply** to save OLJ application points.

---

## Phase 2: High-Conversion OLJ Proposal Architecture

Every OnlineJobs.ph proposal must follow this exact high-conversion framework:

```
[SUBJECT LINE]
Role Title Application - [Candidate Full Name] - [Secret Code Word if required] | [One Strongest Fact Hook]

[LINE 1: ATTENTION TEST / SCREENING ANSWERS]
(Direct, zero-fluff answers to any screening questions or secret phrases required by the client)

[PARAGRAPH 1: THE EMPATHY & PROBLEM-FIRST HOOK (2-3 sentences)]
(Reflect the client's exact problem and state immediate readiness to take it off their plate)

[PARAGRAPH 2: 2-3 FACT-GROUNDED PROOF BULLETS]
(Specific, quantifiable achievements directly addressing the JD requirements)

[PARAGRAPH 3: LOGISTICS, WORKSTATION & ZERO-RISK REASSURANCE (2 sentences)]
(Timezone availability, fiber connection + backup, immediate start)

[CALL TO ACTION & PROFESSIONAL SIGN-OFF (2 sentences)]
(Frictionless low-pressure invite for a 10-minute chat or short test task)
```

---

## Golden Rules for High Conversion on OnlineJobs.ph

### Rule 1: The First Sentence Must Be About THEM, Not YOU
- ❌ **Bad:** "Hi, my name is Alex and I am looking for a job as your VA." (Boring, selfish, client skips).
- ✅ **Good:** "You need a detail-oriented Virtual Assistant who can take over your daily candidate sourcing on LinkedIn and keep your Google Sheets pipeline immaculate without handholding."

### Rule 2: Keep Word Count Strictly Between 150 and 250 Words
OnlineJobs.ph employers read on mobile screens or scroll through dozens of messages. Long essays are skipped. Brevity demonstrates respect and clear communication.

### Rule 3: Use the "Micro-Proof" Formula
Instead of broad adjectives (*"I am hardworking, dedicated, and fast-learning"*), use verified micro-proofs:
- *"In my previous role, I published ~30 targeted job postings daily and coordinated onboarding for 30 new hires."*
- *"Certified spreadsheet specialist who audited and organized financial transaction logs with 100% verified accuracy."*

### Rule 4: Tackle Remote Trust Head-On
Prevent employer anxiety before they even ask:
- *"I work from a dedicated home office equipped with high-speed fiber internet and mobile backup data to ensure zero downtime."*
- *"I am fully available to work during your preferred hours ([Client Timezone e.g., US EST / AU AEST / UK GMT]) and can start immediately."*

### Rule 5: Low-Friction Call-to-Action (CTA)
Never demand a job or ask for a long interview:
- ❌ *"Please review my attached resume and hire me."*
- ✅ *"Are you open to a quick 10-minute chat or a short sample task this week so I can demonstrate how I work?"*

---

## Role-Specific Proposal Blueprints

### Blueprint 1: Virtual Assistant / Executive Assistant
```text
Subject: Virtual Assistant Application - [Candidate Full Name] | [Secret Code if any] - Reliable Admin Support

Hi [Client Name / Hiring Team],

[If secret word or questions exist, answer here in 1 line]

Running daily operations requires an assistant who stays three steps ahead of your calendar, keeps your spreadsheets organized, and handles confidential correspondence without needing constant supervision. I would love to take those administrative tasks off your plate.

Here is how my hands-on experience aligns with your day-to-day needs:
• Executive & Administrative Support: Extensive experience managing executive schedules, appointment booking, and confidential correspondence to ensure smooth daily operations.
• Data & System Management: Advanced spreadsheet and cloud database administration experience, managing tracking logs and maintaining document confidentiality.
• Communications & Inquiries: Actively manage candidate inquiries and client communications with rapid response times and professional etiquette.

Logistics & Setup:
I work from a dedicated home workstation with high-speed fiber internet plus backup connectivity. I am available to work during [Client's preferred timezone, e.g., US EST / AU AEST] and can start immediately.

Would you be open to a quick 10-minute chat or a short sample task this week to see if we are a great fit?

Best regards,

[Candidate Full Name]
[Location]
LinkedIn: [LinkedIn URL]
Portfolio: [Portfolio URL]
```

### Blueprint 2: Recruitment Assistant / Talent Sourcer
```text
Subject: Recruitment Assistant Application - [Candidate Full Name] | [Secret Code if any] - High-Volume Sourcing Specialist

Hi [Client Name / Hiring Team],

[If secret word or questions exist, answer here in 1 line]

Finding qualified candidates and keeping your hiring pipeline moving takes relentless consistency and clean tracking. If you need someone who can source talent daily, filter out unqualified leads, and maintain clear candidate records, I am ready to step in.

Here is what I bring to your hiring workflow:
• Active Talent Sourcing: Proven experience publishing high-volume targeted job postings across professional platforms and sourcing prospective talent using LinkedIn.
• Pipeline Results: Track record of facilitating candidate screenings, coordinating interview schedules, and streamlining onboarding funnels.
• Pipeline Tracking & CRM: Maintain real-time recruitment tracking sheets, logging applicant statuses and communication history with zero drop-off.

Setup & Availability:
I have a dedicated remote setup with reliable high-speed fiber internet and backup connectivity. I am comfortable working your business hours in [Client Timezone] and can begin right away.

I'd welcome the chance to do a brief 10-minute introductory call or source 5 sample leads for you this week. Does that sound good?

Best regards,

[Candidate Full Name]
[Location]
LinkedIn: [LinkedIn URL]
```

### Blueprint 3: Data Entry / Spreadsheet & Bookkeeping Assistant
```text
Subject: Data Entry & Spreadsheet Specialist - [Candidate Full Name] | [Secret Code if any] - High-Accuracy Data Specialist

Hi [Client Name / Hiring Team],

[If secret word or questions exist, answer here in 1 line]

When handling your company's data, you cannot afford typos, broken spreadsheet formulas, or compromised confidentiality. You need someone with proven accuracy who treats your records with absolute discretion.

Here is why you can count on my data integrity:
• Certified Spreadsheet Skills: Certified spreadsheet specialist proficient in complex data organization, lookup formulas, data validation, and automated reporting.
• Precision & Accuracy: High-precision alphanumeric data entry experience, auditing and categorizing confidential transaction logs with verified zero error rates.
• High-Volume Database Admin: Administered multi-user database workflows in cloud productivity suites, ensuring strict data privacy protocols.

Setup & Availability:
Equipped with a quiet dedicated home setup, fiber internet connection, and backup power/data. Ready to support your team full-time across [Client Timezone].

Are you open to sending over a quick 5-minute data test or having a brief chat to discuss your workflow?

Best regards,

[Candidate Full Name]
[Location]
LinkedIn: [LinkedIn URL]
```

### Blueprint 4: Social Media & Content Creation VA
```text
Subject: Social Media VA Application - [Candidate Full Name] | [Secret Code if any] - Branded Content & Video Creator

Hi [Client Name / Hiring Team],

[If secret word or questions exist, answer here in 1 line]

Maintaining an engaging online presence requires consistent, branded visuals and snappy video content without draining your personal bandwidth. I can help streamline your daily content calendar and keep your feeds active.

My direct content creation experience:
• Visual Branding: Design promotional graphics, hiring banners, and social assets adhering strictly to client brand palettes and guidelines.
• Short-Form Video Editing: Produce reels, Stories, and promotional video clips complete with captions, pacing cuts, and engaging layouts.
• Content Planning & Scheduling: Experience organizing digital assets, preparing copy, and scheduling campaign deliverables under tight deadlines.

Logistics & Availability:
Ready to work immediately on [Client Timezone] with reliable high-speed fiber internet and backup connectivity.

I would love to share a few recent design samples or create a complimentary sample graphic for your brand. Are you free for a quick chat this week?

Best regards,

[Candidate Full Name]
[Location]
LinkedIn: [LinkedIn URL]
```

---

## Addressing Gaps Without Lying (The "Adjacent Bridge" Technique)

When a job description mentions a tool or software not in the candidate's verified profile:

### ❌ NEVER HALLUCINATE:
- Do NOT write: *"I have 3 years of experience managing Shopify stores and HubSpot CRM."*

### ✅ THE ADJACENT BRIDGE:
Highlight mastery of parallel workflows and certifications showing rapid tool adoption:
- **For Project Management Tools (ClickUp/Asana/Monday):**
  *"While my primary workflow tracking has been in Google Sheets and cloud workspaces, I have foundational project management training and adapt to new PM boards within an afternoon."*
- **For E-commerce / CRMs (Shopify/HubSpot):**
  *"With my strong technical background in web systems and database administration, I learn CRM interfaces very quickly and am already fluent in pipeline logic and customer records."*

---

## Output Format When Executing This Skill

When the user gives you a Job Description to evaluate and generate a proposal for, present your output cleanly in this structure:

### 1. Job Description Evaluation Summary
- **Target Role Category:** [e.g., Recruitment Assistant / General VA]
- **Fit Score:** [e.g., 88% — Strong Fit]
- **Detected Traps & Screener Codes:** [e.g., Must start with "Sunrise" | Asks for typing speed]
- **Key Client Pain Points:** [1-2 sentences on what the client actually needs solved]
- **Grounded Match Highlights:** [2-3 verified candidate facts to leverage]
- **Gaps / Cautions:** [Any missing tool or schedule constraint, and how it is handled]

### 2. High-Conversion OnlineJobs.ph Proposal
*(Formatted in clean markdown, ready to copy-paste directly into OnlineJobs.ph)*

---

## Final Quality Checklist (Before Delivery)

- [ ] **Secret Code Word included?** If requested in JD, is it placed prominently in the subject or opening line?
- [ ] **All screening questions answered?** Are specific questions answered immediately?
- [ ] **Zero AI cliché openings?** No *"I hope this email finds you well"* or *"I am thrilled to apply"*.
- [ ] **100% grounded facts?** Every metric, company name, tool, and certification matches `config/profile.yaml`.
- [ ] **Word count under 250 words?** Can the employer read the entire letter in 45 seconds?
- [ ] **Timezone and remote specs stated?** Fiber internet, backup data, and hours confirmed.
- [ ] **Frictionless CTA?** Offers a quick 10-minute chat or short test task.
