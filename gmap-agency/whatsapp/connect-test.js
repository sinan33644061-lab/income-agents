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
  const bundle = JSON.parse(Buffer.from(WA_SESSION, 'base64').toString('utf8'));
  for (const [filename, content] of Object.entries(bundle)) {
    fs.writeFileSync(path.join(AUTH_DIR, filename), content, 'utf8');
  }
}

async function main() {
  if (!WA_SESSION) {
    logErr('WA_SESSION environment variable is missing.');
    process.exit(1);
  }

  restoreSession();

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
      logErr('Connection closed. Status: ' + statusCode);
      if (statusCode === DisconnectReason.loggedOut) {
        logErr('Session is logged out — you will need to re-pair.');
      }
      process.exit(1);
    }
  });
}

main().catch((err) => {
  logErr('Fatal error: ' + err);
  process.exit(1);
});
