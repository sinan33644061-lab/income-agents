const { Client, LocalAuth } = require('whatsapp-web.js');

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: { headless: true }
});

let otpReceived = false;

// When OTP arrives
client.on('authenticated', () => {
    console.log('✅ OTP RECEIVED!');
    otpReceived = true;
    process.exit(0); // Exit immediately
});

client.on('ready', () => {
    console.log('✅ Ready!');
    process.exit(0);
});

client.on('auth_failure', (msg) => {
    console.error('❌ Failed:', msg);
    process.exit(1);
});

console.log('⏳ Waiting for OTP... (Keep this running)');
client.initialize();

// Force wait - keeps script alive
const waitForOTP = setInterval(() => {
    if (!otpReceived) {
        console.log('⏳ Still waiting for OTP...');
    }
}, 5000);

// Timeout after 60 seconds
setTimeout(() => {
    clearInterval(waitForOTP);
    console.log('❌ Timeout - OTP not received in 60s');
    process.exit(1);
}, 60000);
