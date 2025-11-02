const express = require('express');
const amqp = require('amqplib');

// --- Config ---
const PORT = process.env.PORT || 3001;
const RABBITMQ_URL = process.env.RABBITMQ_URL || 'amqp://pulseuser:pulsepassword@rabbitmq:5672';
const QUEUE_NAME = 'activity_events';

// --- App Setup ---
const app = express();
app.use(express.json());

let amqpConnection = null;
let amqpChannel = null;

// --- RabbitMQ Connection ---
async function connectRabbitMQ() {
  try {
    console.log('Connecting to RabbitMQ...');
    amqpConnection = await amqp.connect(RABBITMQ_URL);
    amqpChannel = await amqpConnection.createChannel();
    
    // Assert the queue exists, or create it if it doesn't
    await amqpChannel.assertQueue(QUEUE_NAME, { durable: true });
    
    console.log('RabbitMQ connected and channel created.');
  } catch (error) {
    console.error('Failed to connect to RabbitMQ:', error.message);
    // Retry connection after 5 seconds
    setTimeout(connectRabbitMQ, 5000);
  }
}

// --- API Endpoints ---

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok' });
});

// Test endpoint to publish a message
app.get('/test-publish', async (req, res) => {
  if (!amqpChannel) {
    return res.status(500).json({ error: 'RabbitMQ channel not available.' });
  }

  const message = {
    type: 'test_event',
    user_id: 123,
    timestamp: new Date().toISOString(),
    data: 'Hello, World!'
  };

  try {
    // Send the message to the queue as a buffer
    amqpChannel.sendToQueue(QUEUE_NAME, Buffer.from(JSON.stringify(message)), {
      persistent: true // Make message persistent
    });
    
    console.log('Message published:', message);
    res.status(200).json({ status: 'Message published!', message });
  } catch (error) {
    console.error('Failed to publish message:', error);
    res.status(500).json({ error: 'Failed to publish message.' });
  }
});

// --- Start Server ---
app.listen(PORT, () => {
  console.log(`Activity-Service listening on port ${PORT}`);
  connectRabbitMQ(); // Connect to RabbitMQ on start
});