const { default: makeWASocket, useMultiFileAuthState, fetchLatestBaileysVersion, DisconnectReason } = require('@whiskeysockets/baileys');
const pino = require('pino');
const fs = require('fs');
const path = require('path');

const AUTH_DIR = './auth_info';
const PHONE_NUMBER = process.env.WA_PHONE_NUMBER;

async function main() {
  if (!PHONE_NUMBER) {
    console.error('WA_PHONE_NUMBER environment variable is missing.');
    process.exit(1);
  }

  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();
  console.log('Using WhatsApp Web version:', version.join('.'));

  const sock = makeWASocket({
    auth: state,
    version,
    printQRInTerminal: false,
    logger: pino({ level: 'silent' }),
  });

  sock.ev.on('creds.update', saveCreds);

  let paired = false;

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect } = update;

    if (connection === 'open') {
      console.log('\n=== CONNECTED SUCCESSFULLY ===\n');
      paired = true;

      await new Promise((r) => setTimeout(r, 5000));

      const files = fs.readdirSync(AUTH_DIR);
      const bundle = {};
      for (const file of files) {
        bundle[file] = fs.readFileSync(path.join(AUTH_DIR, file), 'utf8');
      }
      const encoded = Buffer.from(JSON.stringify(bundle)).toString('base64');

      console.log('\n=== COPY THE BLOCK BELOW AS YOUR WA_SESSION SECRET ===\n');
      console.log(encoded);
      console.log('\n=== END OF BLOCK ===\n');

      process.exit(0);
    }

    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
      console.log('Connection closed.', lastDisconnect?.error?.message || lastDisconnect?.error, 'Reconnecting:', shouldReconnect);
      if (!paired) {
        console.error('Disconnected before pairing completed. Re-run this workflow to try again.');
        process.exit(1);
      }
    }
  });

  if (!sock.authState.creds.registered) {
    await new Promise((r) => setTimeout(r, 3000));
    const code = await sock.requestPairingCode(PHONE_NUMBER);
    console.log('\n=== YOUR PAIRING CODE ===\n');
    console.log(code);
    console.log('\nEnter this in WhatsApp on your phone within 60 seconds:');
    console.log('Settings > Linked Devices > Link a Device > Link with phone number instead\n');
  }

  setTimeout(() => {
    if (!paired) {
      console.error('\nTimed out waiting for pairing. Re-run the workflow to try again.');
      process.exit(1);
    }
  }, 180000);
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
