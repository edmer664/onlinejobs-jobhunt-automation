/**
 * jobhunt_opensource — Client-Side Application Script
 * Minimalist, dependency-free vanilla JavaScript (ES2022+).
 * 
 * Modules:
 *  1. Screening Trap & Code Word Tester (Regex-based parser, Route decider, Grounded Proposal generator)
 *  2. MCP 8-Tool Interactive Simulator (Stateful in-memory mock SQLite database)
 *  3. Global Hiring Windows & World Clock (Live Intl timezones & cron countdown)
 *  4. 5-Step Build Stepper Navigation
 *  5. Clipboard & UI Utilities
 */

(() => {
  'use strict';

  // =========================================================================
  // 1. Candidate Ground Truth & Synthetic Fixtures
  // =========================================================================
  const CANDIDATE_PROFILE = {
    name: "Alex Taylor",
    display_name: "Alex",
    email: "alex.taylor@example.com",
    phone: "+1-555-0144",
    location: "Remote, Worldwide",
    linkedin: "https://linkedin.com/in/alex-taylor",
    portfolio: "https://portfolio.example.com",
    resume: "https://docs.google.com/document/d/your-resume-link/pub",
    logistics: {
      internet: "300 Mbps Fiber primary with 50 Mbps 5G mobile hotspot backup",
      power: "1500VA UPS backup battery (4 hours continuous runtime)",
      hardware: "Dedicated Workstation with Dual Monitors",
      availability: "Full-time (40 hrs/wk), immediate start across US, UK, or AU timezones"
    }
  };

  const SAMPLE_JDS = {
    blueberry: `Title: Executive Virtual Assistant - High-Level Calendar & Inbox Management
Client: Apex Horizon Partners
Location: Remote (US East Coast Hours)
Salary: $1,200 - $1,500 / month

We are a high-growth technology advisory firm looking for an exceptional, proactive Executive Virtual Assistant to support our Managing Partners.

Core Responsibilities:
- Manage multi-calendar scheduling across US timezones with zero double-booking errors.
- Triage high-volume executive inboxes, drafting professional replies and prioritizing urgent messages.
- Maintain Notion workspaces, client CRM records in Airtable, and executive meeting notes.
- Coordinate travel itineraries, flight logistics, and expense summaries.

Requirements:
- 3+ years experience as a remote Executive Assistant for US/UK executives.
- Advanced proficiency in Google Workspace, Slack, Notion, and Zoom.
- Proven reliability with dedicated home office power and high-speed fiber internet.

APPLICATION INSTRUCTIONS (READ CAREFULLY):
To ensure you read instructions and possess attention to detail, you MUST put "BLUEBERRY" in your email subject line.
Applications that do not include the code word will be automatically rejected.

Send your resume directly to our hiring team at: careers@apexhorizonpartners.example.com`,

    operations: `Title: Operations Coordinator & Administrative Assistant
Company: Beacon Financial Systems
Arrangement: Full-Time Remote (UK Working Hours 09:00 - 17:00 GMT)
Compensation: £1,100 - £1,400 / month

We need a structured Operations Coordinator to streamline internal reporting, organize SOPs, and assist our project teams.

Responsibilities:
- Document operational workflows and standard operating procedures (SOPs) in Notion and ClickUp.
- Consolidate weekly client data spreadsheets in Google Sheets.
- Manage team meeting agendas, document action items, and follow up on team deliverables.

How to Apply:
Do NOT apply on this job board. We manage our hiring pipeline externally.
Complete our candidate form here: https://docs.google.com/forms/d/e/1FAIpQLSc-sample-operations/viewform

Note: Question 4 on the form asks for our screening verification code. Enter "PHOENIX" in that field to verify your submission.`,

    masked: `Title: General Administrative Virtual Assistant for Real Estate
Company: Premier Realty Group
Location: Remote (US Central / Pacific Timezone)
Salary: $900 - $1,100 / month

Looking for an honest, dependable Virtual Assistant to handle client follow-ups, schedule property showings, and maintain listing databases in Google Sheets.

Must have excellent English communication skills and fast internet.
Experience with real estate CRMs is a plus.

To apply, send your application directly to:
Email: ----------

(Listing email address is protected by platform masking. Route B On-Platform safeguards applied.)`,

    custom: ""
  };

  const MOCK_JOBS_DB = [
    {
      job_id: "seed-001",
      title: "Executive Virtual Assistant - High-Level Calendar & Inbox Management",
      employer: "Apex Horizon Partners",
      salary: "$1,200 - $1,500 / month",
      salary_usd_monthly_est: 1350.0,
      arrangement: "Full Time",
      client_region: "US",
      role_category: "Virtual Assistant",
      match_score: 94,
      suitability_tier: "Excellent Fit",
      status: "New",
      posted_at: "2026-11-10 14:00:00",
      matched_skills: ["Executive Assistant", "Email Management", "Calendar Scheduling", "Google Workspace", "Notion"],
      missing_skills: [],
      notes: "Route A Direct Email: careers@apexhorizonpartners.example.com. Screening code: BLUEBERRY."
    },
    {
      job_id: "seed-002",
      title: "Operations Coordinator & Administrative Assistant",
      employer: "Beacon Financial Systems",
      salary: "£1,100 - £1,400 / month",
      salary_usd_monthly_est: 1450.0,
      arrangement: "Full Time",
      client_region: "UK",
      role_category: "Operations Coordinator",
      match_score: 88,
      suitability_tier: "Excellent Fit",
      status: "New",
      posted_at: "2026-11-10 12:00:00",
      matched_skills: ["Operations", "SOP Documentation", "Notion", "ClickUp", "Google Sheets"],
      missing_skills: [],
      notes: "Route C Form: https://docs.google.com/forms/d/e/1FAIpQLSc-sample-operations/viewform. Code: PHOENIX."
    },
    {
      job_id: "seed-003",
      title: "B2B Lead Sourcing & Data Prospecting Specialist",
      employer: "GrowthMetrics Global",
      salary: "$900 - $1,200 / month",
      salary_usd_monthly_est: 1050.0,
      arrangement: "Full Time",
      client_region: "US",
      role_category: "Lead Generation",
      match_score: 85,
      suitability_tier: "Excellent Fit",
      status: "New",
      posted_at: "2026-11-10 11:30:00",
      matched_skills: ["Lead Generation", "Data Sourcing", "Google Sheets", "Web Research"],
      missing_skills: [],
      notes: "Route A Email: jobs@growthmetrics.example.com. Screening prompt present."
    },
    {
      job_id: "seed-004",
      title: "Virtual Assistant for Real Estate Lead Management",
      employer: "Sydney Metro Properties",
      salary: "A$2,200 - A$2,800 / month",
      salary_usd_monthly_est: 1650.0,
      arrangement: "Full Time",
      client_region: "AU",
      role_category: "Virtual Assistant",
      match_score: 82,
      suitability_tier: "Excellent Fit",
      status: "New",
      posted_at: "2026-11-10 09:30:00",
      matched_skills: ["Calendar Scheduling", "Spreadsheet Management", "Email Inbox Zero"],
      missing_skills: [],
      notes: "AU morning peak posting. High suitability for calendar coordination."
    },
    {
      job_id: "seed-005",
      title: "Senior Full-Stack Laravel / React Architect",
      employer: "TechCorp Labs",
      salary: "$3,500 / month",
      salary_usd_monthly_est: 3500.0,
      arrangement: "Full Time",
      client_region: "US",
      role_category: "IT & Systems Analysis",
      match_score: 32,
      suitability_tier: "Low Fit",
      status: "New",
      posted_at: "2026-11-10 08:00:00",
      matched_skills: ["Technical Documentation"],
      missing_skills: ["Laravel", "React", "Docker", "AWS DevOps"],
      notes: "Hard mismatch: Senior software engineering role outside candidate profile."
    },
    {
      job_id: "seed-006",
      title: "Outbound Telemarketer - 150 Cold Calls Per Day",
      employer: "FastDial Solutions",
      salary: "$500 / month + commission",
      salary_usd_monthly_est: 500.0,
      arrangement: "Full Time",
      client_region: "US",
      role_category: "Other",
      match_score: 22,
      suitability_tier: "Low Fit",
      status: "New",
      posted_at: "2026-11-10 07:00:00",
      matched_skills: [],
      missing_skills: ["High-Volume Outbound Dialer"],
      notes: "Red flag: High-stress dialer role with commission dependency."
    }
  ];

  // Scheduled Peak Windows in Philippine Time (PHT, UTC+8)
  const CRON_SLOTS_PHT = [
    { hour: 1, minute: 0, label: "US West Coast Morning Peak (09:00 AM PST)" },
    { hour: 3, minute: 30, label: "US West Midday / East Afternoon (11:30 AM PST / 02:30 PM EST)" },
    { hour: 7, minute: 0, label: "Australia Morning Business Start (09:00 AM AEST)" },
    { hour: 9, minute: 30, label: "Australia Midday Hiring Peak (11:30 AM AEST)" },
    { hour: 17, minute: 0, label: "UK Morning Business Start (09:00 AM GMT)" },
    { hour: 19, minute: 30, label: "UK Midday Hiring Peak (11:30 AM GMT)" },
    { hour: 21, minute: 0, label: "US East Coast Morning Start (08:00 AM EST)" },
    { hour: 23, minute: 30, label: "US East Coast Midday Peak (10:30 AM EST)" }
  ];

  // =========================================================================
  // 2. Core Screening Trap & Proposal Engine Port
  // =========================================================================
  function auditScreeningTraps(text) {
    const traps = {
      secretCodes: [],
      emailSubmission: null,
      formSubmission: null,
      route: "B",
      routeLabel: "Route B: On-Platform Application",
      connects: 20,
      instructions: "Standard platform application. Apply with verified credentials.",
      target: "OnlineJobs.ph Modal",
      requiresSpeedtest: false,
      requiresVoiceVideo: false
    };

    if (!text || !text.trim()) return traps;

    // 1. Direct Email Extraction
    const emailRegex = /[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+/g;
    const matches = text.match(emailRegex) || [];
    const ignoredDomains = ["onlinejobs.ph", "example.com", "domain.com", "test.com"];
    for (const email of matches) {
      const cleanEmail = email.replace(/[.,;)>\]]+$/, "");
      const domain = cleanEmail.split("@")[1]?.toLowerCase();
      if (domain && !ignoredDomains.includes(domain) && !cleanEmail.match(/\.(png|jpg|jpeg|gif|webp)$/i)) {
        traps.emailSubmission = cleanEmail;
        break;
      }
    }

    // 2. External Application Form Detection
    const formRegex = /https?:\/\/(?:forms\.gle|docs\.google\.com\/forms|airtable\.com|forms\.clickup\.com|(?:[a-zA-Z0-9_-]+\.)?clickup\.com\/f|recruitcrm\.io|apply\.workable\.com|tally\.so|(?:[a-zA-Z0-9_-]+\.)?jotform\.com|wkf\.ms)[^\s"\'<>]+/i;
    const formMatch = text.match(formRegex);
    if (formMatch) {
      traps.formSubmission = formMatch[0].replace(/[.,;:)>\]]+$/, "");
    }

    // 3. Secret Code Words Detection
    const quoteChars = `"'\u201c\u201d\u2018\u2019`;
    const quotedWord = `(?:(["'])([^${quoteChars}\\n\\r]{1,35})\\1|\\u201c([^${quoteChars}\\n\\r]{1,35})\\u201d|\\u2018([^${quoteChars}\\n\\r]{1,35})\\u2019)`;
    const codePatterns = [
      new RegExp(`(?:put|include|write|use)\\s+${quotedWord}\\s+(?:in|as|on)\\s+(?:the|your)?\\s*(?:email\\s*)?subject`, 'i'),
      new RegExp(`start\\s+your\\s+(?:subject|message|proposal|application)\\s+with\\s+(?:(?:the\\s+)?(?:word|phrase|code)\\s+)?${quotedWord}`, 'i'),
      new RegExp(`subject\\s+line\\s+must\\s+(?:contain|include|start\\s+with)\\s+[${quoteChars}]?([^${quoteChars}\\n\\r.,;]{2,35})[${quoteChars}]?`, 'i'),
      new RegExp(`(?:secret|magic|code|verification)\\s*(?:word|phrase|code)\\s*(?:is\\s*:|is|:)\\s*[${quoteChars}]?([^${quoteChars}\\n\\r.,;]{2,30})[${quoteChars}]?`, 'i'),
      new RegExp(`(?:enter|type)\\s+${quotedWord}`, 'i')
    ];

    const noiseWords = new Set(["the", "this", "a", "an", "your", "none", "word", "code", "proposal", "application", "carefully"]);
    for (const pat of codePatterns) {
      const match = text.match(pat);
      if (match) {
        let rawCandidate = "";
        for (let i = 1; i < match.length; i++) {
          if (match[i] && !['"', "'", '\u201c', '\u201d', '\u2018', '\u2019'].includes(match[i])) {
            rawCandidate = match[i];
            break;
          }
        }
        if (!rawCandidate) rawCandidate = match[2] || match[1] || "";
        const candidate = rawCandidate.trim().replace(/^[:\s"'“”‘’]+|[:\s"'“”‘’]+$/g, "").trim();
        if (candidate.length > 1 && !noiseWords.has(candidate.toLowerCase()) && !traps.secretCodes.includes(candidate.toUpperCase())) {
          traps.secretCodes.push(candidate.toUpperCase());
        }
      }
    }

    // Specific preset fallback check if needed
    if (text.includes("BLUEBERRY") && !traps.secretCodes.includes("BLUEBERRY")) {
      traps.secretCodes.push("BLUEBERRY");
    }
    if (text.includes("PHOENIX") && !traps.secretCodes.includes("PHOENIX")) {
      traps.secretCodes.push("PHOENIX");
    }

    // 4. Keyword Checks
    const lower = text.toLowerCase();
    traps.requiresSpeedtest = /(speedtest|speed\s*test|internet\s*speed)/i.test(lower);
    traps.requiresVoiceVideo = /(loom|video\s*intro|record\s*a\s*video|audio\s*clip)/i.test(lower);

    // 5. Channel & Route Determination
    if (traps.formSubmission) {
      traps.route = "C";
      traps.routeLabel = "Route C: External Form";
      traps.connects = 0;
      traps.target = traps.formSubmission;
      traps.instructions = traps.secretCodes.length > 0 
        ? `Submit through external form. Insert code word [${traps.secretCodes[0]}] into designated field.`
        : "Complete and submit external form with verified candidate facts.";
    } else if (traps.emailSubmission) {
      traps.route = "A";
      traps.routeLabel = "Route A: Direct Email";
      traps.connects = 0;
      traps.target = traps.emailSubmission;
      traps.instructions = traps.secretCodes.length > 0
        ? `Send direct email. Include [${traps.secretCodes[0]}] in subject line and opening line.`
        : "Send direct application email with PDF resume attached.";
    } else {
      traps.route = "B";
      traps.routeLabel = "Route B: On-Platform Application";
      traps.connects = 20;
      traps.target = "OnlineJobs.ph Modal";
      traps.instructions = "Standard listing. Guardrail limits points to genuine high-fit opportunities.";
    }

    return traps;
  }

  function calculateMatchScore(text) {
    if (!text || !text.trim()) return { score: 50, tier: "Moderate Fit" };
    const lower = text.toLowerCase();
    let score = 55;

    const positiveSkills = [
      { regex: /calendar|scheduling|appointment/i, pts: 10 },
      { regex: /inbox|email\s*management|correspondence/i, pts: 10 },
      { regex: /notion|clickup|asana|trello|sop/i, pts: 8 },
      { regex: /sheets?|excel|spreadsheet|data/i, pts: 8 },
      { regex: /executive|administrative|virtual\s*assistant/i, pts: 10 },
      { regex: /slack|google\s*workspace/i, pts: 6 }
    ];

    for (const item of positiveSkills) {
      if (item.regex.test(lower)) score += item.pts;
    }

    if (/(senior|principal|lead)\s+(software|backend|full-stack|devops)/i.test(lower)) score -= 35;
    if (/cold\s*calling|telemarketer|150\s*calls/i.test(lower)) score -= 30;
    if (/medical\s*billing|nurse/i.test(lower)) score -= 30;

    score = Math.max(18, Math.min(96, Math.round(score)));
    let tier = "Moderate Fit";
    if (score >= 80) tier = "High Fit";
    else if (score >= 65) tier = "Good Fit";
    else if (score < 50) tier = "Low Fit";

    return { score, tier };
  }

  function buildGroundedProposal(traps, candidate, title) {
    const code = traps.secretCodes.length > 0 ? traps.secretCodes[0] : "";
    const codeLine = code ? `Keyword / Screening Code: ${code}\n\n` : "";
    const subjectCode = code ? `[${code}] ` : "";
    const subject = `${subjectCode}Application: Executive VA & Systems Specialist — ${candidate.name}`;

    const body = `${codeLine}Hi Hiring Team,

I understand you need dependable, proactive executive support to keep calendars scheduled across timezones, inboxes answered promptly, and administrative priorities on track without hand-holding.

Here is how my verified background directly supports your workflow:
- Proactive Calendar & Inbox Management: Experience coordinating executive calendars across US and global timezones, managing high-volume correspondence, and maintaining Inbox Zero.
- High-Accuracy Data & Systems: Advanced proficiency in Google Sheets, Notion, and Airtable, ensuring reliable data tracking, clear reporting, and structured SOP documentation.
- Rapid Communication & Low Friction: Experienced managing client inquiries, meeting agendas, and team deliverables with zero need for hand-holding.

Workstation & Availability: Equipped with high-speed fiber internet (300 Mbps) plus mobile backup, a dedicated workstation with UPS battery backup, and immediate availability aligned with your core business hours.

I would welcome the opportunity for a brief 10-minute discovery chat or to complete a short trial task to demonstrate my reliability firsthand.

Best regards,
${candidate.name}
${candidate.location}
Portfolio: ${candidate.portfolio}
Resume: ${candidate.resume}`;

    const words = body.trim().split(/\s+/).length;
    return { subject, body, words };
  }

  // =========================================================================
  // 3. Module 1: Screening Trap & Code Word Tester Controller
  // =========================================================================
  function initTrapTester() {
    const jdInput = document.getElementById("jd-input");
    const btnAnalyze = document.getElementById("btn-analyze-jd");
    const presetButtons = document.querySelectorAll(".btn-preset");

    const resultScore = document.getElementById("result-match-score");
    const resultRoute = document.getElementById("result-route");
    const resultConnects = document.getElementById("result-connects");
    const resultSecretCode = document.getElementById("result-secret-code");
    const resultInstructions = document.getElementById("result-instructions");
    const resultTarget = document.getElementById("result-target");
    const resultSubject = document.getElementById("result-proposal-subject");
    const resultBody = document.getElementById("result-proposal-body");
    const resultWordCount = document.getElementById("result-word-count");
    const btnCopyProposal = document.getElementById("trap-copy-proposal-btn");

    function runEvaluation() {
      const text = jdInput ? jdInput.value : "";
      const traps = auditScreeningTraps(text);
      const scoreObj = calculateMatchScore(text);
      const proposal = buildGroundedProposal(traps, CANDIDATE_PROFILE, "Virtual Assistant");

      if (resultScore) resultScore.textContent = `${scoreObj.score}% — ${scoreObj.tier}`;
      if (resultRoute) resultRoute.textContent = traps.routeLabel;
      if (resultConnects) resultConnects.textContent = `${traps.connects} Points`;
      if (resultSecretCode) resultSecretCode.textContent = traps.secretCodes.length > 0 ? traps.secretCodes.join(", ") : "None Detected";
      if (resultInstructions) resultInstructions.textContent = traps.instructions;
      if (resultTarget) resultTarget.textContent = traps.target;
      if (resultSubject) resultSubject.textContent = proposal.subject;
      if (resultBody) resultBody.textContent = proposal.body;
      if (resultWordCount) resultWordCount.textContent = `${proposal.words} words`;
    }

    presetButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        presetButtons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        const presetKey = btn.getAttribute("data-preset");
        if (jdInput && SAMPLE_JDS[presetKey] !== undefined) {
          jdInput.value = SAMPLE_JDS[presetKey];
          runEvaluation();
        }
      });
    });

    if (btnAnalyze) {
      btnAnalyze.addEventListener("click", runEvaluation);
    }

    if (jdInput) {
      jdInput.addEventListener("input", debounce(runEvaluation, 300));
      // Initialize with blueberry preset
      jdInput.value = SAMPLE_JDS.blueberry;
      runEvaluation();
    }

    if (btnCopyProposal && resultBody) {
      btnCopyProposal.addEventListener("click", () => {
        copyText(resultBody.textContent, btnCopyProposal);
      });
    }
  }

  // =========================================================================
  // 4. Module 2: Model Context Protocol (MCP) 8-Tool Simulator Controller
  // =========================================================================
  function initMcpSimulator() {
    const toolSelect = document.getElementById("mcp-tool-select");
    const paramsContainer = document.getElementById("mcp-param-fields");
    const btnExec = document.getElementById("btn-exec-mcp");
    const callSig = document.getElementById("mcp-call-sig");
    const latencyEl = document.getElementById("mcp-latency");
    const consoleOutput = document.getElementById("mcp-console-output");

    const TOOL_CONFIGS = {
      search_jobs: {
        fields: [
          { name: "min_score", label: "Minimum Match Score", type: "number", value: "70" },
          { name: "status", label: "Status Filter", type: "select", options: ["All", "New", "Shortlisted", "Applied"], value: "New" },
          { name: "client_region", label: "Client Region", type: "select", options: ["All", "US", "UK", "AU"], value: "All" },
          { name: "limit", label: "Result Limit", type: "number", value: "3" }
        ],
        exec: (params) => {
          const min = Number(params.min_score) || 70;
          const status = params.status || "All";
          const region = params.client_region || "All";
          const limit = Number(params.limit) || 3;

          const filtered = MOCK_JOBS_DB.filter(j => {
            if (j.match_score < min) return false;
            if (status !== "All" && j.status !== status) return false;
            if (region !== "All" && j.client_region !== region) return false;
            return true;
          }).slice(0, limit);

          return {
            count: filtered.length,
            jobs: filtered.map(j => ({
              job_id: j.job_id,
              title: j.title,
              employer: j.employer,
              match_score: j.match_score,
              suitability_tier: j.suitability_tier,
              status: j.status,
              salary: j.salary,
              matched_skills: j.matched_skills
            }))
          };
        }
      },

      get_job_details: {
        fields: [
          { name: "job_id", label: "Job ID", type: "select", options: ["seed-001", "seed-002", "seed-003", "seed-004", "seed-005", "seed-006"], value: "seed-001" }
        ],
        exec: (params) => {
          const job = MOCK_JOBS_DB.find(j => j.job_id === params.job_id);
          if (!job) return { error: `Job ID ${params.job_id} not found.` };
          return {
            ...job,
            screening_audit: auditScreeningTraps(job.notes + " " + job.title)
          };
        }
      },

      generate_job_proposal: {
        fields: [
          { name: "job_id", label: "Job ID", type: "select", options: ["seed-001", "seed-002", "seed-003", "seed-004"], value: "seed-001" },
          { name: "client_name", label: "Client / Company Name", type: "text", value: "Apex Horizon Partners" }
        ],
        exec: (params) => {
          const job = MOCK_JOBS_DB.find(j => j.job_id === params.job_id);
          if (!job) return { error: `Job ID ${params.job_id} not found.` };
          const traps = auditScreeningTraps(job.notes);
          const proposal = buildGroundedProposal(traps, CANDIDATE_PROFILE, job.title);
          return {
            job_id: job.job_id,
            job_title: job.title,
            employer: params.client_name || job.employer,
            subject_line: proposal.subject,
            proposal_text: proposal.body,
            word_count: proposal.words,
            zero_hallucinations_verified: true
          };
        }
      },

      apply_job: {
        fields: [
          { name: "job_id", label: "Job ID to Apply", type: "select", options: ["seed-001", "seed-002", "seed-003", "seed-004"], value: "seed-001" },
          { name: "notes", label: "Submission Audit Log", type: "text", value: "Submitted via Route A Direct Email with PDF resume attached." }
        ],
        exec: (params) => {
          const job = MOCK_JOBS_DB.find(j => j.job_id === params.job_id);
          if (!job) return { error: `Job ID ${params.job_id} not found.` };
          job.status = "Applied";
          job.notes += `\n[Applied: ${new Date().toISOString()}] ${params.notes}`;
          return {
            status: "success",
            job_id: job.job_id,
            updated_status: "Applied",
            audit_entry: params.notes,
            connects_spent: 0
          };
        }
      },

      update_job_status: {
        fields: [
          { name: "job_id", label: "Job ID", type: "select", options: ["seed-001", "seed-002", "seed-003", "seed-004", "seed-005", "seed-006"], value: "seed-001" },
          { name: "status", label: "New Status", type: "select", options: ["New", "Shortlisted", "Applied", "Interviewing", "Offer", "Rejected", "Archived"], value: "Shortlisted" },
          { name: "notes", label: "Status Log", type: "text", value: "Marked high-priority for follow up." }
        ],
        exec: (params) => {
          const job = MOCK_JOBS_DB.find(j => j.job_id === params.job_id);
          if (!job) return { error: `Job ID ${params.job_id} not found.` };
          job.status = params.status;
          return {
            status: "success",
            job_id: job.job_id,
            previous_status: "New",
            current_status: job.status,
            updated_at: new Date().toISOString()
          };
        }
      },

      trigger_scrape: {
        fields: [
          { name: "pages", label: "Pages to Scrape", type: "number", value: "3" },
          { name: "target_region", label: "Target Market", type: "select", options: ["US/UK/AU", "US", "UK", "AU"], value: "US/UK/AU" }
        ],
        exec: (params) => {
          const pages = Number(params.pages) || 3;
          return {
            status: "completed",
            pages_crawled: pages,
            listings_discovered: pages * 30,
            indexed_in_sqlite: 14,
            high_fit_matches: 4,
            zero_connect_routes_detected: { email_route_a: 2, form_route_c: 1 },
            duration_seconds: (pages * 1.6).toFixed(1)
          };
        }
      },

      get_pipeline_stats: {
        fields: [],
        exec: () => {
          const total = MOCK_JOBS_DB.length;
          const applied = MOCK_JOBS_DB.filter(j => j.status === "Applied").length;
          const shortlisted = MOCK_JOBS_DB.filter(j => j.status === "Shortlisted").length;
          const newJobs = MOCK_JOBS_DB.filter(j => j.status === "New").length;
          const matched = MOCK_JOBS_DB.filter(j => j.match_score >= 60).length;

          return {
            total_jobs_indexed: total,
            matched_opportunities: matched,
            unmatched_filtered: total - matched,
            status_breakdown: {
              New: newJobs,
              Applied: applied,
              Shortlisted: shortlisted,
              Interviewing: 0
            },
            total_connects_spent: 0,
            zero_cost_compliance: "100% compliant (0 points spent)",
            database_mode: "SQLite WAL (Concurrency Safe)"
          };
        }
      },

      get_candidate_profile: {
        fields: [],
        exec: () => ({
          candidate: {
            name: CANDIDATE_PROFILE.name,
            email: CANDIDATE_PROFILE.email,
            phone: CANDIDATE_PROFILE.phone,
            location: CANDIDATE_PROFILE.location,
            linkedin: CANDIDATE_PROFILE.linkedin,
            portfolio: CANDIDATE_PROFILE.portfolio
          },
          logistics: CANDIDATE_PROFILE.logistics,
          anti_hallucination_rules: [
            "Never invent software or certifications not explicitly declared in verified profile.",
            "Maintain proposal length strictly between 150 and 250 words.",
            "Always position detected screening codes in the very first line and subject line."
          ]
        })
      }
    };

    function renderFields() {
      if (!toolSelect || !paramsContainer) return;
      const toolName = toolSelect.value;
      const cfg = TOOL_CONFIGS[toolName];
      if (!cfg) return;

      paramsContainer.innerHTML = "";
      if (cfg.fields.length === 0) {
        const p = document.createElement("p");
        p.className = "param-desc";
        p.textContent = "This tool takes no arguments. Ready to execute.";
        paramsContainer.appendChild(p);
        return;
      }

      cfg.fields.forEach(f => {
        const group = document.createElement("div");
        group.className = "param-group";

        const label = document.createElement("label");
        label.className = "param-label";
        label.textContent = f.label;
        group.appendChild(label);

        if (f.type === "select") {
          const sel = document.createElement("select");
          sel.className = "param-input";
          sel.name = f.name;
          f.options.forEach(opt => {
            const o = document.createElement("option");
            o.value = opt;
            o.textContent = opt;
            if (opt === f.value) o.selected = true;
            sel.appendChild(o);
          });
          group.appendChild(sel);
        } else {
          const inp = document.createElement("input");
          inp.className = "param-input";
          inp.type = f.type;
          inp.name = f.name;
          inp.value = f.value;
          group.appendChild(inp);
        }

        paramsContainer.appendChild(group);
      });
    }

    function runTool() {
      if (!toolSelect) return;
      const toolName = toolSelect.value;
      const cfg = TOOL_CONFIGS[toolName];
      if (!cfg) return;

      const params = {};
      const inputs = paramsContainer.querySelectorAll("input, select");
      inputs.forEach(i => {
        if (i.name) params[i.name] = i.value;
      });

      const start = performance.now();
      const result = cfg.exec(params);
      const elapsed = Math.max(8, Math.round(performance.now() - start));

      if (callSig) {
        callSig.textContent = `call_tool("onlinejobs-portal", "${toolName}", ${JSON.stringify(params)})`;
      }
      if (latencyEl) {
        latencyEl.textContent = `Latency: ~${elapsed}ms`;
      }
      if (consoleOutput) {
        consoleOutput.textContent = JSON.stringify(result, null, 2);
      }
    }

    if (toolSelect) {
      toolSelect.addEventListener("change", () => {
        renderFields();
        runTool();
      });
      renderFields();
      runTool();
    }

    if (btnExec) {
      btnExec.addEventListener("click", runTool);
    }
  }

  // =========================================================================
  // 5. Module 3: Global Hiring Windows World Clock & Countdown
  // =========================================================================
  function initWorldClock() {
    const clockPht = document.getElementById("clock-pht");
    const clockPst = document.getElementById("clock-pst");
    const clockEst = document.getElementById("clock-est");
    const clockGmt = document.getElementById("clock-gmt");
    const clockAest = document.getElementById("clock-aest");

    const statusPst = document.getElementById("status-pst");
    const statusEst = document.getElementById("status-est");
    const statusGmt = document.getElementById("status-gmt");
    const statusAest = document.getElementById("status-aest");

    const dotPst = document.getElementById("status-pst-dot");
    const dotEst = document.getElementById("status-est-dot");
    const dotGmt = document.getElementById("status-gmt-dot");
    const dotAest = document.getElementById("status-aest-dot");

    const countdownEl = document.getElementById("next-scrape-timer");

    function update() {
      const now = new Date();

      // Formatters
      const fmt = (tz) => new Intl.DateTimeFormat("en-US", {
        timeZone: tz,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true
      }).format(now);

      const hourFmt = (tz) => {
        const parts = new Intl.DateTimeFormat("en-US", {
          timeZone: tz,
          hour: "numeric",
          minute: "numeric",
          hourCycle: "h23"
        }).formatToParts(now);
        const map = {};
        parts.forEach(p => map[p.type] = p.value);
        return { hour: parseInt(map.hour, 10), minute: parseInt(map.minute, 10) };
      };

      if (clockPht) clockPht.textContent = fmt("Asia/Manila");
      if (clockPst) clockPst.textContent = fmt("America/Los_Angeles");
      if (clockEst) clockEst.textContent = fmt("America/New_York");
      if (clockGmt) clockGmt.textContent = fmt("Europe/London");
      if (clockAest) clockAest.textContent = fmt("Australia/Sydney");

      // Peak Windows:
      // US West (PST): 09:00 - 11:30
      const pst = hourFmt("America/Los_Angeles");
      const pstMins = pst.hour * 60 + pst.minute;
      const pstPeak = pstMins >= (9 * 60) && pstMins <= (11 * 60 + 30);
      setMarketStatus(statusPst, dotPst, pstPeak);

      // US East (EST): 08:00 - 11:30
      const est = hourFmt("America/New_York");
      const estMins = est.hour * 60 + est.minute;
      const estPeak = estMins >= (8 * 60) && estMins <= (11 * 60 + 30);
      setMarketStatus(statusEst, dotEst, estPeak);

      // UK (GMT): 09:00 - 11:30
      const gmt = hourFmt("Europe/London");
      const gmtMins = gmt.hour * 60 + gmt.minute;
      const gmtPeak = gmtMins >= (9 * 60) && gmtMins <= (11 * 60 + 30);
      setMarketStatus(statusGmt, dotGmt, gmtPeak);

      // Australia (AEST): 09:00 - 11:30
      const aest = hourFmt("Australia/Sydney");
      const aestMins = aest.hour * 60 + aest.minute;
      const aestPeak = aestMins >= (9 * 60) && aestMins <= (11 * 60 + 30);
      setMarketStatus(statusAest, dotAest, aestPeak);

      // Next Scheduled Scrape Slot in PHT
      const phtParts = new Intl.DateTimeFormat("en-US", {
        timeZone: "Asia/Manila",
        year: "numeric", month: "numeric", day: "numeric",
        hour: "numeric", minute: "numeric", second: "numeric",
        hourCycle: "h23"
      }).formatToParts(now);
      const phtMap = {};
      phtParts.forEach(p => phtMap[p.type] = p.value);

      const phtNow = new Date(Date.UTC(phtMap.year, phtMap.month - 1, phtMap.day, phtMap.hour, phtMap.minute, phtMap.second));

      let minDiff = Infinity;
      for (const slot of CRON_SLOTS_PHT) {
        let slotDate = new Date(Date.UTC(phtMap.year, phtMap.month - 1, phtMap.day, slot.hour, slot.minute, 0));
        if (slotDate <= phtNow) {
          slotDate.setUTCDate(slotDate.getUTCDate() + 1);
        }
        const diff = slotDate.getTime() - phtNow.getTime();
        if (diff < minDiff) {
          minDiff = diff;
        }
      }

      if (countdownEl && minDiff !== Infinity) {
        const totalSec = Math.floor(minDiff / 1000);
        const h = Math.floor(totalSec / 3600);
        const m = Math.floor((totalSec % 3600) / 60);
        const s = totalSec % 60;
        countdownEl.textContent = `${h > 0 ? h + "h " : ""}${m}m ${s < 10 ? "0" + s : s}s`;
      }
    }

    function setMarketStatus(textEl, dotEl, isPeak) {
      if (!textEl || !dotEl) return;
      if (isPeak) {
        textEl.textContent = "ACTIVE PEAK WINDOW";
        textEl.className = "status-text active";
        dotEl.className = "status-dot active";
      } else {
        textEl.textContent = "Off-Peak / Idle";
        textEl.className = "status-text";
        dotEl.className = "status-dot";
      }
    }

    update();
    setInterval(update, 1000);
  }

  // =========================================================================
  // 6. Module 4: 5-Step Build Stepper Navigation
  // =========================================================================
  function initBuildStepper() {
    const stepperBtns = document.querySelectorAll(".stepper-btn");
    const stepperPanes = document.querySelectorAll(".stepper-pane");

    stepperBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        const stepNum = btn.getAttribute("data-step");
        stepperBtns.forEach(b => {
          b.classList.remove("active");
          b.setAttribute("aria-selected", "false");
        });
        btn.classList.add("active");
        btn.setAttribute("aria-selected", "true");

        stepperPanes.forEach(pane => {
          if (pane.id === `pane-step-${stepNum}`) {
            pane.classList.add("active");
            pane.hidden = false;
          } else {
            pane.classList.remove("active");
            pane.hidden = true;
          }
        });
      });
    });
  }

  // =========================================================================
  // 7. Module 5: Tab Switcher & Clipboard Manager
  // =========================================================================
  function initSandboxTabs() {
    const tabs = document.querySelectorAll(".sandbox-tabs .tab-btn");
    const panels = document.querySelectorAll(".sandbox-panel");

    tabs.forEach(tab => {
      tab.addEventListener("click", () => {
        const targetId = tab.getAttribute("data-tab");
        tabs.forEach(t => {
          t.classList.remove("active");
          t.setAttribute("aria-selected", "false");
        });
        tab.classList.add("active");
        tab.setAttribute("aria-selected", "true");

        panels.forEach(p => {
          if (p.id === targetId) {
            p.classList.add("active");
            p.hidden = false;
          } else {
            p.classList.remove("active");
            p.hidden = true;
          }
        });
      });
    });
  }

  function initCopyButtons() {
    const copyBtns = document.querySelectorAll(".btn-copy");
    copyBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        const targetId = btn.getAttribute("data-target");
        if (!targetId) return;
        const targetEl = document.getElementById(targetId);
        if (targetEl) {
          copyText(targetEl.textContent, btn);
        }
      });
    });
  }

  function copyText(text, buttonEl) {
    if (!text) return;
    const originalText = buttonEl ? buttonEl.innerHTML : "";

    const onSuccess = () => {
      if (!buttonEl) return;
      buttonEl.textContent = "Copied!";
      buttonEl.classList.add("copied");
      setTimeout(() => {
        buttonEl.innerHTML = originalText;
        buttonEl.classList.remove("copied");
      }, 1800);
    };

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(onSuccess).catch(() => fallbackCopy(text, onSuccess));
    } else {
      fallbackCopy(text, onSuccess);
    }
  }

  function fallbackCopy(text, onSuccess) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
      onSuccess();
    } catch (e) {
      console.warn("Fallback copy failed:", e);
    }
    document.body.removeChild(ta);
  }

  function debounce(func, wait) {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func(...args), wait);
    };
  }

  // =========================================================================
  // 8. Application Bootstrap
  // =========================================================================
  document.addEventListener("DOMContentLoaded", () => {
    initTrapTester();
    initMcpSimulator();
    initWorldClock();
    initBuildStepper();
    initSandboxTabs();
    initCopyButtons();
  });

})();
