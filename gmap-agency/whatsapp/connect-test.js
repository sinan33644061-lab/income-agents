const { default: makeWASocket, useMultiFileAuthState, fetchLatestBaileysVersion, DisconnectReason } = require('@whiskeysockets/baileys');
const pino = require('pino');
const fs = require('fs');
const path = require('path');

const AUTH_DIR = './auth_info';
const WA_SESSION = process.env.WA_SESSION;
const MY_NUMBER = process.env.WA_PHONE_NUMBER;

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

let attempts = 0;
const MAX_ATTEMPTS = 6;

async function connect() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();

  const sock = makeWASocket({
    auth: state,
    version,
    printQRInTerminal: false,
    logger: pino({ level: 'silent' }),
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect } = update;

    if (connection === 'open') {
      log('\n=== RECONNECTED SUCCESSFULLY USING SAVED SESSION ===\n');

      const jid = MY_NUMBER + '@s.whatsapp.net';
      await sock.sendMessage(jid, { text: 'Test message from your gmap-agency outreach agent — session restore works.' });
      log('Sent a test message to your own number. Check your WhatsApp.');

      await new Promise((r) => setTimeout(r, 3000));
      sock.end(undefined);
      process.exit(0);
    }

    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode;

      if (statusCode === DisconnectReason.loggedOut) {
        logErr('Session is logged out — you will need to re-pair.');
        process.exit(1);
      }

      attempts++;
      if (attempts > MAX_ATTEMPTS) {
        logErr(`Gave up after ${MAX_ATTEMPTS} reconnect attempts. Status: ${statusCode}`);
        process.exit(1);
      }

      log(`Connection closed (status ${statusCode}) — this is expected sometimes, reconnecting (attempt ${attempts}/${MAX_ATTEMPTS})...`);
      setTimeout(connect, 3000);
    }
  });
}

if (!WA_SESSION) {
  logErr('WA_SESSION environment variable is missing.');
  process.exit(1);
}

restoreSession();
connect();

setTimeout(() => {
  logErr('\nOverall timeout reached.');
  process.exit(1);
}, 120000);
