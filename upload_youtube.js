'use strict';

/**
 * YouTube Auto-Uploader  —  SEO Sniper Edition
 *
 * Pipeline:
 *   Agent 1  →  Script Parser        (NVIDIA NIM — Llama 3.3 70B)
 *   Agent 2  →  Trend Intelligence   (Reddit + Google Trends + DuckDuckGo — parallel, free)
 *   Agent 3  →  SEO Generator        (NVIDIA NIM — Mistral Small)
 *   Agent 4  →  Viral Predictor      (NVIDIA NIM — Mistral Small)
 *   Upload   →  youtube-videos-uploader
 *
 * Install / update:
 *   npm install duck-duck-scrape
 *   npm install youtube-videos-uploader@latest   ← also fixes the visibility error
 */

const { upload }    = require('youtube-videos-uploader');
const fs            = require('fs');
const path          = require('path');//
const mammoth       = require('mammoth');
const axios         = require('axios');
const cliProgress   = require('cli-progress');
const googleTrends  = require('google-trends-api');

// duck-duck-scrape is optional — DDG news is skipped if not installed
let ddgSearchNews = null;
try { ({ searchNews: ddgSearchNews } = require('duck-duck-scrape')); }
catch { /* npm install duck-duck-scrape  to enable */ }

// Reddit OAuth token — fetched once per run, cached for the process lifetime (tokens last 1 h)
let _redditToken = null;


// ─────────────────────────────────────────────────────────────────────────────
// CONFIG
// ─────────────────────────────────────────────────────────────────────────────
const CONFIG_PATH = path.join(__dirname, 'upload.config.json');
if (!fs.existsSync(CONFIG_PATH)) {
  console.error(
    '\n❌  upload.config.json not found.\n' +
    '    Copy upload.config.example.json → upload.config.json and fill it in.\n'
  );
  process.exit(1);
}
const cfg = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));

const REQUIRED = [
  ['youtube.email',      cfg.youtube?.email],
  ['youtube.pass',       cfg.youtube?.pass],
  ['nvidia_nim.api_key', cfg.nvidia_nim?.api_key],
  ['paths.script',       cfg.paths?.script],
  ['paths.video_folder', cfg.paths?.video_folder],
];
for (const [k, v] of REQUIRED) {
  if (!v || String(v).startsWith('YOUR_')) {
    console.error(`❌  Missing or placeholder value for "${k}" in upload.config.json`);
    process.exit(1);
  }
}

// NIM model routing — matches seo_sniper.py provider config
const MODEL_PARSE = cfg.nvidia_nim?.model_parse ?? 'meta/llama-3.3-70b-instruct';
const MODEL_SEO   = cfg.nvidia_nim?.model_seo   ?? 'mistralai/mistral-small-4-119b-2603';
const MODEL_VIRAL = cfg.nvidia_nim?.model_viral  ?? 'mistralai/mistral-small-4-119b-2603';


// ─────────────────────────────────────────────────────────────────────────────
// SMALL HELPERS
// ─────────────────────────────────────────────────────────────────────────────
const sleep = ms => new Promise(r => setTimeout(r, ms));

// Progress bar
const bar = new cliProgress.SingleBar(
  {
    format:            '  [{bar}] {percentage}%  ·  {stage}',
    barCompleteChar:   '█',
    barIncompleteChar: '░',
    hideCursor:        true,
  },
  cliProgress.Presets.shades_grey
);
const BS = { active: false, value: 0, stage: '' };   // bar state

function barStart(value = 0, stage = 'Starting…') {
  Object.assign(BS, { active: true, value, stage });
  bar.start(100, value, { stage });
}
function barUpdate(value, stage) {
  Object.assign(BS, { value, stage });
  if (BS.active) bar.update(value, { stage });
}
function barStop() {
  BS.active = false;
  bar.stop();
}

/** Log a line without corrupting the progress bar. */
function log(msg) {
  if (BS.active) bar.stop();
  console.log(msg);
  if (BS.active) bar.start(100, BS.value, { stage: BS.stage });
}


// ─────────────────────────────────────────────────────────────────────────────
// NVIDIA NIM CLIENT  (NIM-only, with retry + rate-limit handling)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Raw NIM call — SSE streaming POST.
 *
 * stream:true means the first token arrives in ~2-5 s even on a congested free-
 * tier; a rolling 60 s stall-timer then catches genuinely dead streams without
 * imposing a hard ceiling on slow-but-alive responses.  This replaces the old
 * non-streaming POST whose 180 s hard timeout fired before the full response
 * arrived on mistralai/mistral-small-4-119b-2603 under load.
 */
