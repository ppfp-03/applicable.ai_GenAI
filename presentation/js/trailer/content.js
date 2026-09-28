/*
 * Trailer copy and data. Everything a writer might want to change lives here; the scenes
 * only decide how it moves. Companies are the fictional demo set, shown as monograms.
 */
(function (A) {
  'use strict';

  A.content = {
    opening: ['Entering the job market', 'is already a job.'],
    verbs: ['Find.', 'Read.', 'Compare.', 'Adapt.', 'Write.', 'Apply.', 'Repeat.'],

    // Phase 1 desk: the first three roles you find.
    firstJobs: [
      { id: 'j-bolton', mono: 'BC', title: 'Strategy Analyst', company: 'Bolton Consulting Group', city: 'London', priority: 88, bar: 72, closes: 'Closes in 6 d', hot: true },
      { id: 'j-deutsch', mono: 'DB', title: 'Investment Banking Analyst', company: 'Deutsch Bank', city: 'Frankfurt', priority: 92, bar: 58, closes: 'Closes 14 Oct' },
      { id: 'j-nestella', mono: 'NE', title: 'Business Analyst', company: 'Nestella', city: 'Milan', priority: 81, bar: 40, closes: 'Closes 20 Oct', grey: true },
    ],
    jd: {
      title: 'Investment Banking Analyst',
      company: 'Deutsch Bank · Frankfurt',
      words: '1,240 words',
    },
    cvFiles: ['CV_consulting.pdf', 'CV_banking_v2.pdf', 'CV_final_FINAL.pdf'],
    letter: { greeting: 'Dear Hiring Manager,' },
    form: { title: 'Application form', fields: ['Full name', 'University', 'Upload CV', 'Why us? (300 words)'], submit: 'Submit' },

    // Phase 2: the rising tide. Types drive the counters.
    field: {
      jobs: [
        ['MS', 'Summer Analyst', 'Morgan Stanfield', 'London'],
        ['JM', 'Markets Graduate', 'J.P. Morrow', 'Paris'],
        ['RO', 'Business Analyst', 'Roshe', 'Basel'],
        ['LZ', 'M&A Analyst', 'Lazarde & Co.', 'Paris'],
        ['UC', 'Graduate Analyst', 'UniCreda', 'Milan'],
        ['MB', 'Analyst', 'Mediobanco', 'Milan'],
        ['RP', 'Product Analyst', 'Replai', 'Zurich'],
        ['NE', 'Finance Trainee', 'Nestella', 'Vevey'],
        ['BC', 'Associate', 'Bolton Consulting Group', 'Munich'],
        ['DB', 'Risk Analyst', 'Deutsch Bank', 'Berlin'],
        ['JM', 'Research Intern', 'J.P. Morrow', 'Dublin'],
        ['MS', 'IB Analyst', 'Morgan Stanfield', 'Frankfurt'],
        ['RO', 'Strategy Intern', 'Roshe', 'Zurich'],
        ['LZ', 'Analyst', 'Lazarde & Co.', 'Madrid'],
        ['RP', 'Data Analyst', 'Replai', 'Amsterdam'],
        ['UC', 'Treasury Graduate', 'UniCreda', 'Vienna'],
        ['MB', 'Summer Intern', 'Mediobanco', 'London'],
        ['BC', 'Business Analyst', 'Bolton Consulting Group', 'Amsterdam'],
        ['JM', 'Operations Analyst', 'J.P. Morrow', 'Luxembourg'],
        ['NE', 'Supply Chain Graduate', 'Nestella', 'Barcelona'],
        ['DB', 'Graduate Programme', 'Deutsch Bank', 'London'],
        ['MS', 'Wealth Analyst', 'Morgan Stanfield', 'Geneva'],
      ],
      deadlines: ['Closes Friday', 'Closes tomorrow 23:59', 'Closes in 3 days', 'Rolling — may close early', 'Closes Sunday', 'Closes in 6 days', 'Closes tonight', 'Closes 14 Oct'],
      statuses: [
        ['Applied', '12 days ago · no reply'],
        ['Online test', 'due in 48 h'],
        ['Interview', 'Tue 10:00'],
        ['Applied', 'yesterday'],
        ['Rejected', 'automated email'],
        ['Video interview', 'record by Thursday'],
        ['Draft', 'not submitted'],
        ['Applied', '3 weeks ago · no reply'],
      ],
      reminders: [
        'Follow up with J.P. Morrow',
        'Tailor CV for Roshe',
        'Ask Marta for a referral',
        'Cover letter · Mediobanco',
        'Case practice · 2 h',
        'Update LinkedIn',
      ],
      documents: ['Cover_letter_Lazarde.docx', 'CV_consulting_v4.pdf', 'Transcript_EN.pdf', 'Motivation_letter.docx', 'CV_short.pdf'],
    },
    counters: [
      { key: 'job', label: 'Open roles' },
      { key: 'deadline', label: 'Deadlines' },
      { key: 'status', label: 'Waiting on' },
      { key: 'document', label: 'Documents' },
    ],
    overload: 'Too much to keep track of.',
    harder: 'And then it gets harder.',

    // Phase 3
    abroad: ['Now do it', 'in another country.'],
    hero: { id: 'j-deutsch' },
    constraints: [
      { key: 'WORK AUTHORIZATION', value: 'Right to work in Germany?' },
      { key: 'LANGUAGE', value: 'Fluent German (C1) required' },
      { key: 'VISA / SPONSORSHIP', value: 'Sponsorship not offered' },
    ],
    fieldTags: [
      '? Right to work', 'German C1', 'No sponsorship', '? Work permit', 'French C1', 'EU passport only',
      '? Visa', 'Dutch B2', 'Swiss permit?', '? Right to work', 'Sponsorship unclear', 'Italian C2',
    ],
    like: 'Do I like this job?',
    can: 'Can I actually apply?',

    // Phase 4
    question: ['Which opportunity is', 'actually worth your time?'],

    // Phase 5
    profileTitle: 'Your profile',
    profileSub: 'CV_final_FINAL.pdf · 2 pages',
    facts: [
      { key: 'Education', value: 'MSc Finance · Bocconi', src: 'CV' },
      { key: 'Experience', value: 'M&A internship · 6 months', src: 'CV' },
      { key: 'Skills', value: 'Valuation · Excel · SQL', src: 'CV' },
      { key: 'Languages', value: 'Italian · English C1 · German A2', src: 'CV' },
      { key: 'Right to work', value: 'EU citizen', src: 'CV', note: 'UK: Not stated in your CV', uncertain: true },
      { key: 'Preferences', value: 'London · Milan · Frankfurt', src: 'YOU' },
    ],
    requirementsTitle: 'Investment Banking Analyst',
    requirementsSub: 'Deutsch Bank · Frankfurt',
    requirements: [
      { key: 'Degree', value: 'Finance or economics', src: 'JOB', match: 0, status: 'met' },
      { key: 'Experience', value: 'Banking internship', src: 'JOB', match: 1, status: 'met' },
      { key: 'Skills', value: 'Financial modelling', src: 'JOB', match: 2, status: 'met' },
      { key: 'Language', value: 'Fluent German (C1)', src: 'JOB', match: 3, status: 'conflict' },
      { key: 'Right to work', value: 'Germany', src: 'RULE', match: 4, status: 'met' },
      { key: 'Deadline', value: 'Closes 14 Oct', src: 'JOB', match: null, status: 'info' },
    ],
    fitLabel: 'Profile fit',
    fitValue: 'Strong · 92',
    eligLabel: 'Eligibility',
    eligValue: 'Explicit conflict',
    method: ['Understand.', 'Verify.', 'Prioritise.'],

    // Phase 6: ranked list. `fit` is profile fit; ordering is decided by the scenes.
    ranking: [
      { id: 'r-deutsch', mono: 'DB', title: 'Investment Banking Analyst', where: 'Deutsch Bank · Frankfurt', fit: 92 },
      { id: 'r-bolton', mono: 'BC', title: 'Strategy Analyst', where: 'Bolton Consulting Group · London', fit: 88 },
      { id: 'r-nestella', mono: 'NE', title: 'Business Analyst', where: 'Nestella · Milan', fit: 81 },
      { id: 'r-unicreda', mono: 'UC', title: 'Graduate Analyst', where: 'UniCreda · Milan', fit: 74 },
    ],
    listTitleBefore: 'Sorted by fit',
    listTitleAfter: 'Your shortlist this week',
    checking: 'Checking eligibility…',
    status: {
      eligible: 'Eligible under checked rules',
      verify: 'Needs verification',
      conflict: 'Explicit conflict',
    },
    statusDetail: {
      'r-deutsch': 'German C1 required',
      'r-bolton': 'UK right to work',
    },
    notForNow: 'Not for now',
    clarify: {
      label: 'Question · about 10 seconds',
      question: 'Are you authorised to work in the UK?',
      sub: 'Not stated in your CV · it decides Strategy Analyst at Bolton',
      answers: ['Yes', 'No', 'Not sure yet'],
      chosen: 0,
    },
    moved: '→ #1',

    // Phase 7: the app's own "Next best action" card, and the app's own promise.
    nextBest: {
      kicker: 'Your #1 this week',
      mono: 'BC',
      title: 'Apply to Bolton Consulting Group',
      sub: 'Strategy Analyst · London · Eligible under checked rules',
      closes: 'Closes Fri 2 Oct, 23:59 BST',
      count: [['6', 'd'], ['04', 'h'], ['12', 'm']],
      checks: [
        ['g', 'Right to work in the UK · you answered'],
        ['g', 'Strong profile fit · 88'],
        ['g', 'CV ready · 1 cover letter to write'],
      ],
      primary: 'Start application',
      secondary: 'Not now',
      whyQuote: 'M&A internship',
      whyAfter: ' · closest deadline',
    },
    tagline: ['Know where to apply', 'this week, and why.'],
    continueHint: 'Press → to continue',
  };
})(window.Applicable = window.Applicable || {});
