const { default: makeWASocket, useMultiFileAuthState, fetchLatestBaileysVersion, DisconnectReason } = require('@whiskeysockets/baileys');
const pino = require('pino');
const fs = require('fs');
const path = require('path');

const AUTH_DIR = './auth_info';
const PHONE_NUMBER = process.env.WA_PHONE_NUMBER;

function log(msg) {
  fs.writeSync(1, msg + '\n');
}
function logErr(msg) {
  fs.writeSync(2, msg + '\n');
}

let codeRequested = false;
let attempts = 0;
const MAX_RECONNECTS = 5;

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

    if (connection === 'connecting' && !sock.authState.creds.registered && !codeRequested) {
      codeRequested = true;
      await new Promise((r) => setTimeout(r, 2000));
      const code = await sock.requestPairingCode(PHONE_NUMBER);
      log('\n=== YOUR PAIRING CODE ===');
      log(code);
      log('\nEnter this in WhatsApp on your phone right now:');
      log('Settings > Linked Devices > Link a Device > Link with phone number instead\n');
    }

    if (connection === 'open') {
      log('\n=== CONNECTED SUCCESSFULLY ===\n');
      await new Promise((r) => setTimeout(r, 5000));

      const files = fs.readdirSync(AUTH_DIR);
      const bundle = {};
      for (const file of files) {
        bundle[file] = fs.readFileSync(path.join(AUTH_DIR, file), 'utf8');
      }
      const encoded = Buffer.from(JSON.stringify(bundle)).toString('base64');

      log('\n=== COPY THE BLOCK BELOW AS YOUR WA_SESSION SECRET ===\n');
      log(encoded);
      log('\n=== END OF BLOCK ===\n');

      process.exit(0);
    }

    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const loggedOut = statusCode === DisconnectReason.loggedOut;

      if (loggedOut) {
        logErr('Logged out — need a completely fresh pairing. Re-run the workflow.');
        process.exit(1);
      }

      attempts++;
      if (attempts > MAX_RECONNECTS) {
        logErr('Too many reconnect attempts. Re-run the workflow to try again.');
        process.exit(1);
      }

      log('Reconnecting to finish pairing (this is normal right after entering the code)...');
      setTimeout(connect, 2000);
    }
  });
}

if (!PHONE_NUMBER) {
  logErr('WA_PHONE_NUMBER environment variable is missing.');
  process.exit(1);
}

connect();

setTimeout(() => {
  logErr('\nOverall timeout reached. Re-run the workflow to try again.');
  process.exit(1);
}, 240000);