async function nimCall(model, messages, maxTokens = 1400,
                       temperature = 0.3, retries = 2) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const res = await axios.post(
        'https://integrate.api.nvidia.com/v1/chat/completions',
        { model, messages, max_tokens: maxTokens, temperature, stream: true },
        {
          headers: {
            Authorization:  `Bearer ${cfg.nvidia_nim.api_key}`,
            'Content-Type': 'application/json',
          },
          responseType:   'stream',
          timeout:        30_000,    // 30 s to receive the first byte; stall-timer below covers the rest
          validateStatus: null,      // inspect status manually so the error body is still readable
        }
      );

      // HTTP error — read the (small) JSON error body from the stream, then surface it
      if (res.status >= 400) {
        const errBody = await new Promise(resolve => {
          let body = '';
          res.data.on('data',  c  => { body += c.toString(); });
          res.data.on('end',   () => resolve(body));
          res.data.on('error', () => resolve(''));
        });
        let detail;
        try { const p = JSON.parse(errBody); detail = p.detail ?? p.message; } catch { /* */ }
        const httpErr    = new Error(detail ?? `HTTP ${res.status}`);
        httpErr.response = { status: res.status };
        throw httpErr;
      }

      // 200 OK — accumulate SSE chunks.  Rolling stall-timer resets on every
      // chunk so a slow-but-alive stream never fires it.
      return await new Promise((resolve, reject) => {
        let text = '';
        let buf  = '';
        let stallTimer;

        const resetStall = () => {
          clearTimeout(stallTimer);
          stallTimer = setTimeout(
            () => reject(new Error('SSE stream stalled — no data for 60 s')),
            60_000
          );
        };
        resetStall();

        res.data.on('data', chunk => {
          resetStall();
          buf += chunk.toString();
          const lines = buf.split('\n');
          buf = lines.pop();         // keep the last (possibly incomplete) line in the buffer

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed === 'data: [DONE]') continue;
            if (!trimmed.startsWith('data: '))          continue;
            try {
              const parsed = JSON.parse(trimmed.slice(6));
              const delta  = parsed.choices?.[0]?.delta?.content;
              if (delta) text += delta;
            } catch { /* malformed SSE chunk — skip silently */ }
          }
        });

        res.data.on('end', () => {
          clearTimeout(stallTimer);
          resolve(text.trim());
        });

        res.data.on('error', err => {
          clearTimeout(stallTimer);
          reject(err);
        });
      });

    } catch (err) {
      const status = err.response?.status ?? 0;
      const detail = err.message;

      log(`⚠️   NIM attempt ${attempt}/${retries}: ${detail}`);

      if      (status === 429) await sleep(Math.min(60_000, 10_000 * attempt));
      else if (status >= 500)  await sleep(2 ** attempt * 1000);
      else if (attempt < retries) await sleep(2 ** attempt * 1000);
      else throw new Error(`NVIDIA NIM error: ${detail}`);
    }
  }
  return '';
}

/** Wrapper that calls NIM and robustly parses the JSON response. */
async function nimJson(model, systemPrompt, userPrompt, maxTokens = 1400) {
  const messages = [
    { role: 'system', content: systemPrompt },
    { role: 'user',   content: userPrompt  },
  ];
  const raw = await nimCall(model, messages, maxTokens, 0.3);
  return raw ? repairJson(raw) : {};
}


// ─────────────────────────────────────────────────────────────────────────────
// 5-STRATEGY JSON REPAIR  (ported from seo_sniper.py _repair_json)
// ─────────────────────────────────────────────────────────────────────────────
function repairJson(raw) {
  const s = raw.trim();

  // ── Strategy 1: direct parse
  try { return JSON.parse(s); } catch { /* continue */ }

  // ── Strategy 2: strip markdown fences  ``` json ... ```
  const clean = s.replace(/```(?:json|JSON)?\s*|\s*```/g, '').trim();
  try { return JSON.parse(clean); } catch { /* continue */ }

  // ── Strategy 3: extract first complete { } block
  const blockMatch = clean.match(/\{[\s\S]*\}/);
  if (blockMatch) { try { return JSON.parse(blockMatch[0]); } catch { /* continue */ } }

  // ── Strategy 4: syntax fixes + char-by-char control-char repair
  let fixed = clean
    .replace(/,\s*([}\]])/g, '$1')   // trailing commas
    .replace(/\bTrue\b/g,  'true')   // Python/AI literals
    .replace(/\bFalse\b/g, 'false')
    .replace(/\bNone\b/g,  'null');

  // Walk char-by-char: escape literal \n \r \t only inside JSON string values
  let repaired = '';
  let inStr = false, esc = false;
  for (const ch of fixed) {
    if (esc)             { repaired += ch; esc = false;         continue; }
    if (ch === '\\' && inStr) { repaired += ch; esc = true;     continue; }
    if (ch === '"')      { repaired += ch; inStr = !inStr;      continue; }
    if (inStr) {
      if      (ch === '\n') { repaired += '\\n';  continue; }
      else if (ch === '\r') { repaired += '\\r';  continue; }
      else if (ch === '\t') { repaired += '\\t';  continue; }
      else if (ch < ' ')    { /* drop other control chars */     continue; }
    }
    repaired += ch;
  }
  try { return JSON.parse(repaired); } catch { /* continue */ }

  // ── Strategy 5: truncation recovery — count unclosed braces and close them
  if (repaired.trimStart().startsWith('{')) {
    let depth = 0, inS = false, e = false;
    for (const ch of repaired) {
      if (e)          { e = false;          continue; }
      if (ch === '\\') { e = true;           continue; }
      if (ch === '"')  { inS = !inS;         continue; }
      if (!inS) {
        if      (ch === '{' || ch === '[') depth++;
        else if (ch === '}' || ch === ']') depth--;
      }
    }
    if (depth > 0) {
      try { return JSON.parse(repaired + '}'.repeat(depth)); } catch { /* fall through */ }
    }
  }

  log('⚠️   JSON repair exhausted all 5 strategies — returning {}');
  return {};
}


