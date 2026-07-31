const { default: makeWASocket, useMultiFileAuthState, fetchLatestBaileysVersion, DisconnectReason } = require('@whiskeysockets/baileys');
const pino = require('pino');
const fs = require('fs');
const path = require('path');

const AUTH_DIR = './auth_info';
const WA_SESSION = process.env.WA_SESSION;
const MY_NUMBER = process.env.WA_PHONE_NUMBER;
const DAILY_LIMIT = parseInt(process.env.DAILY_LIMIT || '15', 10);
const LEADS_FILE = '../leads.json';
const REPLY_WAIT_MS = 15000;

function log(msg) { fs.writeSync(1, msg + '\n'); }
function logErr(msg) { fs.writeSync(2, msg + '\n'); }

function restoreSession() {
  if (!fs.existsSync(AUTH_DIR)) fs.mkdirSync(AUTH_DIR, { recursive: true });
  const cleaned = WA_SESSION.replace(/\s+/g, '');
  const bundle = JSON.parse(Buffer.from(cleaned, 'base64').toString('utf8'));
  for (const [filename, content] of Object.entries(bundle)) {
    fs.writeFileSync(path.join(AUTH_DIR, filename), content, 'utf8');
  }
}

function randomDelay(minMs, maxMs) {
  return new Promise((r) => setTimeout(r, minMs + Math.random() * (maxMs - minMs)));
}

function messageFor(lead) {
  return `Hi! I noticed ${lead.name} doesn't have a website yet, so I put together a free demo of what one could look like: ${lead.demo_url}\n\nTake a look — happy to make it official if you like it.`;
}

async function main() {
  if (!WA_SESSION || !MY_NUMBER) {
    logErr('WA_SESSION or WA_PHONE_NUMBER missing.');
    process.exit(1);
  }

  restoreSession();

  const leads = JSON.parse(fs.readFileSync(LEADS_FILE, 'utf8'));
  const phoneToLead = {};
  for (const lead of leads) {
    if (lead.phone) {
      const digits = lead.phone.replace(/\D/g, '');
      if (digits) phoneToLead[digits] = lead;
    }
  }

  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();

  const sock = makeWASocket({
    auth: state,
    version,
    printQRInTerminal: false,
    logger: pino({ level: 'silent' }),
  });

  sock.ev.on('creds.update', saveCreds);

  let repliesFound = 0;

  sock.ev.on('messages.upsert', async ({ messages }) => {
    for (const msg of messages) {
      if (msg.key.fromMe) continue;
      const senderJid = msg.key.remoteJid || '';
      const senderNumber = senderJid.split('@')[0];
      const text = msg.message?.conversation
        || msg.message?.extendedTextMessage?.text
        || '(non-text message)';

      const matchedLead = phoneToLead[senderNumber];
      if (matchedLead) {
        matchedLead.status = 'replied';
      }

      repliesFound++;
      const label = matchedLead ? matchedLead.name : senderNumber;
      try {
        await sock.sendMessage(MY_NUMBER + '@s.whatsapp.net', {
          text: `New reply from ${label} (${senderNumber}):\n\n${text}`,
        });
      } catch (e) {
        logErr('Failed to forward notification: ' + e.message);
      }
    }
  });

  await new Promise((resolve, reject) => {
    sock.ev.on('connection.update', (update) => {
      if (update.connection === 'open') resolve();
      if (update.connection === 'close') {
        const statusCode = update.lastDisconnect?.error?.output?.statusCode;
        reject(new Error('Connection closed before opening, status: ' + statusCode));
      }
    });
  });

  log('=== CONNECTED ===');
  log('Waiting to catch any queued replies...');
  await new Promise((r) => setTimeout(r, REPLY_WAIT_MS));
  log(`Replies detected this run: ${repliesFound}`);

  const todo = leads.filter((l) => l.channel === 'whatsapp' && l.status === 'built').slice(0, DAILY_LIMIT);
  log(`Sending outreach to ${todo.length} leads (daily limit: ${DAILY_LIMIT})`);

  let sentCount = 0;
  for (const lead of todo) {
    const digits = lead.phone.replace(/\D/g, '');
    const jid = digits + '@s.whatsapp.net';
    try {
      await sock.sendMessage(jid, { text: messageFor(lead) });
      lead.status = 'contacted';
      lead.contacted_at = new Date().toISOString();
      sentCount++;
      log(`Sent to ${lead.name} (${lead.area})`);
    } catch (e) {
      log(`Failed to send to ${lead.name}: ${e.message}`);
    }
    await randomDelay(45000, 120000);
  }

  log(`Sent ${sentCount} messages this run.`);

  fs.writeFileSync(LEADS_FILE, JSON.stringify(leads, null, 2), 'utf8');
  log('leads.json updated.');

  await new Promise((r) => setTimeout(r, 3000));
  sock.end(undefined);
  process.exit(0);
}

main().catch((err) => {
  logErr('Fatal error: ' + err.message);
  process.exit(1);
});
