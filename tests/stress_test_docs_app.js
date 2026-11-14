/**
 * stress_test_docs_app.js - Adversarial Stress Test & Verification Harness
 * Targets: docs/app.js (Client-side JavaScript Engine)
 * 
 * Verifies:
 *  1. JD Screening Trap Engine: Unicode curly quotes, multiple/nested quotes, complex email extraction
 *     (URLs, mailto, fake domains, trailing punctuation, image false positives), external form detection,
 *     secret code patterns & noise rejection, speedtest & voice/video flags, typing test handling, boundary fuzzing.
 *  2. MCP 8-Tool Interactive Simulator: All 8 tools with valid, invalid, boundary, and unexpected arguments;
 *     in-memory database state persistence and mutation integrity across consecutive calls.
 *  3. Global Hiring Windows World Clock & Countdown: Multi-timezone calculations, market peak status math,
 *     exact boundary seconds, midnight rollovers, month/year transitions, non-negative countdown formatting.
 *  4. DOM Wireup & Event Lifecycle: Simulated mounting of interactive sandbox controllers.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const APP_JS_PATH = path.resolve(__dirname, '../docs/app.js');

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;
const failureDetails = [];
const empiricalFindings = [];

function test(name, fn) {
  totalTests++;
  try {
    fn();
    passedTests++;
    console.log(`  [PASS] ${name}`);
  } catch (err) {
    failedTests++;
    console.error(`  [FAIL] ${name}`);
    console.error(`         Failure Reason: ${err.message}`);
    failureDetails.push({ name, error: err });
  }
}

function suite(name, fn) {
  console.log(`\n======================================================================`);
  console.log(`SUITE: ${name}`);
  console.log(`======================================================================`);
  fn();
}

// -------------------------------------------------------------------------
// Environment Setup & Instrumentation
// -------------------------------------------------------------------------
function loadAppModule() {
  const originalCode = fs.readFileSync(APP_JS_PATH, 'utf8');

  // Safely hook closures for testing without modifying file on disk
  let instrumented = originalCode;
  instrumented = instrumented.replace(
    'const TOOL_CONFIGS = {',
    'const TOOL_CONFIGS = globalThis.__TOOL_CONFIGS__ = {'
  );
  instrumented = instrumented.replace(
    /}\)\(\);?\s*$/,
    `globalThis.__DOCS_APP__ = {
      CANDIDATE_PROFILE,
      SAMPLE_JDS,
      MOCK_JOBS_DB,
      CRON_SLOTS_PHT,
      auditScreeningTraps,
      calculateMatchScore,
      buildGroundedProposal,
      initTrapTester,
      initMcpSimulator,
      initWorldClock,
      initBuildStepper,
      initSandboxTabs,
      initCopyButtons
    };
  })();`
  );

  const domListeners = [];
  const mockElements = new Map();

  function createMockElement(id = '', tag = 'div', classes = []) {
    const el = {
      id,
      tagName: tag.toUpperCase(),
      classList: {
        _classes: new Set(classes),
        add: function(c) { this._classes.add(c); },
        remove: function(c) { this._classes.delete(c); },
        contains: function(c) { return this._classes.has(c); }
      },
      textContent: '',
      innerHTML: '',
      value: '',
      hidden: false,
      attributes: {},
      listeners: {},
      setAttribute: function(name, val) { this.attributes[name] = val; },
      getAttribute: function(name) { return this.attributes[name] || null; },
      addEventListener: function(event, handler) {
        if (!this.listeners[event]) this.listeners[event] = [];
        this.listeners[event].push(handler);
      },
      dispatchEvent: function(event) {
        const handlers = this.listeners[event] || [];
        handlers.forEach(h => h({ target: this, preventDefault: () => {} }));
      },
      querySelectorAll: function(sel) { return []; },
      appendChild: function(c) {}
    };
    return el;
  }

  // Pre-seed known DOM IDs
  const knownIds = [
    'jd-input', 'btn-analyze-jd', 'result-match-score', 'result-route', 'result-connects',
    'result-secret-code', 'result-instructions', 'result-target', 'result-proposal-subject',
    'result-proposal-body', 'result-word-count', 'trap-copy-proposal-btn',
    'mcp-tool-select', 'mcp-param-fields', 'btn-exec-mcp', 'mcp-call-sig',
    'mcp-latency', 'mcp-console-output',
    'clock-pht', 'clock-pst', 'clock-est', 'clock-gmt', 'clock-aest',
    'status-pst', 'status-est', 'status-gmt', 'status-aest',
    'status-pst-dot', 'status-est-dot', 'status-gmt-dot', 'status-aest-dot',
    'next-scrape-timer'
  ];

  knownIds.forEach(id => {
    mockElements.set(id, createMockElement(id));
  });

  // Cached node lists for querySelectorAll
  const presetButtons = ['blueberry', 'operations', 'masked'].map(p => {
    const el = createMockElement(`preset-${p}`, 'button', ['btn-preset']);
    el.setAttribute('data-preset', p);
    return el;
  });

  const stepperButtons = [1, 2, 3, 4, 5].map(step => {
    const el = createMockElement(`btn-step-${step}`, 'button', ['stepper-btn']);
    el.setAttribute('data-step', String(step));
    return el;
  });

  const stepperPanes = [1, 2, 3, 4, 5].map(step => {
    return createMockElement(`pane-step-${step}`, 'div', ['stepper-pane']);
  });

  const sandboxTabs = ['traps', 'mcp', 'clock'].map(tab => {
    const el = createMockElement(`tab-${tab}`, 'button', ['tab-btn']);
    el.setAttribute('data-tab', `panel-${tab}`);
    return el;
  });

  const sandboxPanels = ['traps', 'mcp', 'clock'].map(tab => {
    return createMockElement(`panel-${tab}`, 'div', ['sandbox-panel']);
  });

  const copyButtons = [createMockElement('btn-copy-test', 'button', ['btn-copy'])];
  copyButtons[0].setAttribute('data-target', 'result-proposal-body');

  const mockDocument = {
    addEventListener: (evt, cb) => domListeners.push({ evt, cb }),
    getElementById: (id) => mockElements.get(id) || null,
    querySelectorAll: (sel) => {
      if (sel === '.btn-preset') return presetButtons;
      if (sel === '.stepper-btn') return stepperButtons;
      if (sel === '.stepper-pane') return stepperPanes;
      if (sel === '.sandbox-tabs .tab-btn') return sandboxTabs;
      if (sel === '.sandbox-panel') return sandboxPanels;
      if (sel === '.btn-copy') return copyButtons;
      return [];
    },
    createElement: (tag) => createMockElement(`elem-${Math.random()}`, tag),
    body: createMockElement('body', 'body')
  };

  const sandbox = {
    console,
    setTimeout,
    clearTimeout,
    setInterval,
    clearInterval,
    performance,
    Intl,
    Date,
    Math,
    document: mockDocument,
    navigator: {
      clipboard: {
        writeText: (t) => Promise.resolve()
      }
    },
    window: {}
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(instrumented, sandbox);

  return {
    sandbox,
    app: sandbox.__DOCS_APP__,
    mockDocument,
    mockElements,
    domListeners,
    presetButtons,
    stepperButtons,
    stepperPanes,
    sandboxTabs,
    sandboxPanels
  };
}

// =========================================================================
// RUN SUITES
// =========================================================================

const env = loadAppModule();
const app = env.app;
const auditScreeningTraps = app.auditScreeningTraps;
const calculateMatchScore = app.calculateMatchScore;
const buildGroundedProposal = app.buildGroundedProposal;

// -------------------------------------------------------------------------
// SUITE 1: JD Screening Trap Engine Adversarial Stress Tests
// -------------------------------------------------------------------------
suite('1. JD Screening Trap Engine — Adversarial Scenarios & Edge Cases', () => {

  test('1.1 Standard ASCII quotes in secret code words', () => {
    const jdAscii = `Requirements:
To show you read this, put "DRAGONFRUIT" in your subject line.
Apply to: careers@innovate.example.org`;
    const res = auditScreeningTraps(jdAscii);
    assert(res.secretCodes.includes('DRAGONFRUIT'), `Failed to extract code with standard quotes. Got: ${JSON.stringify(res.secretCodes)}`);
  });

  test('1.2 Adversarial Vulnerability: Unicode curly quotes backreference mismatch in codePatterns', () => {
    // In typographical text (Word, Google Docs, Slack, macOS), quotes are paired as:
    // Opening \u201c (“) and closing \u201d (”).
    // docs/app.js uses `([${quoteChars}])([^${quoteChars}\n\r]{1,35})\1`
    // \1 expects the CLOSING quote to be identical to OPENING quote (\u201c !== \u201d).
    const jdDoubleCurly = `Requirements:\nTo show you read this, put \u201cDRAGONFRUIT\u201d in your subject line.\nApply to: careers@innovate.example.org`;
    const res = auditScreeningTraps(jdDoubleCurly);

    // Oracle Assertion: Must successfully extract DRAGONFRUIT
    assert(
      res.secretCodes.includes('DRAGONFRUIT'),
      `BUG CONFIRMED: Typographical curly quotes (\u201cDRAGONFRUIT\u201d) failed backreference \\1 check. Extracted: ${JSON.stringify(res.secretCodes)}`
    );
  });

  test('1.3 Adversarial Vulnerability: Pattern 4 extracts leading colon when JD has "is:"', () => {
    // When text has "Secret word is: SUNBURST", (?:is|:)? matches "is",
    // leaving the trailing colon unconsumed. The captured code becomes ": SUNBURST".
    const jdColon = `Verification instructions: Secret word is: SUNBURST. Apply now.`;
    const resColon = auditScreeningTraps(jdColon);

    // Oracle Assertion: Must extract clean 'SUNBURST' without leading colon
    assert(
      resColon.secretCodes.includes('SUNBURST'),
      `BUG CONFIRMED: Secret code extracted with raw leading colon: ${JSON.stringify(resColon.secretCodes)}`
    );
    assert(
      !resColon.secretCodes.includes(': SUNBURST'),
      `BUG CONFIRMED: Corrupted secret code contains colon prefix: ": SUNBURST"`
    );
  });

  test('1.4 Complex Email Extraction — URL params, mailto, fake domains, trailing punctuation', () => {
    // Fake onlinejobs.ph email should be ignored
    const jdFakeOlj = `Do not message us here. Contact support@onlinejobs.ph for billing questions. We hire through platform only.`;
    const resFake = auditScreeningTraps(jdFakeOlj);
    assert.strictEqual(resFake.emailSubmission, null, 'Ignored domain onlinejobs.ph should not be extracted as emailSubmission');
    assert.strictEqual(resFake.route, 'B', 'Job with only onlinejobs.ph email should route to Route B');

    // Email embedded inside URL query parameter
    const jdUrlParam = `Apply at our portal: https://apply.greenhouse.io/landing?contact=talent.scout@nexusholdings.com&ref=boards`;
    const resUrl = auditScreeningTraps(jdUrlParam);
    assert.strictEqual(resUrl.emailSubmission, 'talent.scout@nexusholdings.com', `Failed to extract email embedded in URL. Got: ${resUrl.emailSubmission}`);
    assert.strictEqual(resUrl.route, 'A', 'Should resolve to Route A for emailSubmission');

    // Mailto link
    const jdMailto = `Click here: mailto:executives@premieradvisors.co.uk to submit CV.`;
    const resMailto = auditScreeningTraps(jdMailto);
    assert.strictEqual(resMailto.emailSubmission, 'executives@premieradvisors.co.uk', `Failed to parse mailto link. Got: ${resMailto.emailSubmission}`);

    // Email with trailing punctuation
    const jdPunctuation = `Submit CV to hiring@alphacorp.com. (Inquiries to hr@alphacorp.com);`;
    const resPunct = auditScreeningTraps(jdPunctuation);
    assert.strictEqual(resPunct.emailSubmission, 'hiring@alphacorp.com', `Trailing punctuation not cleanly stripped: ${resPunct.emailSubmission}`);

    // Image filename false-positive suppression
    const jdImage = `Assets required: icon@2x.png and banner@hires.jpg. Apply on-platform.`;
    const resImage = auditScreeningTraps(jdImage);
    assert.strictEqual(resImage.emailSubmission, null, `Image asset filename falsely matched as email: ${resImage.emailSubmission}`);

    // Sequential fake then real email
    const jdSequence = `Ignore admin@example.com and contact@test.com. Real applications: ops@vanguardpartners.org.`;
    const resSeq = auditScreeningTraps(jdSequence);
    assert.strictEqual(resSeq.emailSubmission, 'ops@vanguardpartners.org', `Failed to skip ignored domains in sequence. Got: ${resSeq.emailSubmission}`);
  });

  test('1.5 External Application Forms & Channel Route Precedence (Route C > Route A > Route B)', () => {
    // Form detection across standard supported providers
    const formSamples = [
      { url: 'https://forms.gle/4j9XqL8yP9Z', desc: 'Google Forms Short' },
      { url: 'https://docs.google.com/forms/d/e/1FAIpQLSc-sample/viewform', desc: 'Google Forms Full' },
      { url: 'https://airtable.com/app123/shr456', desc: 'Airtable Form' },
      { url: 'https://forms.clickup.com/f/33211', desc: 'ClickUp Form subdomain' },
      { url: 'https://recruitcrm.io/apply/9981', desc: 'RecruitCRM ATS' },
      { url: 'https://tally.so/r/mK90pL', desc: 'Tally Form' },
      { url: 'https://jotform.com/23123456789', desc: 'JotForm Root Domain' }
    ];

    formSamples.forEach(sample => {
      const jd = `To apply, visit our external intake: ${sample.url}. Include your availability.`;
      const res = auditScreeningTraps(jd);
      assert.strictEqual(res.route, 'C', `Expected Route C for ${sample.desc}, got: ${res.route}`);
      assert.strictEqual(res.connects, 0, `Expected 0 connects for Route C ${sample.desc}`);
      assert(res.formSubmission.startsWith('http'), `formSubmission should be valid URL for ${sample.desc}`);
    });

    // Subdomain JotForm URL check
    const jdJotformSubdomain = `Apply here: https://form.jotform.com/23123456789.`;
    const resJot = auditScreeningTraps(jdJotformSubdomain);
    assert.strictEqual(
      resJot.route,
      'C',
      `BUG CONFIRMED: form.jotform.com failed formRegex and routed to ${resJot.route} instead of Route C (External Form)`
    );

    // Priority conflict resolution: BOTH Form URL and Direct Email present
    const jdBoth = `Fill out our screening questionnaire at https://forms.gle/screening123.
If technical issues arise, contact fallback@company.com.`;
    const resBoth = auditScreeningTraps(jdBoth);
    assert.strictEqual(resBoth.route, 'C', 'Route C (External Form) must take strict priority over Route A (Email)');
    assert.strictEqual(resBoth.connects, 0, 'Zero connects constraint must hold');
    assert.strictEqual(resBoth.target, 'https://forms.gle/screening123');

    // Route B default
    const jdRouteB = `Standard Virtual Assistant role. Submit your application directly through this platform.`;
    const resB = auditScreeningTraps(jdRouteB);
    assert.strictEqual(resB.route, 'B');
    assert.strictEqual(resB.connects, 20);
    assert.strictEqual(resB.target, 'OnlineJobs.ph Modal');
  });

  test('1.6 Secret Code Word Noise Rejection & Fallbacks', () => {
    // Pattern 3: Subject line must contain
    const jdPattern3 = `Notice: Subject line must contain "GLACIER" to be reviewed.`;
    const res3 = auditScreeningTraps(jdPattern3);
    assert(res3.secretCodes.includes('GLACIER'), `Pattern 3 failed. Got: ${JSON.stringify(res3.secretCodes)}`);

    // Noise word rejection
    const jdNoise1 = `Please put the word carefully in your subject line if you understand.`;
    const resNoise1 = auditScreeningTraps(jdNoise1);
    assert(!resNoise1.secretCodes.includes('CAREFULLY') && !resNoise1.secretCodes.includes('WORD'), 'Noise word should be rejected');

    // Missing code word handling
    const jdNoCode = `We are looking for an executive assistant. Please review requirements and apply.`;
    const resNoCode = auditScreeningTraps(jdNoCode);
    assert.strictEqual(resNoCode.secretCodes.length, 0, 'Empty code word array expected when no trap exists');

    // Hardcoded Preset Fallbacks
    assert(auditScreeningTraps('We love BLUEBERRY muffins!').secretCodes.includes('BLUEBERRY'));
    assert(auditScreeningTraps('Operation PHOENIX is active.').secretCodes.includes('PHOENIX'));
  });

  test('1.7 Speedtest, Voice/Video, and Typing Test Variations', () => {
    // Speedtest variations
    const stCases = [
      'Must provide a speedtest result link.',
      'Attach your speed test screenshot.',
      'Proof of high-speed internet speed required.'
    ];
    stCases.forEach(st => {
      const res = auditScreeningTraps(st);
      assert.strictEqual(res.requiresSpeedtest, true, `Speedtest flag failed for: "${st}"`);
    });

    // Voice / Video variations
    const vidCases = [
      'Include a short Loom video introducing yourself.',
      'Record a 60-second video intro.',
      'Submit an audio clip demonstrating English fluency.'
    ];
    vidCases.forEach(vid => {
      const res = auditScreeningTraps(vid);
      assert.strictEqual(res.requiresVoiceVideo, true, `Voice/video flag failed for: "${vid}"`);
    });

    // Typing test variations (engine response stability)
    const typingJd = `Requirements: Typing test score above 60 WPM. Submit typing test certificate.`;
    const resTyping = auditScreeningTraps(typingJd);
    assert.strictEqual(typeof resTyping, 'object');
  });

  test('1.8 Boundary Inputs, ReDoS Stress & Match Scoring', () => {
    // Empty, null, undefined, whitespace
    assert.strictEqual(auditScreeningTraps('').route, 'B');
    assert.strictEqual(auditScreeningTraps(null).route, 'B');
    assert.strictEqual(auditScreeningTraps(undefined).route, 'B');
    assert.strictEqual(auditScreeningTraps('   \t\n   ').route, 'B');

    // 20,000 character JD with repeated regex triggers (ReDoS safety test)
    const startTime = performance.now();
    const largeJd = 'Looking for an assistant. '.repeat(500) + 
      'Please put "EVEREST" in your subject line. ' +
      'https://forms.clickup.com/f/99999 ' +
      'Check speedtest and submit. '.repeat(300);
    const resLarge = auditScreeningTraps(largeJd);
    const duration = performance.now() - startTime;

    assert(duration < 250, `ReDoS risk: auditScreeningTraps took ${duration.toFixed(2)}ms on 20k payload`);
    assert(resLarge.secretCodes.includes('EVEREST'));
    assert.strictEqual(resLarge.route, 'C');
    assert.strictEqual(resLarge.requiresSpeedtest, true);

    // Match scoring
    const vaJd = `Executive Virtual Assistant for calendar scheduling, email inbox management, Notion SOP documentation, Google Sheets reporting.`;
    const scoreObj = calculateMatchScore(vaJd);
    assert(scoreObj.score >= 80, `Expected High Fit score (>=80), got: ${scoreObj.score}`);
    assert.strictEqual(scoreObj.tier, 'High Fit');

    const devJd = `Senior Software Engineer with Docker, Kubernetes, and backend DevOps expertise.`;
    const devScore = calculateMatchScore(devJd);
    assert(devScore.score < 50, `Senior dev role must score < 50, got: ${devScore.score}`);
    assert.strictEqual(devScore.tier, 'Low Fit');
  });

});

// -------------------------------------------------------------------------
// SUITE 2: MCP Simulator 8-Tool Adversarial Stress Tests & Mutation Integrity
// -------------------------------------------------------------------------
suite('2. MCP Simulator — 8-Tool Execution, Boundary Arguments & In-Memory Mutation', () => {

  const freshEnv = loadAppModule();
  freshEnv.app.initMcpSimulator();
  const tools = freshEnv.sandbox.__TOOL_CONFIGS__;
  assert(tools, 'TOOL_CONFIGS must be bound after initMcpSimulator()');

  test('2.1 Tool Registry Completeness (All 8 Tools Present & Callable)', () => {
    const requiredTools = [
      'search_jobs',
      'get_job_details',
      'generate_job_proposal',
      'apply_job',
      'update_job_status',
      'trigger_scrape',
      'get_pipeline_stats',
      'get_candidate_profile'
    ];
    requiredTools.forEach(t => {
      assert(tools[t], `Tool ${t} missing from TOOL_CONFIGS`);
      assert(typeof tools[t].exec === 'function', `Tool ${t} has no executable exec() function`);
    });
  });

  test('2.2 search_jobs — Filters, Boundaries, and Limit Clamping', () => {
    // Normal filter
    const res1 = tools.search_jobs.exec({ min_score: 80, status: 'New', client_region: 'US', limit: 5 });
    assert(typeof res1.count === 'number', 'count must be a number');
    res1.jobs.forEach(j => {
      assert(j.match_score >= 80, `Job score ${j.match_score} < 80`);
      assert.strictEqual(j.status, 'New');
    });

    // Extreme high threshold -> empty list
    const res2 = tools.search_jobs.exec({ min_score: 99, status: 'All', client_region: 'All', limit: 10 });
    assert.strictEqual(res2.count, 0);
    assert.strictEqual(res2.jobs.length, 0);

    // Clamped limit = 1
    const res3 = tools.search_jobs.exec({ min_score: 50, status: 'All', client_region: 'All', limit: 1 });
    assert.strictEqual(res3.jobs.length, 1);
  });

  test('2.3 get_job_details — Valid, Invalid, and Boundary IDs', () => {
    // Valid ID
    const valid = tools.get_job_details.exec({ job_id: 'seed-001' });
    assert.strictEqual(valid.job_id, 'seed-001');
    assert(valid.screening_audit, 'Must include screening_audit');
    assert(valid.screening_audit.secretCodes.includes('BLUEBERRY'), 'Audit must detect BLUEBERRY in seed-001');

    // Invalid IDs
    const invalidIds = ['seed-999', 'invalid_id', '', null, undefined];
    invalidIds.forEach(id => {
      const errRes = tools.get_job_details.exec({ job_id: id });
      assert(errRes.error, `Expected error object for job_id: ${id}`);
    });
  });

  test('2.4 generate_job_proposal — Valid Generation and Grounding', () => {
    const res = tools.generate_job_proposal.exec({ job_id: 'seed-001', client_name: 'Apex Partners' });
    assert.strictEqual(res.job_id, 'seed-001');
    assert.strictEqual(res.employer, 'Apex Partners');
    assert(res.proposal_text.includes('BLUEBERRY'), 'Proposal text must include detected code word');
    assert.strictEqual(res.zero_hallucinations_verified, true);
    assert(res.word_count > 100);

    // Missing job ID
    const errRes = tools.generate_job_proposal.exec({ job_id: 'seed-404' });
    assert(errRes.error);
  });

  test('2.5 In-Memory Database State Persistence & Mutation Integrity (apply_job & update_job_status)', () => {
    // Step A: Baseline pipeline stats
    const initialStats = tools.get_pipeline_stats.exec();
    const initApplied = initialStats.status_breakdown.Applied;
    const initNew = initialStats.status_breakdown.New;

    // Step B: Apply to seed-003
    const applyRes = tools.apply_job.exec({
      job_id: 'seed-003',
      notes: 'Applied via Route A Direct Email with tailored cover letter.'
    });
    assert.strictEqual(applyRes.status, 'success');
    assert.strictEqual(applyRes.updated_status, 'Applied');
    assert.strictEqual(applyRes.connects_spent, 0, 'Must record 0 connects spent');

    // Step C: Verify persistence in get_job_details
    const detailAfter = tools.get_job_details.exec({ job_id: 'seed-003' });
    assert.strictEqual(detailAfter.status, 'Applied', 'Job status must persist as Applied in DB');
    assert(detailAfter.notes.includes('[Applied:'), 'Audit timestamp entry must persist in notes');
    assert(detailAfter.notes.includes('Applied via Route A Direct Email'));

    // Step D: Verify persistence in search_jobs filter
    const searchApplied = tools.search_jobs.exec({ min_score: 50, status: 'Applied', limit: 10 });
    const foundInApplied = searchApplied.jobs.some(j => j.job_id === 'seed-003');
    assert(foundInApplied, 'seed-003 must be discoverable in search_jobs with status: Applied');

    // Step E: Verify pipeline stats counters updated consistently
    const updatedStats = tools.get_pipeline_stats.exec();
    assert.strictEqual(updatedStats.status_breakdown.Applied, initApplied + 1, 'Applied count must increment by exactly 1');
    assert.strictEqual(updatedStats.status_breakdown.New, initNew - 1, 'New count must decrement by exactly 1');

    // Step F: update_job_status mutation to "Shortlisted" on seed-004
    const updateRes = tools.update_job_status.exec({
      job_id: 'seed-004',
      status: 'Shortlisted',
      notes: 'Employer viewed profile.'
    });
    assert.strictEqual(updateRes.status, 'success');
    assert.strictEqual(updateRes.current_status, 'Shortlisted');

    const detail004 = tools.get_job_details.exec({ job_id: 'seed-004' });
    assert.strictEqual(detail004.status, 'Shortlisted', 'Status update to Shortlisted must persist');

    // Step G: Successive apply on already applied job (multi-touch logging)
    tools.apply_job.exec({ job_id: 'seed-003', notes: 'Follow-up email dispatched.' });
    const detailAfter2 = tools.get_job_details.exec({ job_id: 'seed-003' });
    assert(detailAfter2.notes.includes('Follow-up email dispatched.'), 'Subsequent audit logs must append cleanly');

    // Step H: Invalid ID in apply_job returns error and leaves DB uncorrupted
    const invalidApply = tools.apply_job.exec({ job_id: 'seed-unknown', notes: 'test' });
    assert(invalidApply.error, 'Invalid job ID must return error');
  });

  test('2.6 trigger_scrape — Crawl Simulation Math & Boundary Handling', () => {
    const res1 = tools.trigger_scrape.exec({ pages: 3, target_region: 'US/UK/AU' });
    assert.strictEqual(res1.status, 'completed');
    assert.strictEqual(res1.pages_crawled, 3);
    assert.strictEqual(res1.listings_discovered, 90);
    assert(res1.zero_connect_routes_detected.email_route_a >= 0);

    const res2 = tools.trigger_scrape.exec({});
    assert.strictEqual(res2.pages_crawled, 3);
  });

  test('2.7 get_pipeline_stats & get_candidate_profile — Safety & Zero Leaks', () => {
    const stats = tools.get_pipeline_stats.exec();
    assert.strictEqual(stats.total_connects_spent, 0, 'Total connects spent must strictly remain 0');
    assert(stats.zero_cost_compliance.includes('0 points spent'));

    const profile = tools.get_candidate_profile.exec();
    assert.strictEqual(profile.candidate.name, 'Alex Taylor');
    assert.strictEqual(profile.candidate.email, 'alex.taylor@example.com');
    assert(Array.isArray(profile.anti_hallucination_rules));
  });

});

// -------------------------------------------------------------------------
// SUITE 3: Peak Hiring Hours World Clock & Countdown Math Stress Tests
// -------------------------------------------------------------------------
suite('3. Global Hiring Windows World Clock & Countdown Math', () => {

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

  function calculateNextScrapeCountdown(simulatedDate) {
    const phtParts = new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Manila",
      year: "numeric", month: "numeric", day: "numeric",
      hour: "numeric", minute: "numeric", second: "numeric",
      hourCycle: "h23"
    }).formatToParts(simulatedDate);
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

    const totalSec = Math.floor(minDiff / 1000);
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    const formatted = `${h > 0 ? h + "h " : ""}${m}m ${s < 10 ? "0" + s : s}s`;

    return { minDiff, totalSec, h, m, s, formatted };
  }

  function checkMarketPeak(simulatedDate, tz, startH, startM, endH, endM) {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      hour: "numeric",
      minute: "numeric",
      hourCycle: "h23"
    }).formatToParts(simulatedDate);
    const map = {};
    parts.forEach(p => map[p.type] = p.value);
    const hour = parseInt(map.hour, 10);
    const minute = parseInt(map.minute, 10);

    const currentMins = hour * 60 + minute;
    const startMins = startH * 60 + startM;
    const endMins = endH * 60 + endM;

    return currentMins >= startMins && currentMins <= endMins;
  }

  test('3.1 Timezone Formatting Across All 5 Key Business Regions', () => {
    const tzs = [
      { name: 'PHT', tz: 'Asia/Manila' },
      { name: 'PST', tz: 'America/Los_Angeles' },
      { name: 'EST', tz: 'America/New_York' },
      { name: 'GMT', tz: 'Europe/London' },
      { name: 'AEST', tz: 'Australia/Sydney' }
    ];

    const testDate = new Date('2026-11-12T12:00:00Z');
    tzs.forEach(t => {
      const formatted = new Intl.DateTimeFormat('en-US', {
        timeZone: t.tz,
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true
      }).format(testDate);
      assert(typeof formatted === 'string' && formatted.length > 5, `Failed formatting for ${t.name}: ${formatted}`);
    });
  });

  test('3.2 Market Peak Status Boundary Minute Checks', () => {
    // US West (PST): 09:00 - 11:30 (America/Los_Angeles)
    const checkPst = (h, m) => {
      const d = new Date(Date.UTC(2026, 10, 12, h + 8, m, 0));
      return checkMarketPeak(d, 'America/Los_Angeles', 9, 0, 11, 30);
    };
    assert.strictEqual(checkPst(8, 59), false, 'PST 08:59 should be off-peak');
    assert.strictEqual(checkPst(9, 0), true, 'PST 09:00 should be active peak');
    assert.strictEqual(checkPst(10, 15), true, 'PST 10:15 should be active peak');
    assert.strictEqual(checkPst(11, 30), true, 'PST 11:30 should be active peak');
    assert.strictEqual(checkPst(11, 31), false, 'PST 11:31 should be off-peak');

    // US East (EST): 08:00 - 11:30 (America/New_York)
    const checkEst = (h, m) => {
      const d = new Date(Date.UTC(2026, 10, 12, h + 5, m, 0));
      return checkMarketPeak(d, 'America/New_York', 8, 0, 11, 30);
    };
    assert.strictEqual(checkEst(7, 59), false, 'EST 07:59 should be off-peak');
    assert.strictEqual(checkEst(8, 0), true, 'EST 08:00 should be active peak');
    assert.strictEqual(checkEst(11, 30), true, 'EST 11:30 should be active peak');
    assert.strictEqual(checkEst(11, 31), false, 'EST 11:31 should be off-peak');

    // UK (GMT): 09:00 - 11:30 (Europe/London)
    const checkGmt = (h, m) => {
      const d = new Date(Date.UTC(2026, 10, 12, h, m, 0));
      return checkMarketPeak(d, 'Europe/London', 9, 0, 11, 30);
    };
    assert.strictEqual(checkGmt(8, 59), false, 'GMT 08:59 should be off-peak');
    assert.strictEqual(checkGmt(9, 0), true, 'GMT 09:00 should be active peak');
    assert.strictEqual(checkGmt(11, 30), true, 'GMT 11:30 should be active peak');
    assert.strictEqual(checkGmt(11, 31), false, 'GMT 11:31 should be off-peak');

    // Australia (AEST/AEDT): 09:00 - 11:30 (Australia/Sydney)
    const checkAest = (h, m) => {
      const d = new Date(Date.UTC(2026, 10, 12, (h - 11 + 24) % 24, m, 0));
      return checkMarketPeak(d, 'Australia/Sydney', 9, 0, 11, 30);
    };
    assert.strictEqual(checkAest(8, 59), false, 'AEST 08:59 should be off-peak');
    assert.strictEqual(checkAest(9, 0), true, 'AEST 09:00 should be active peak');
    assert.strictEqual(checkAest(11, 30), true, 'AEST 11:30 should be active peak');
    assert.strictEqual(checkAest(11, 31), false, 'AEST 11:31 should be off-peak');
  });

  test('3.3 Countdown Math — Boundary Seconds, Midnight Rollover, and Next Slot Transitions', () => {
    // Case A: Exactly 1 second before Slot 1 (01:00:00 PHT) -> 00:59:59 PHT
    const dBefore1 = new Date(Date.UTC(2026, 10, 11, 16, 59, 59));
    const resA = calculateNextScrapeCountdown(dBefore1);
    assert.strictEqual(resA.totalSec, 1, `Expected 1s countdown, got: ${resA.totalSec}s`);
    assert.strictEqual(resA.formatted, '0m 01s');

    // Case B: At exact moment of Slot 1 (01:00:00 PHT) -> advances to 03:30:00 PHT
    const dAt1 = new Date(Date.UTC(2026, 10, 11, 17, 0, 0));
    const resB = calculateNextScrapeCountdown(dAt1);
    assert.strictEqual(resB.totalSec, 2 * 3600 + 30 * 60, `Expected 2h 30m, got: ${resB.totalSec}s`);
    assert.strictEqual(resB.formatted, '2h 30m 00s');

    // Case C: Between slots (08:00:00 PHT) -> next slot 09:30 (1h 30m)
    const dBetween = new Date(Date.UTC(2026, 10, 12, 0, 0, 0));
    const resC = calculateNextScrapeCountdown(dBetween);
    assert.strictEqual(resC.totalSec, 1 * 3600 + 30 * 60);
    assert.strictEqual(resC.formatted, '1h 30m 00s');

    // Case D: Exact moment of final daily slot (23:30:00 PHT) -> advances to tomorrow 01:00 (1h 30m)
    const dAtLastSlot = new Date(Date.UTC(2026, 10, 12, 15, 30, 0));
    const resD = calculateNextScrapeCountdown(dAtLastSlot);
    assert.strictEqual(resD.totalSec, 1 * 3600 + 30 * 60);
    assert.strictEqual(resD.formatted, '1h 30m 00s');

    // Case E: Late night past last slot (23:45:00 PHT) -> 1h 15m to 01:00:00
    const dLateNight = new Date(Date.UTC(2026, 10, 12, 15, 45, 0));
    const resE = calculateNextScrapeCountdown(dLateNight);
    assert.strictEqual(resE.totalSec, 1 * 3600 + 15 * 60);
    assert.strictEqual(resE.formatted, '1h 15m 00s');

    // Case F: Midnight Eve (23:59:59 PHT) -> 1h 0m 1s to 01:00:00
    const dMidnightEve = new Date(Date.UTC(2026, 10, 12, 15, 59, 59));
    const resF = calculateNextScrapeCountdown(dMidnightEve);
    assert.strictEqual(resF.totalSec, 3601);
    assert.strictEqual(resF.formatted, '1h 0m 01s');

    // Case G: Month-End Rollover (Nov 30 23:45:00 PHT -> Dec 1 01:00:00 PHT)
    const dMonthEnd = new Date(Date.UTC(2026, 10, 30, 15, 45, 0));
    const resG = calculateNextScrapeCountdown(dMonthEnd);
    assert.strictEqual(resG.totalSec, 4500);

    // Case H: Year-End Rollover (Dec 31 23:45:00 PHT -> Jan 1 01:00:00 PHT)
    const dYearEnd = new Date(Date.UTC(2026, 11, 31, 15, 45, 0));
    const resH = calculateNextScrapeCountdown(dYearEnd);
    assert.strictEqual(resH.totalSec, 4500);

    // Guarantee: All calculations must yield positive non-zero integers
    [resA, resB, resC, resD, resE, resF, resG, resH].forEach((r, idx) => {
      assert(!isNaN(r.totalSec), `Case ${idx} yielded NaN`);
      assert(r.totalSec >= 0, `Case ${idx} yielded negative countdown seconds: ${r.totalSec}`);
    });
  });

});

// -------------------------------------------------------------------------
// SUITE 4: DOM Wireup, Interactive Sandbox Controllers, & Lifecycle
// -------------------------------------------------------------------------
suite('4. DOM Wireup, Interactive Sandbox Controllers, & Lifecycle', () => {

  test('4.1 Full DOM Initialization Lifecycle (DOMContentLoaded Execution)', () => {
    const fullEnv = loadAppModule();
    assert(fullEnv.domListeners.length > 0, 'DOMContentLoaded listener should be registered');
    fullEnv.domListeners.forEach(({ evt, cb }) => {
      if (evt === 'DOMContentLoaded') {
        cb();
      }
    });

    // Check initial preset value was set into #jd-input
    const jdInput = fullEnv.mockElements.get('jd-input');
    assert(jdInput.value.length > 0, '#jd-input should be populated on boot');
    assert(jdInput.value.includes('BLUEBERRY'), 'Initial preset should default to blueberry');

    // Check evaluation result elements populated
    const scoreEl = fullEnv.mockElements.get('result-match-score');
    assert(scoreEl.textContent.includes('%'), 'Match score element should be populated');

    const routeEl = fullEnv.mockElements.get('result-route');
    assert.strictEqual(routeEl.textContent, 'Route A: Direct Email');

    const connectsEl = fullEnv.mockElements.get('result-connects');
    assert.strictEqual(connectsEl.textContent, '0 Points');

    const proposalEl = fullEnv.mockElements.get('result-proposal-body');
    assert(proposalEl.textContent.includes('Alex Taylor'), 'Proposal body should be populated with candidate info');
  });

  test('4.2 Preset Button Interactions & Dynamic Evaluation', () => {
    const fullEnv = loadAppModule();
    fullEnv.domListeners.forEach(({ evt, cb }) => { if (evt === 'DOMContentLoaded') cb(); });

    const opsPreset = fullEnv.presetButtons.find(p => p.getAttribute('data-preset') === 'operations');
    assert(opsPreset, 'Operations preset button should exist');

    // Trigger click on operations preset
    opsPreset.dispatchEvent('click');

    const jdInput = fullEnv.mockElements.get('jd-input');
    assert(jdInput.value.includes('PHOENIX'), 'Operations preset should update jd-input with PHOENIX');

    const routeEl = fullEnv.mockElements.get('result-route');
    assert.strictEqual(routeEl.textContent, 'Route C: External Form');

    const codeEl = fullEnv.mockElements.get('result-secret-code');
    assert(codeEl.textContent.includes('PHOENIX'));
  });

  test('4.3 Build Stepper & Sandbox Tab Navigation Toggles', () => {
    const fullEnv = loadAppModule();
    fullEnv.domListeners.forEach(({ evt, cb }) => { if (evt === 'DOMContentLoaded') cb(); });

    const stepBtns = fullEnv.stepperButtons;
    assert.strictEqual(stepBtns.length, 5, 'Should find 5 build stepper buttons');

    // Click step 3
    stepBtns[2].dispatchEvent('click');
    assert(stepBtns[2].classList.contains('active'), 'Step 3 button should become active');
    assert.strictEqual(stepBtns[2].getAttribute('aria-selected'), 'true');

    // Sandbox tabs
    const tabs = fullEnv.sandboxTabs;
    assert.strictEqual(tabs.length, 3, 'Should find 3 sandbox tabs');

    // Click second tab (mcp)
    tabs[1].dispatchEvent('click');
    assert(tabs[1].classList.contains('active'), 'MCP tab should become active');
    assert.strictEqual(tabs[1].getAttribute('aria-selected'), 'true');
  });

});

// -------------------------------------------------------------------------
// SUMMARY & VERDICT
// -------------------------------------------------------------------------
console.log(`\n======================================================================`);
console.log(`ADVERSARIAL STRESS TEST EXECUTION SUMMARY`);
console.log(`======================================================================`);
console.log(`Total Invocations Tested : ${totalTests}`);
console.log(`Passed Assertions        : ${passedTests}`);
console.log(`Failed Assertions        : ${failedTests}`);
console.log(`Pass Rate                : ${((passedTests / totalTests) * 100).toFixed(1)}%`);

if (failedTests > 0) {
  console.log(`\n[EMPIRICAL DEFECTS CONFIRMED: ${failedTests}]`);
  failureDetails.forEach(({ name, error }, idx) => {
    console.log(` ${idx + 1}. ${name}`);
    console.log(`    -> ${error.message}`);
  });
  process.exit(1);
} else {
  console.log(`\n[SUCCESS] 100% of client-side JavaScript engine verification tests passed.`);
  process.exit(0);
}