// ─────────────────────────────────────────────────────────────────────────────
// DOCX READER
// ─────────────────────────────────────────────────────────────────────────────
async function readDocxScript() {
  // Resolve relative to the config file's directory so "./pod1.docx" works
  const p = path.resolve(path.dirname(CONFIG_PATH), cfg.paths.script);
  if (!fs.existsSync(p)) throw new Error(`Script not found: ${p}`);
  const { value } = await mammoth.extractRawText({ path: p });
  if (!value.trim()) throw new Error('Script file is empty.');
  return value.trim();
}


// ─────────────────────────────────────────────────────────────────────────────
// SUBREDDIT MAP  (from seo_sniper.py)
// ─────────────────────────────────────────────────────────────────────────────
const SUBREDDIT_MAP = {
  'dark psychology':  ['psychology', 'manipulation', 'socialengineering', 'NarcissisticAbuse'],
  'psychology':       ['psychology', 'socialpsychology', 'AskPsychology', 'cognitivescience'],
  'true crime':       ['TrueCrime', 'unresolvedmysteries', 'criminalminds', 'serialkillers'],
  'self improvement': ['selfimprovement', 'productivity', 'getmotivated', 'DecidingToBeBetter'],
  'relationships':    ['relationships', 'relationship_advice', 'NarcissisticAbuse', 'dating_advice'],
  'ai':               ['artificial', 'MachineLearning', 'LocalLLaMA', 'ChatGPT'],
  'technology':       ['technology', 'Futurology', 'gadgets', 'hardware'],
  'finance':          ['personalfinance', 'investing', 'wallstreetbets', 'financialindependence'],
  'health':           ['health', 'fitness', 'nutrition', 'loseit'],
  'gaming':           ['gaming', 'pcgaming', 'games', 'IndieGaming'],
  'animation':        ['animation', 'AnimationCareer', 'learnanimation', 'blender'],
  'history':          ['history', 'AskHistorians', 'HistoryMemes', 'worldhistory'],
  'conspiracy':       ['conspiracy', 'conspiracy_commons', 'highstrangeness'],
  'spiritual':        ['spirituality', 'Meditation', 'awakened', 'metaphysics'],
  'default':          ['videos', 'youtube', 'OutOfTheLoop', 'TIL'],
};

function getSubreddits(niche = '') {
  const lc = niche.toLowerCase();
  const entry = Object.entries(SUBREDDIT_MAP).find(([k]) => lc.includes(k));
  return entry ? entry[1] : SUBREDDIT_MAP.default;
}


// ─────────────────────────────────────────────────────────────────────────────
// REDDIT OAUTH  (application-only client_credentials flow — no user login)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Exchange client_id + client_secret for a Bearer token.
 * Returns null (and logs a warning) when credentials are absent or the
 * request fails — callers fall back to the unauthenticated public API.
 */
