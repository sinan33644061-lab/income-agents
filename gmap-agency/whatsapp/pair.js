const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: { headless: true }
});

client.on('qr', (qr) => {
    console.log('📱 SCAN THIS QR CODE WITH WHATSAPP:');
    qrcode.generate(qr, { small: true });
    console.log('⏳ Scan within 60 seconds!');
});

client.on('ready', () => {
    console.log('✅ CONNECTED!');
    process.exit(0);
});

client.initialize();

// Keep alive
setTimeout(() => {}, 60000);
