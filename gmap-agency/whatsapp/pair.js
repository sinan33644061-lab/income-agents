const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

let qrDisplayed = false;

client.on('qr', (qr) => {
    if (!qrDisplayed) {
        console.log('\n📱 SCAN THIS QR CODE WITH WHATSAPP:');
        console.log('====================================\n');
        qrcode.generate(qr, { small: true });
        console.log('\n====================================');
        console.log('⏳ You have 60 seconds to scan!');
        qrDisplayed = true;
    }
});

client.on('ready', () => {
    console.log('\n✅ WHATSAPP CONNECTED SUCCESSFULLY!');
    console.log('🎉 Pairing complete!');
    process.exit(0);
});

client.on('auth_failure', (msg) => {
    console.error('\n❌ Authentication failed:', msg);
    process.exit(1);
});

client.on('disconnected', (reason) => {
    console.log('\n❌ Disconnected:', reason);
    process.exit(1);
});

console.log('🔄 Initializing WhatsApp...');
client.initialize();

// Keep alive for 90 seconds
setTimeout(() => {
    console.log('\n⏰ Timeout!');
    console.log('💡 If QR didn\'t appear, check your internet connection');
    process.exit(1);
}, 90000);