async function getRedditToken() {
  if (_redditToken) return _redditToken;   // already fetched this run

  const { client_id, client_secret, user_agent } = cfg.reddit ?? {};
  if (!client_id || !client_secret) {
    log('ℹ️   Reddit credentials not in config — using public API (may 403)');
    return null;
  }

  try {
    const res = await axios.post(
      'https://www.reddit.com/api/v1/access_token',
      'grant_type=client_credentials',
      {
        auth:    { username: client_id, password: client_secret },
        headers: {
          'User-Agent':   user_agent ?? 'upload-youtube-seo-sniper/2.0',
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        timeout: 10_000,
      }
    );
    _redditToken = res.data.access_token;
    log('✅  Reddit OAuth token acquired');
    return _redditToken;
  } catch (e) {
    log(`⚠️   Reddit OAuth failed: ${e.message} — falling back to public API`);
    return null;
  }
}


// ─────────────────────────────────────────────────────────────────────────────
// REDDIT SCRAPER  (free JSON API — no key needed)
// ─────────────────────────────────────────────────────────────────────────────
async function scrapeReddit(queries, niche) {
  log('🟠  Reddit: searching hot posts…');

  const token     = await getRedditToken();
  const userAgent = cfg.reddit?.user_agent ?? 'Mozilla/5.0 (compatible; upload-youtube-seo-sniper/2.0; +research)';

  const headers = {
    'User-Agent': userAgent,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  // Authenticated requests go to oauth.reddit.com (proper API, no bot-detection).
  // Unauthenticated fall back to www.reddit.com with raw_json=1 to force JSON.
  const base   = token ? 'https://oauth.reddit.com' : 'https://www.reddit.com';
  const suffix = token ? '' : '&raw_json=1';

  const subs      = getSubreddits(niche);
  const endpoints = [
    // Subreddit hot feeds first — more reliable than search for unauthenticated requests
    ...subs.slice(0, 3).map(sub =>
      `${base}/r/${sub}/hot.json?limit=10${suffix}`
    ),
    // Keyword search as secondary
    ...queries.slice(0, 2).map(q =>
      `${base}/search.json?q=${encodeURIComponent(q)}&sort=hot&limit=8&t=week${suffix}`
    ),
  ];

  const results = [];
  for (const url of endpoints) {
    try {
      const r = await axios.get(url, { headers, timeout: 12_000 });
      if (r.status === 429) { log('⚠️   Reddit rate-limited — stopping early'); break; }
      // Guard: Reddit sometimes serves HTML (bot-detection wall) as a 200; data won't have .data
      if (typeof r.data !== 'object') { log('⚠️   Reddit: non-JSON response (bot-detection?) — skipping'); continue; }
      for (const p of (r.data?.data?.children ?? [])) {
        const d = p.data ?? {};
        if (d.title) results.push({
          title:       d.title,
          score:       d.score       ?? 0,
          subreddit:   d.subreddit   ?? '',
          numComments: d.num_comments ?? 0,
        });
      }
    } catch (e) { log(`⚠️   Reddit endpoint failed: ${e.message}`); }
    await sleep(800);   // polite delay between requests
  }

  // Deduplicate by title, sort by Reddit score
  const seen = new Set();
  return results
    .filter(r => { if (seen.has(r.title)) return false; seen.add(r.title); return true; })
    .sort((a, b) => b.score - a.score)
    .slice(0, 18);
}


// ─────────────────────────────────────────────────────────────────────────────
// GOOGLE TRENDS  (google-trends-api — no key needed)
// ─────────────────────────────────────────────────────────────────────────────
async function scrapeGoogleTrends(keywords) {
  log('📈  Google Trends: fetching rising + top queries…');
  await sleep(3000);   // 3 s pause reduces Google 429 bot-detection (from seo_sniper.py)

  const out = { available: false, risingQueries: [], topQueries: [] };

  for (const kw of (keywords ?? []).filter(Boolean).slice(0, 5)) {
    try {
      const raw   = await googleTrends.relatedQueries({ keyword: kw });
      const lists = JSON.parse(raw)?.default?.rankedList ?? [];

      // rankedList[0] = top queries, rankedList[1] = rising queries
      for (const item of (lists[0]?.rankedKeyword ?? []).slice(0, 6)) {
        if (item.query) out.topQueries.push(item.query);
      }
      for (const item of (lists[1]?.rankedKeyword ?? []).slice(0, 6)) {
        if (item.query) out.risingQueries.push(item.query);
      }
    } catch { /* skip per-keyword failures */ }
  }

  out.risingQueries = [...new Set(out.risingQueries)];
  out.topQueries    = [...new Set(out.topQueries)];
  out.available     = (out.risingQueries.length + out.topQueries.length) > 0;
  return out;
}


// ─────────────────────────────────────────────────────────────────────────────
// DUCKDUCKGO NEWS  (duck-duck-scrape — no key needed)
// ─────────────────────────────────────────────────────────────────────────────
async function scrapeDDGNews(queries) {
  if (!ddgSearchNews) {
    log('⚠️   duck-duck-scrape not installed → DDG skipped  (run: npm install duck-duck-scrape)');
    return [];
  }
  log('🦆  DuckDuckGo: fetching news headlines…');

  const results     = [];
  const seenQueries = new Set();

  // Pre-filter: DDG 503s on single-word queries — require at least 2 words
  const multiWord = queries.filter(q => q && q.trim().split(/\s+/).length >= 2);

  // Deduplicate queries case-insensitively (seo_sniper.py: prevents instant 403)
  const unique = multiWord.slice(0, 3).filter(q => {
    if (seenQueries.has(q.toLowerCase())) return false;
    seenQueries.add(q.toLowerCase());
    return true;
  });

  if (!unique.length) {
    log('ℹ️   DDG skipped — no multi-word queries in this set');
    return [];
  }

  for (const q of unique.slice(0, 2)) {   // max 2 queries to stay under DDG rate limit
    let attempt = 0;
    while (attempt < 2) {
      try {
        const news = await ddgSearchNews(q, { safeSearch: -2 });
        for (const item of (news?.results ?? []).slice(0, 8)) {
          results.push({
            title:  item.title        ?? '',
            source: item.syndicate    ?? '',
            date:   item.relativeTime ?? '',
            url:    item.url          ?? '',
          });
        }
        break;   // success — move to next query
      } catch (e) {
        attempt++;
        const isServerErr = e.message.toLowerCase().includes('server error');
        if (isServerErr && attempt < 2) {
          log(`⚠️   DDG server error for "${q}" — retrying in 5 s…`);
          await sleep(5_000);
        } else {
          log(`⚠️   DDG error for "${q}": ${e.message}`);
          break;   // give up on this query — avoid cascading 403s
        }
      }
    }
    await sleep(2500);   // 2.5 s between DDG queries (from seo_sniper.py)
  }

  return results.slice(0, 20);
}


// ─────────────────────────────────────────────────────────────────────────────
// AGENT 1 — SCRIPT PARSER  (prompts ported from seo_sniper.py)
// ─────────────────────────────────────────────────────────────────────────────
const A1_SYS =
  'You are a professional YouTube content analyst. ' +
  'Extract structured metadata from video scripts. ' +
  'Respond with valid JSON only — no markdown, no preamble.';

async function agent1_parseScript(scriptText) {
  log('\n🔍  [Agent 1/4] Script Parser — analyzing content…');

  const result = await nimJson(MODEL_PARSE, A1_SYS,
`Analyze this YouTube video script and extract ALL metadata fields below.

SCRIPT (first 6000 chars):
${scriptText.slice(0, 6000)}

Return EXACTLY this JSON (no extra keys, fill every field):
{
  "main_topic": "short topic name",
  "content_summary": "2-3 sentence summary",
  "niche": "primary niche",
  "sub_niche": "specific sub-niche",
  "content_type": "educational|story|tutorial|commentary|review|entertainment",
  "tone": "dark|inspirational|informative|shocking|calm|humorous",
  "target_audience": "who this appeals to",
  "estimated_duration_mins": 8,
  "key_entities": ["people/brands/places mentioned"],
  "main_topics": ["topic1", "topic2", "topic3"],
  "subtopics": ["sub1", "sub2", "sub3", "sub4"],
  "core_message": "one sentence takeaway",
  "emotional_triggers": ["curiosity", "fear", "trust", "urgency"],
  "unique_angle": "what makes this video different from others on the topic",
  "content_pillars": ["pillar1", "pillar2"],
  "seed_keywords": ["8 keywords that naturally appear or fit the script"],
  "related_searches": ["what viewers would search after watching — 6 phrases"],
  "competitor_topics": ["similar videos already on YouTube — 4 examples"],
  "difficulty_level": "beginner|intermediate|advanced"
}`, 1200);

  if (!result?.main_topic) {
    log('⚠️   Script parsing returned minimal data — using fallback values');
    return {
      main_topic: 'general', niche: 'general', sub_niche: 'general',
      content_type: 'educational', tone: 'informative',
      target_audience: 'general audience', estimated_duration_mins: 8,
      core_message: '', unique_angle: '', content_summary: '',
      seed_keywords: [], subtopics: [], emotional_triggers: [],
      main_topics: [], key_entities: [],
    };
  }

  log(`📌  Topic: ${result.main_topic}  ·  Niche: ${result.niche}`);
  log(`🎯  Core message: ${result.core_message || '(not extracted)'}`);
  log(`😮  Emotional hooks: ${(result.emotional_triggers ?? []).join(', ') || '(none)'}`);
  return result;
}


// ─────────────────────────────────────────────────────────────────────────────
// AGENT 2 — TREND INTELLIGENCE  (3 sources, fully parallel)
// ─────────────────────────────────────────────────────────────────────────────
async function agent2_collectTrends(scriptData) {
  log('\n🌐  [Agent 2/4] Trend Intelligence — running all sources in parallel…');

  const mainTopic = scriptData.main_topic   ?? '';
  const niche     = scriptData.niche        ?? '';
  const seedKws   = scriptData.seed_keywords ?? [];
  const subtopics = scriptData.subtopics     ?? [];

  // Build deduplicated query list (same logic as seo_sniper.py agent_collect_trends)
  const queries = [
    ...new Set([mainTopic, ...seedKws.slice(0, 3), ...subtopics.slice(0, 2)].filter(Boolean))
  ].slice(0, 5);

  // Run all 3 scrapers simultaneously — total time ≈ slowest single source
  const [rReddit, rTrends, rDDG] = await Promise.allSettled([
    scrapeReddit(queries, niche),
    scrapeGoogleTrends(seedKws.length ? seedKws.slice(0, 5) : [mainTopic]),
    scrapeDDGNews(queries),
  ]);

  const reddit  = rReddit.status  === 'fulfilled' ? rReddit.value  : [];
  const gtrends = rTrends.status  === 'fulfilled' ? rTrends.value  :
                  { available: false, risingQueries: [], topQueries: [] };
  const ddgNews = rDDG.status     === 'fulfilled' ? rDDG.value     : [];

  log(`\n📊  Sources: Reddit ${reddit.length} posts  ·  Trends ${gtrends.available ? '✓' : '✗'}  ·  DDG ${ddgNews.length} articles`);

  return {
    queriesUsed:   queries,
    reddit,
    googleTrends:  gtrends,
    ddgNews,
    sourceCounts:  { reddit: reddit.length, ddg: ddgNews.length },
  };
}


// ─────────────────────────────────────────────────────────────────────────────
// AGENT 3 — SEO GENERATOR  (prompts ported from seo_sniper.py)
// ─────────────────────────────────────────────────────────────────────────────
const A3_SYS =
  'You are a senior YouTube SEO strategist with 10+ years growing channels ' +
  'to millions of subscribers. You understand CTR psychology, YouTube search ' +
  'algorithms, keyword clustering, and tag architecture. ' +
  'Respond with valid JSON only — no markdown, no preamble. ' +
  'Every string value must be on ONE LINE — use \\n for paragraph breaks.';

async function agent3_generateSEO(scriptData, trends) {
  log('\n🎯  [Agent 3/4] SEO Generator — crafting titles, tags & description…');

  const redditTitles = trends.reddit.slice(0, 6).map(r => r.title);
  const risingQry    = trends.googleTrends.risingQueries ?? [];
  const topQry       = trends.googleTrends.topQueries    ?? [];
  const newsTitles   = trends.ddgNews.slice(0, 5).map(n => n.title);

  return await nimJson(MODEL_SEO, A3_SYS,
`Generate complete YouTube SEO optimization for this video.

== SCRIPT ANALYSIS ==
Topic         : ${scriptData.main_topic}
Niche         : ${scriptData.niche} / ${scriptData.sub_niche}
Content Type  : ${scriptData.content_type}
Core Message  : ${scriptData.core_message}
Seed Keywords : ${JSON.stringify(scriptData.seed_keywords ?? [])}
Subtopics     : ${JSON.stringify(scriptData.subtopics ?? [])}
Unique Angle  : ${scriptData.unique_angle}
Audience      : ${scriptData.target_audience}

== LIVE TREND DATA ==
Reddit hot titles     : ${JSON.stringify(redditTitles)}
Rising Google queries : ${JSON.stringify(risingQry)}
Top Google queries    : ${JSON.stringify(topQry)}
Recent news headlines : ${JSON.stringify(newsTitles)}

== INSTRUCTIONS ==
- Primary title: under 70 chars, front-load main keyword, use power words
- Description: 450-500 words, keyword-dense first 150 chars, include timestamp skeleton
- Generate exactly 40 tags mixing: broad, specific, trending, long-tail
- Competitor-gap tags = tags competitors in this niche consistently miss

CRITICAL JSON RULES:
- Every string value on ONE LINE
- Use \\n\\n for paragraph breaks inside full_text
- No markdown, no preamble, output must pass JSON.parse()

{
  "titles": {
    "primary": "best title under 70 chars",
    "alternatives": [
      "curiosity-gap formula variant",
      "number/list formula e.g. 7 Signs...",
      "shock/controversy variant"
    ],
    "title_score": 85,
    "title_analysis": "why this title works"
  },
  "description": {
    "full_text": "450-500 word SEO description. First sentence contains primary keyword. Use \\n\\n between paragraphs. End with 3-5 hashtags.",
    "first_line_hook": "first 150 chars — compelling and keyword-rich",
    "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
  },
  "tags": {
    "primary_tags":        ["5 exact-match high-priority tags"],
    "secondary_tags":      ["10 related broad topic tags"],
    "long_tail_tags":      ["10 specific 3-5 word phrases viewers actually search"],
    "trending_tags":       ["5 tags from current trending data above"],
    "competitor_gap_tags": ["5 tags competitors consistently miss"],
    "all_tags":            ["complete merged deduplicated list of 40 tags, priority ordered"]
  }
}`, 1600) ?? {};
}


// ─────────────────────────────────────────────────────────────────────────────
// AGENT 4 — VIRAL PREDICTOR  (prompts ported from seo_sniper.py)
// ─────────────────────────────────────────────────────────────────────────────
const A4_SYS =
  'You are a viral content analyst who has studied 50,000+ YouTube videos ' +
  'across all niches. You understand psychological triggers, algorithm signals, ' +
  'and timing factors that determine virality. You are brutally honest about ' +
  'viral potential and give specific, actionable recommendations. ' +
  'Respond with valid JSON only — no markdown, no preamble. ' +
  'Every string value must be on ONE LINE — use \\n for line breaks.';

async function agent4_predictViral(scriptData, seoData, trends) {
  log('\n🚀  [Agent 4/4] Viral Predictor — scoring viral potential…');

  const primaryTitle = seoData?.titles?.primary        ?? 'N/A';
  const viralTags    = seoData?.tags?.trending_tags    ?? [];
  const risingQry    = trends.googleTrends.risingQueries ?? [];
  const redditScores = trends.reddit.slice(0, 5).map(r => [r.title, r.score]);

  const result = await nimJson(MODEL_VIRAL, A4_SYS,
`Analyze this YouTube video's viral potential with brutal honesty.

== VIDEO METADATA ==
Topic           : ${scriptData.main_topic}
Niche           : ${scriptData.niche}
Primary Title   : ${primaryTitle}
Core Message    : ${scriptData.core_message}
Unique Angle    : ${scriptData.unique_angle}
Emotional Hooks : ${JSON.stringify(scriptData.emotional_triggers ?? [])}
Duration (est.) : ${scriptData.estimated_duration_mins} min
Content Type    : ${scriptData.content_type}

== TREND ALIGNMENT ==
Rising searches  : ${JSON.stringify(risingQry)}
Hot Reddit posts : ${JSON.stringify(redditScores)}
Trending tags    : ${JSON.stringify(viralTags)}

== SCORING GUIDE (be honest, not flattering) ==
- trend_alignment:  0-20  (how well topic aligns with what is trending RIGHT NOW)
- title_strength:   0-20  (CTR potential — brutal honest assessment)
- emotional_impact: 0-20  (strength of emotional triggers in the content)
- search_demand:    0-20  (search volume + competition ratio)
- timing_score:     0-20  (how timely/seasonal this topic is)
- viral_score = sum of all five (0-100)

{
  "viral_score": 78,
  "confidence": "high|medium|low",
  "verdict": "one-sentence honest assessment",
  "score_breakdown": {
    "trend_alignment":  14,
    "title_strength":   16,
    "emotional_impact": 18,
    "search_demand":    15,
    "timing_score":     15,
    "analysis": "2-3 sentence explanation of the scores"
  },
  "best_upload_times": {
    "best_days":   ["Thursday", "Friday"],
    "time_window": "14:00-17:00 UTC",
    "avoid_days":  ["Monday", "Tuesday"],
    "reasoning":   "why these times work for this niche"
  },
  "predicted_performance": {
    "views_48h":       "500-2,000",
    "views_7d":        "2,000-8,000",
    "ctr_estimate":    "4-7%",
    "growth_catalyst": "what could push this to 10x views"
  },
  "critical_improvements": [
    "most important change to increase viral potential",
    "second most important change",
    "third most important change"
  ]
}`, 1400) ?? {};

  // Clamp viral_score to 0-100 (from seo_sniper.py _validate_output)
  if (result.viral_score !== undefined) {
    result.viral_score = Math.max(0, Math.min(100, parseInt(result.viral_score) || 0));
  }
  return result;
}


// ─────────────────────────────────────────────────────────────────────────────
// MAIN  —  full pipeline + upload
// ─────────────────────────────────────────────────────────────────────────────
async function uploadProcess() {
  console.log('\n🚀  YouTube Auto-Uploader  ·  SEO Sniper Edition\n');
  barStart(0, 'Starting…');

  try {
    // ── Stage 1: Read script ───────────────────────────────────────────────
    barUpdate(5, 'Reading script…');
    const scriptText = await readDocxScript();
    barUpdate(12, 'Script loaded');
    log(`✅  Script: ${scriptText.length.toLocaleString()} chars`);

    barStop();   // pause bar — agents produce their own log lines

    // ── Agent 1 ────────────────────────────────────────────────────────────
    const scriptData = await agent1_parseScript(scriptText);
    barStart(25, 'Agent 1 done');

    // ── Agent 2 ────────────────────────────────────────────────────────────
    barUpdate(25, 'Collecting trends…');
    barStop();
    const trends = await agent2_collectTrends(scriptData);
    barStart(50, 'Trends collected');

    // ── Agent 3 ────────────────────────────────────────────────────────────
    barUpdate(50, 'Generating SEO…');
    barStop();
    const seoData = await agent3_generateSEO(scriptData, trends);
    barStart(65, 'SEO done');

    // ── Agent 4 ────────────────────────────────────────────────────────────
    barUpdate(65, 'Predicting virality…');
    barStop();
    const viralData = await agent4_predictViral(scriptData, seoData, trends);
    barStart(75, 'Analysis complete');

    // ── Extract upload metadata ────────────────────────────────────────────
    // Enforce title character limit (from seo_sniper.py _validate_output)
    let title = seoData?.titles?.primary ?? scriptData.main_topic ?? 'Untitled';
    if (title.length > 70) {
      const cut = title.slice(0, 70);
      const sp  = cut.lastIndexOf(' ');
      title = sp > 40 ? cut.slice(0, sp) : cut;
    }

    const description = seoData?.description?.full_text ?? '';
    // Enforce YouTube's 500-character hard limit on total tag string.
    // Greedily pack tags in priority order; drop any tag that would push past the limit.
    const rawTags = seoData?.tags?.all_tags ?? [];
    const tags = [];
    let tagChars = 0;
    for (const t of rawTags) {
      const cost = (tags.length ? 2 : 0) + t.length;   // 2 = ", " separator
      if (tagChars + cost > 500) break;
      tags.push(t);
      tagChars += cost;
    }
    if (rawTags.length > tags.length)
      log(`ℹ️   Tags capped: kept ${tags.length}/${rawTags.length} (${tagChars}/500 chars)`);
    const viralScore  = viralData?.viral_score ?? '?';
    const verdict     = viralData?.verdict     ?? '';
    const bestDay     = viralData?.best_upload_times?.best_days?.[0] ?? 'N/A';
    const timeWindow  = viralData?.best_upload_times?.time_window    ?? '';
    const views7d     = viralData?.predicted_performance?.views_7d   ?? 'N/A';
    const topTag      = tags[0] ?? 'N/A';

    // Summary banner — mirrors seo_sniper.py output
    console.log('\n' + '═'.repeat(62));
    console.log(`  🏆  TITLE       ${title}`);
    console.log(`  🔥  VIRAL SCORE ${viralScore}/100  —  ${verdict}`);
    console.log(`  🏷️   TOP TAG     ${topTag}`);
    console.log(`  📅  UPLOAD      ${bestDay}  ${timeWindow}`);
    console.log(`  📈  VIEWS (7d)  ${views7d}`);
    console.log('═'.repeat(62) + '\n');

    // ── Select video file ──────────────────────────────────────────────────
    barUpdate(78, 'Selecting video…');
    const videoDir  = path.resolve(path.dirname(CONFIG_PATH), cfg.paths.video_folder);
    const videoList = fs.readdirSync(videoDir).filter(f => f.toLowerCase().endsWith('.mp4'));
    if (!videoList.length) throw new Error(`No .mp4 files found in: ${videoDir}`);

    const chosen    = videoList[Math.floor(Math.random() * videoList.length)];
    const videoPath = path.join(videoDir, chosen);
    log(`🎬  Selected: ${chosen}`);

    // ── Upload ─────────────────────────────────────────────────────────────
    barUpdate(80, 'Uploading to YouTube…');
    barStop();
    console.log('\n⏳  Uploading — live % is shown in the browser window.\n');

    let videoUrls;
    try {
      videoUrls = await upload(
        { email: cfg.youtube.email, pass: cfg.youtube.pass },
        [{
          path:               videoPath,
          title,
          description,
          tags,
          language:           cfg.upload?.language            ?? 'english',
          channelName:        cfg.upload?.channel_name        ?? '',
          skipProcessingWait: true,
          publishType:        cfg.upload?.publish_type        ?? 'PUBLIC',
          isAgeRestriction:   cfg.upload?.is_age_restriction  ?? false,
          isNotForKid:        cfg.upload?.is_not_for_kid      ?? true,
        }],
        {
          headless: false,
          timeout:  300_000,   // 5 min — more time for YouTube UI to load
        }
      );

    } catch (uploadErr) {
      // ── Visibility error: YouTube Studio setup is missing ────────────────
      // The library cannot find the publish-type dropdown. This is not a code
      // bug — it means YouTube Studio's upload defaults are not configured.
      if (uploadErr.message.toLowerCase().includes('visibility')) {
        throw new Error(
          'YouTube visibility setup error — the library cannot find the publish dropdown.\n\n' +
          '  Fix (takes 2 minutes):\n' +
          '  1.  Open  https://studio.youtube.com\n' +
          '  2.  Click  Settings  →  Upload defaults  →  Basic info\n' +
          '  3.  Set the "Visibility" field to "Public"  →  Save\n' +
          '  4.  Re-run this script.\n\n' +
          '  If the error persists, the YouTube UI may have changed —\n' +
          '  update the library:  npm install youtube-videos-uploader@latest'
        );
      }
      throw uploadErr;
    }

    // ── Archive video ──────────────────────────────────────────────────────
    barStart(90, 'Archiving…');
    const uploadedDir = path.resolve(path.dirname(CONFIG_PATH), cfg.paths.uploaded_folder);
    fs.mkdirSync(uploadedDir, { recursive: true });

    const counterFile = path.join(uploadedDir, 'video_counter.txt');
    const counter     = fs.existsSync(counterFile)
      ? parseInt(fs.readFileSync(counterFile, 'utf-8'), 10) + 1 : 1;

    const archiveName = `video_${counter}.mp4`;
    fs.renameSync(videoPath, path.join(uploadedDir, archiveName));
    fs.writeFileSync(counterFile, String(counter));

    barUpdate(100, '✅  Done!');
    barStop();

    console.log(`\n✅  Upload complete!  Archived as: ${archiveName}`);
    console.log(`📺  URL(s): ${Array.isArray(videoUrls) ? videoUrls.join(', ') : videoUrls}\n`);

  } catch (err) {
    if (BS.active) barStop();
    // Indent every line of the error message for readability
    console.error('\n❌  Error:\n' + err.message.split('\n').map(l => '    ' + l).join('\n') + '\n');
    process.exit(1);
  }
}

uploadProcess();