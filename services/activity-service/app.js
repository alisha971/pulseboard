const express = require('express');
const amqp = require('amqplib');
const { Pool } = require('pg');

// --- Config ---
const PORT = process.env.PORT || 3001;
const RABBITMQ_URL = process.env.RABBITMQ_URL || 'amqp://pulseuser:pulsepassword@rabbitmq:5672';
const POSTGRES_URL = process.env.POSTGRES_URL || 'postgresql://pulseuser:pulsepassword@postgres:5432/pulsedb';
const QUEUE_NAME = 'activity_events';

// --- App Setup ---
const app = express();
app.use(express.json());

let amqpChannel = null;

// --- Postgres Connection Pool ---
const pgPool = new Pool({
  connectionString: POSTGRES_URL,
});

// Test PG connection
pgPool.query('SELECT NOW()', (err, res) => {
  if (err) {
    console.error('Failed to connect to PostgreSQL', err.stack);
  } else {
    console.log('PostgreSQL connected successfully:', res.rows[0].now);
  }
});


// --- RabbitMQ Connection ---
async function connectRabbitMQ() {
  try {
    console.log('Connecting to RabbitMQ...');
    const amqpConnection = await amqp.connect(RABBITMQ_URL);
    amqpChannel = await amqpConnection.createChannel();
    await amqpChannel.assertQueue(QUEUE_NAME, { durable: true });
    console.log('RabbitMQ connected and channel created.');
  } catch (error) {
    console.error('Failed to connect to RabbitMQ:', error.message);
    setTimeout(connectRabbitMQ, 5000); // Retry
  }
}

// --- API Endpoints ---
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok', rabbit: amqpChannel ? 'connected' : 'disconnected' });
});

/**
 * The new "real" endpoint.
 * Expects a POST body like:
 * { "type": "task_completed", "user": "user@example.com", "data": { "task_id": 42 } }
 */
app.post('/api/activity', async (req, res) => {
  const { type, user, data } = req.body;

  if (!type || !user) {
    return res.status(400).json({ error: 'Missing required fields: type, user' });
  }

  if (!amqpChannel) {
    return res.status(503).json({ error: 'Service not ready. RabbitMQ not connected.' });
  }

  const eventMessage = {
    event_type: type,
    user_id: user,
    timestamp: new Date().toISOString(),
    data_payload: data || {}
  };

  try {
    // --- 1. Write to PostgreSQL ---
    const queryText = 'INSERT INTO events(event_type, user_id, timestamp, data_payload) VALUES($1, $2, $3, $4) RETURNING event_id';
    const queryValues = [eventMessage.event_type, eventMessage.user_id, eventMessage.timestamp, eventMessage.data_payload];
    
    const pgRes = await pgPool.query(queryText, queryValues);
    const newEventId = pgRes.rows[0].event_id;
    console.log(`[PG] Event stored with ID: ${newEventId}`);

    // --- 2. Publish to RabbitMQ ---
    // We add the new event_id to the message for the consumer
    const messageToSend = { ...eventMessage, event_id: newEventId };
    
    amqpChannel.sendToQueue(QUEUE_NAME, Buffer.from(JSON.stringify(messageToSend)), {
      persistent: true
    });
    console.log('[RabbitMQ] Event published to queue.');

    res.status(202).json({ status: 'Event received', event_id: newEventId });

  } catch (error) {
    console.error('Failed to process event:', error);
    res.status(500).json({ error: 'Internal server error.' });
  }
});

// --- Start Server ---
app.listen(PORT, () => {
  console.log(`Activity-Service listening on port ${PORT}`);
  connectRabbitMQ();
});