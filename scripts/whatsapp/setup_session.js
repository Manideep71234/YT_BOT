/**
 * setup_session.js  –  Run this ONCE locally to generate your session.
 * 
 * Steps:
 *   cd scripts/whatsapp
 *   npm install
 *   node setup_session.js
 * 
 * Scan the QR with your WhatsApp (the number you want to SEND from).
 * Session saved to ./wwebjs_auth/ — you'll zip + upload to GitHub next.
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './wwebjs_auth' }),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage']
    }
});

client.on('qr', qr => {
    console.log('\n📱 Scan this QR code with WhatsApp (the sender number):\n');
    qrcode.generate(qr, { small: true });
});

client.on('ready', async () => {
    console.log('\n✅ Session saved to ./wwebjs_auth/');
    console.log('\nNext steps:');
    console.log('  1. Run: zip -r wwebjs_auth.zip wwebjs_auth/');
    console.log('  2. Run: base64 wwebjs_auth.zip > session_b64.txt');
    console.log('  3. Copy contents of session_b64.txt');
    console.log('  4. Add as GitHub Secret: WA_SESSION_B64');
    console.log('\nSession is ready. Exiting.');
    await client.destroy();
    process.exit(0);
});

client.on('auth_failure', msg => {
    console.error('❌ Auth failed:', msg);
    process.exit(1);
});

client.initialize();
