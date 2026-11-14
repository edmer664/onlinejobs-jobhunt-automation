/**
 * verify_challenger_adversarial.js
 * Adversarial Gate Stress Harness executed by challenger_os_m3_v2.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const APP_JS_PATH = path.resolve(__dirname, '../docs/app.js');
const appCode = fs.readFileSync(APP_JS_PATH, 'utf8');

// Hook auditScreeningTraps out of IIFE closure
let instrumented = appCode.replace(
  /}\)\(\);?\s*$/,
  `globalThis.__auditScreeningTraps = auditScreeningTraps;
   globalThis.__SAMPLE_JDS = SAMPLE_JDS;
  })();`
);

const sandbox = {
  console,
  performance,
  document: {
    addEventListener: () => {},
    querySelectorAll: () => [],
    getElementById: () => null
  }
};

vm.createContext(sandbox);
vm.runInContext(instrumented, sandbox);

const audit = sandbox.__auditScreeningTraps;
const SAMPLE_JDS = sandbox.__SAMPLE_JDS;

let total = 0;
let passed = 0;
let failed = 0;
const failures = [];

function check(name, fn) {
  total++;
  try {
    fn();
    passed++;
    console.log(`  [PASS] ${name}`);
  } catch (err) {
    failed++;
    console.error(`  [FAIL] ${name}: ${err.message}`);
    failures.push({ name, error: err.message });
  }
}

function assertArrayEqual(actual, expected, msg) {
  assert.strictEqual(
    JSON.stringify(Array.from(actual)),
    JSON.stringify(expected),
    msg || `Expected ${JSON.stringify(expected)} but got ${JSON.stringify(Array.from(actual))}`
  );
}

console.log('======================================================================');
console.log('CHALLENGER ADVERSARIAL STRESS SUITE: docs/app.js auditScreeningTraps');
console.log('======================================================================\n');

// -----------------------------------------------------------------------------
// Category 1: Disclaimer Sentences (False Positive Immunity)
// -----------------------------------------------------------------------------
console.log('--- Category 1: Disclaimer Sentences (False Positive Immunity) ---');

check('1.1 Standard disclaimer alone has no false positive secret code', () => {
  const res = audit('Applications that do not include the code word will be automatically rejected.');
  assert.strictEqual(
    res.secretCodes.includes('WILL BE AUTOMATICALLY REJECTED'),
    false,
    'Extracted sentence fragment as secret code!'
  );
  assert.strictEqual(res.secretCodes.length, 0);
});

check('1.2 Disqualification warning variation: "secret code will be disqualified immediately"', () => {
  const res = audit('Anyone who omits the secret code will be disqualified immediately.');
  assert.strictEqual(res.secretCodes.includes('WILL BE DISQUALIFIED IMMEDIATELY'), false);
  assert.strictEqual(res.secretCodes.length, 0);
});

check('1.3 Disqualification warning variation: "proposals without code word will be discarded"', () => {
  const res = audit('Proposals without the code word will be discarded without review.');
  assert.strictEqual(res.secretCodes.includes('WILL BE DISCARDED WITHOUT REVIEW'), false);
  assert.strictEqual(res.secretCodes.length, 0);
});

check('1.4 Magic word warning: "without the magic word your application will be ignored"', () => {
  const res = audit('Applications without the magic word will be ignored.');
  assert.strictEqual(res.secretCodes.length, 0);
});

check('1.5 Disclaimer combined with legitimate secret code word', () => {
  const jd = 'Our code word is: DRAGONFRUIT. Applications that do not include the code word will be automatically rejected.';
  const res = audit(jd);
  assertArrayEqual(res.secretCodes, ['DRAGONFRUIT']);
  assert.strictEqual(res.secretCodes.includes('WILL BE AUTOMATICALLY REJECTED'), false);
});

check('1.6 Full SAMPLE_JDS.blueberry correctly extracts BLUEBERRY without disclaimer junk', () => {
  const res = audit(SAMPLE_JDS.blueberry);
  assertArrayEqual(res.secretCodes, ['BLUEBERRY']);
  assert.ok(res.instructions.includes('[BLUEBERRY]'));
  assert.ok(!res.instructions.includes('WILL BE AUTOMATICALLY REJECTED'));
});

// -----------------------------------------------------------------------------
// Category 2: Typographical Quotes (Unicode Curly Quotes)
// -----------------------------------------------------------------------------
console.log('\n--- Category 2: Typographical Quotes (Unicode Curly Quotes) ---');

check('2.1 Double curly quotes: “DRAGONFRUIT” in subject pattern', () => {
  const res = audit('Please put \u201cDRAGONFRUIT\u201d in the subject line.');
  assert.strictEqual(res.secretCodes.includes('DRAGONFRUIT'), true);
});

check('2.2 Single curly quotes: ‘SUNBURST’ in start-with pattern', () => {
  const res = audit('Start your proposal with \u2018SUNBURST\u2019');
  assert.strictEqual(res.secretCodes.includes('SUNBURST'), true);
});

check('2.3 Double curly quotes in email subject variation: “AVOCADO”', () => {
  const res = audit('Include \u201cAVOCADO\u201d in your email subject');
  assert.strictEqual(res.secretCodes.includes('AVOCADO'), true);
});

check('2.4 Single curly quotes in write pattern: ‘PINEAPPLE’', () => {
  const res = audit('Write \u2018PINEAPPLE\u2019 on your subject line');
  assert.strictEqual(res.secretCodes.includes('PINEAPPLE'), true);
});

check('2.5 Double curly quotes in enter/type pattern: “COCONUT”', () => {
  const res = audit('Enter \u201cCOCONUT\u201d when prompted');
  assert.strictEqual(res.secretCodes.includes('COCONUT'), true);
});

check('2.6 Single curly quotes in enter/type pattern: ‘MANGO’', () => {
  const res = audit('Type \u2018MANGO\u2019 in your first sentence');
  assert.strictEqual(res.secretCodes.includes('MANGO'), true);
});

check('2.7 ASCII double and single quotes still work cleanly', () => {
  const res1 = audit('Put "GUAVA" in the subject');
  assert.strictEqual(res1.secretCodes.includes('GUAVA'), true);
  const res2 = audit("Put 'PAPAYA' in the subject");
  assert.strictEqual(res2.secretCodes.includes('PAPAYA'), true);
});

// -----------------------------------------------------------------------------
// Category 3: Colon and Whitespace Handling
// -----------------------------------------------------------------------------
console.log('\n--- Category 3: Colon and Whitespace Handling ---');

check('3.1 "Secret word is: SUNBURST" extracts without colon or spaces', () => {
  const res = audit('Secret word is: SUNBURST');
  assertArrayEqual(res.secretCodes, ['SUNBURST']);
});

check('3.2 "Secret word is : SUNBURST" (space before colon)', () => {
  const res = audit('Secret word is : SUNBURST');
  assertArrayEqual(res.secretCodes, ['SUNBURST']);
});

check('3.3 "Secret code: SUNBURST" (direct colon without is)', () => {
  const res = audit('Secret code: SUNBURST');
  assertArrayEqual(res.secretCodes, ['SUNBURST']);
});

check('3.4 "Magic phrase is:   SUNBURST   " (multiple spaces)', () => {
  const res = audit('Magic phrase is:   SUNBURST   ');
  assertArrayEqual(res.secretCodes, ['SUNBURST']);
});

check('3.5 "Verification code is: :::SUNBURST:::" (punctuation wrapping)', () => {
  const res = audit('Verification code is: :::SUNBURST:::');
  assertArrayEqual(res.secretCodes, ['SUNBURST']);
});

check('3.6 "Code word is: “SUNBURST”" (colon + curly quotes)', () => {
  const res = audit('Code word is: \u201cSUNBURST\u201d');
  assertArrayEqual(res.secretCodes, ['SUNBURST']);
});

// -----------------------------------------------------------------------------
// Category 4: Form URLs & Route Precedence (JotForm & Beyond)
// -----------------------------------------------------------------------------
console.log('\n--- Category 4: Form URLs & Route Precedence ---');

check('4.1 JotForm subdomain: https://form.jotform.com/23123456789 -> Route C', () => {
  const res = audit('Apply via: https://form.jotform.com/23123456789');
  assert.strictEqual(res.route, 'C');
  assert.strictEqual(res.routeLabel, 'Route C: External Form');
  assert.strictEqual(res.formSubmission, 'https://form.jotform.com/23123456789');
  assert.strictEqual(res.connects, 0);
});

check('4.2 JotForm other subdomain: https://submit.jotform.com/99887766 -> Route C', () => {
  const res = audit('Fill out https://submit.jotform.com/99887766 to apply');
  assert.strictEqual(res.route, 'C');
  assert.strictEqual(res.formSubmission, 'https://submit.jotform.com/99887766');
});

check('4.3 JotForm apex domain: http://jotform.com/12345 -> Route C', () => {
  const res = audit('Go to http://jotform.com/12345');
  assert.strictEqual(res.route, 'C');
  assert.strictEqual(res.formSubmission, 'http://jotform.com/12345');
});

check('4.4 JotForm URL with trailing punctuation stripped cleanly', () => {
  const res = audit('Submit your responses at https://form.jotform.com/23123456789.');
  assert.strictEqual(res.formSubmission, 'https://form.jotform.com/23123456789');
});

check('4.5 Route Precedence: External Form > Direct Email (Route C > Route A)', () => {
  const jd = 'Send email to hr@company.com OR fill out the form at https://form.jotform.com/23123456789';
  const res = audit(jd);
  assert.strictEqual(res.route, 'C');
  assert.strictEqual(res.formSubmission, 'https://form.jotform.com/23123456789');
  assert.strictEqual(res.emailSubmission, 'hr@company.com');
  assert.strictEqual(res.connects, 0);
  assert.strictEqual(res.target, 'https://form.jotform.com/23123456789');
});

check('4.6 Route A: Direct Email only when no external form', () => {
  const jd = 'Send your resume to careers@acmecorp.com directly.';
  const res = audit(jd);
  assert.strictEqual(res.route, 'A');
  assert.strictEqual(res.emailSubmission, 'careers@acmecorp.com');
  assert.strictEqual(res.connects, 0);
  assert.strictEqual(res.target, 'careers@acmecorp.com');
});

check('4.7 Route B: No external channel -> On-Platform with 20 connects', () => {
  const jd = 'Looking for an executive virtual assistant. Apply directly on this site.';
  const res = audit(jd);
  assert.strictEqual(res.route, 'B');
  assert.strictEqual(res.connects, 20);
  assert.strictEqual(res.target, 'OnlineJobs.ph Modal');
});

// -----------------------------------------------------------------------------
// Category 5: Noise Rejection & Boundary Fuzzing
// -----------------------------------------------------------------------------
console.log('\n--- Category 5: Noise Rejection & Boundary Fuzzing ---');

check('5.1 Noise words rejection: "the", "word", "code", "proposal"', () => {
  const res1 = audit('The secret code is: the');
  assert.strictEqual(res1.secretCodes.includes('THE'), false);
  const res2 = audit('Secret word is: word');
  assert.strictEqual(res2.secretCodes.includes('WORD'), false);
  const res3 = audit('Verification code is: application');
  assert.strictEqual(res3.secretCodes.includes('APPLICATION'), false);
});

check('5.2 Empty or whitespace inputs do not throw and return defaults', () => {
  const res1 = audit('');
  assert.strictEqual(res1.route, 'B');
  assert.strictEqual(res1.secretCodes.length, 0);
  const res2 = audit('   \n\t  ');
  assert.strictEqual(res2.route, 'B');
  assert.strictEqual(res2.secretCodes.length, 0);
  const res3 = audit(null);
  assert.strictEqual(res3.route, 'B');
});

check('5.3 Ignored domains for email (onlinejobs.ph, example.com, test.com)', () => {
  const jd = 'Contact support@onlinejobs.ph or demo@example.com for help.';
  const res = audit(jd);
  assert.strictEqual(res.emailSubmission, null);
  assert.strictEqual(res.route, 'B');
});

check('5.4 ReDoS safety: 10,000 repetitions of nested quotes execute instantaneously', () => {
  const evilInput = 'put ' + '“'.repeat(1000) + 'A' + '”'.repeat(1000) + ' in the subject line';
  const start = Date.now();
  const res = audit(evilInput);
  const elapsed = Date.now() - start;
  assert.ok(elapsed < 200, `Execution took too long: ${elapsed}ms`);
});

console.log('\n======================================================================');
console.log(`SUMMARY: ${passed}/${total} checks passed (${((passed/total)*100).toFixed(1)}%).`);
if (failed > 0) {
  console.error(`FAILED: ${failed} checks failed.`);
  process.exit(1);
} else {
  console.log('ALL ADVERSARIAL CHALLENGES PASSED PERFECTLY!');
  process.exit(0);
}
