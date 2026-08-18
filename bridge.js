const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const QRCode = require('qrcode');
const axios = require('axios');
const http = require('http');
const fs = require('fs');
const path = require('path');

const FLASK_URL = 'http://127.0.0.1:5000/greenapi';
const BRIDGE_PORT = 5001;

console.log('🚀 Initializing Native WhatsApp Web Bridge...');

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './.wwebjs_auth' }),
    puppeteer: {
        headless: process.env.PUPPETEER_HEADLESS === 'false' ? false : true,
        executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu'
        ]
    }
});

client.on('qr', async (qr) => {
    console.log('\n==================================================');
    console.log('📱 QR CODE GENERATED & SAVED AS IMAGE:');
    console.log('==================================================\n');
    qrcode.generate(qr, { small: true });

    try {
        const qrPath = path.join(__dirname, 'static', 'qr.png');
        if (!fs.existsSync(path.dirname(qrPath))) {
            fs.mkdirSync(path.dirname(qrPath), { recursive: true });
        }
        await QRCode.toFile(qrPath, qr, { width: 500, margin: 2 });
        console.log(`[QR Image Saved] -> ${qrPath}`);

        const artifactDir = 'C:\\Users\\saake\\.gemini\\antigravity-ide\\brain\\233f4818-fc1d-4b24-8d12-fc4b81327d4d';
        if (fs.existsSync(artifactDir)) {
            const artifactQrPath = path.join(artifactDir, 'qr.png');
            fs.copyFileSync(qrPath, artifactQrPath);
            console.log(`[QR Image Copied to Artifacts] -> ${artifactQrPath}`);
        }
    } catch (err) {
        console.error('[QR Image Export Error]:', err.message);
    }
});

client.on('ready', () => {
    console.log('\n✅ Native WhatsApp Web Bridge Connected & Ready!');
    console.log(`👤 Logged in user ID: ${client.info.wid._serialized}`);
});

client.on('authenticated', () => {
    console.log('🔑 WhatsApp Web session authenticated successfully!');
});

client.on('auth_failure', (msg) => {
    console.error('❌ WhatsApp Web auth failure:', msg);
});

const processedMsgIds = new Set();

client.on('message', async (msg) => {
    try {
        if (msg.fromMe) return;

        const msgId = msg.id ? msg.id.id : null;
        if (msgId) {
            if (processedMsgIds.has(msgId)) {
                console.log(`[Native WA Skip Duplicate] Message ID ${msgId} already processed.`);
                return;
            }
            processedMsgIds.add(msgId);
            if (processedMsgIds.size > 1000) {
                const firstItem = processedMsgIds.values().next().value;
                processedMsgIds.delete(firstItem);
            }
        }

        const from = msg.from;
        const body = msg.body || '';
        let mediaUrl = null;
        let fileName = null;

        console.log(`[Native WA Incoming] From: ${from} | Body: '${body.substring(0, 40)}...' | HasMedia: ${msg.hasMedia}`);

        if (msg.hasMedia) {
            try {
                const media = await msg.downloadMedia();
                if (media && media.data) {
                    const ext = media.mimetype.split('/')[1]?.split(';')[0] || 'bin';
                    fileName = media.filename || `doc_${Date.now()}.${ext}`;
                    const savePath = path.join(__dirname, 'static', 'uploads', fileName);
                    
                    if (!fs.existsSync(path.dirname(savePath))) {
                        fs.mkdirSync(path.dirname(savePath), { recursive: true });
                    }
                    
                    fs.writeFileSync(savePath, Buffer.from(media.data, 'base64'));
                    mediaUrl = `http://127.0.0.1:5000/static/uploads/${fileName}`;
                    console.log(`[Native WA Media Saved] -> ${savePath}`);
                }
            } catch (mediaErr) {
                console.error('[Native WA Media Error]:', mediaErr.message);
            }
        }

        const payload = {
            typeWebhook: 'incomingMessageReceived',
            senderData: {
                sender: from,
                chatId: from
            },
            messageData: {
                typeMessage: msg.hasMedia ? 'documentMessage' : 'textMessage',
                textMessageData: {
                    textMessage: body
                },
                documentMessageData: mediaUrl ? {
                    downloadUrl: mediaUrl,
                    fileName: fileName,
                    caption: body
                } : null
            }
        };

        await axios.post(FLASK_URL, payload, { timeout: 10000 });
        console.log(`[Native WA Webhook Forwarded] -> Flask 200 OK`);
    } catch (err) {
        console.error('[Native WA Processing Error]:', err.message);
    }
});

// Outbound Message HTTP Server on Port 5001
const server = http.createServer(async (req, res) => {
    if (req.method === 'POST' && req.url === '/send') {
        let bodyStr = '';
        req.on('data', chunk => { bodyStr += chunk; });
        req.on('end', async () => {
            try {
                const data = JSON.parse(bodyStr);
                const toPhone = (data.to || '').replace('+', '').replace('whatsapp:', '').replace(/\s+/g, '');
                const text = data.message || '';

                if (!toPhone || !text) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Missing to or message' }));
                    return;
                }

                const chatId = (toPhone.includes('@c.us') || toPhone.includes('@lid') || toPhone.includes('@g.us')) ? toPhone : `${toPhone}@c.us`;
                console.log(`[Native WA Outbound] Sending to ${chatId}...`);
                
                await client.sendMessage(chatId, text);
                console.log(`[Native WA Outbound Success] Delivered to ${chatId}`);

                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ status: 'sent', chatId: chatId }));
            } catch (err) {
                console.error('[Native WA Outbound Error]:', err.message);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: err.message }));
            }
        });
    } else {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('Not Found');
    }
});

server.listen(BRIDGE_PORT, () => {
    console.log(`📡 Native WhatsApp Outbound Bridge listening on http://127.0.0.1:${BRIDGE_PORT}`);
});

client.initialize();
