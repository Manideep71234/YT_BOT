/**
 * send.js  –  Send a WhatsApp message using the saved session.
 * Called by notifier.py:  node send.js "Your message" "91XXXXXXXXXX"
 */

const { Client, LocalAuth } = require('whatsapp-web.js');

const message = process.argv[2];
const toNumber = process.argv[3];   // format: 91XXXXXXXXXX  (no + no spaces)

if (!message || !toNumber) {
    console.error('Usage: node send.js "<message>" "<number1,number2>"');
    process.exit(1);
}

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './wwebjs_auth' }),
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ]
    },
    webVersionCache: {
        type: 'remote',
        remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html',
    }
});

let sent = false;

client.on('ready', async () => {
    try {
        const numbers = toNumber.split(',');
        for (const num of numbers) {
            const cleanNum = num.trim();
            if (!cleanNum) continue;
            const chatId = `${cleanNum}@c.us`;
            await client.sendMessage(chatId, message);
            console.log(`[whatsapp] ✅ Sent to ${cleanNum}`);
        }
        
        // Wait a few seconds for the message to actually sync to WhatsApp servers
        // before destroying the client, otherwise it gets stuck in the outbox!
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        sent = true;
    } catch (e) {
        console.error(`[whatsapp] ❌ Send failed: ${e.message}`);
    } finally {
        await client.destroy();
        process.exit(sent ? 0 : 1);
    }
});

client.on('auth_failure', () => {
    console.error('[whatsapp] ❌ Session expired — re-run setup_session.js locally.');
    process.exit(1);
});

// Timeout safety — exit after 60s regardless
setTimeout(() => {
    console.error('[whatsapp] ❌ Timeout after 60s');
    process.exit(1);
}, 60000);

client.initialize();
