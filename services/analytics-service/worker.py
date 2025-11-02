import pika
import time
import os
import json
import psycopg2
from psycopg2.extras import Json
from datetime import datetime

# --- Config ---
RABBITMQ_URL = os.environ.get('RABBITMQ_URL', 'amqp://pulseuser:pulsepassword@rabbitmq:5672')
POSTGRES_URL = os.environ.get('POSTGRES_URL', 'postgresql://pulseuser:pulsepassword@postgres:5432/pulsedb')
QUEUE_NAME = 'activity_events'

def connect_postgres():
    """Connect to PostgreSQL with retry logic."""
    while True:
        try:
            conn = psycopg2.connect(POSTGRES_URL)
            conn.autocommit = True  # Auto-commit after each operation
            print("[PG] Connected to PostgreSQL successfully.")
            return conn
        except psycopg2.OperationalError as e:
            print(f"[PG] Connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def process_message(db_conn, body):
    """
    Process the received message and update the analytics database.
    """
    try:
        message = json.loads(body.decode('utf-8'))
        print(f"\n[analytics-service] Received message:")
        print(json.dumps(message, indent=2))

        user_id = message.get('user_id')
        timestamp_str = message.get('timestamp')

        if not user_id or not timestamp_str:
            print(" [!] Skipping message: missing user_id or timestamp.")
            return True # Acknowledge (ack) as it's a bad message

        # Get the date (YYYY-MM-DD) from the timestamp
        metric_date = datetime.fromisoformat(timestamp_str.rstrip('Z')).date()

        # --- The core "UPSERT" logic ---
        # Try to INSERT a new row.
        # If a row for that user_id and metric_date already exists (violating unique constraint),
        # then UPDATE its event_count instead.
        
        upsert_query = """
        INSERT INTO daily_user_metrics (user_id, metric_date, event_count)
        VALUES (%s, %s, 1)
        ON CONFLICT (user_id, metric_date)
        DO UPDATE SET event_count = daily_user_metrics.event_count + 1;
        """
        
        with db_conn.cursor() as cursor:
            cursor.execute(upsert_query, (user_id, metric_date))
        
        print(f"[PG] Metric updated for user {user_id} on {metric_date}.")
        return True # Signal successful processing

    except json.JSONDecodeError:
        print(" [!] Failed to decode JSON")
        return False # Do not acknowledge, message is malformed
    except Exception as e:
        print(f" [!] Error processing message: {e}")
        return False # Do not acknowledge, temporary failure

def main():
    """
    Main function to connect and start consuming messages.
    """
    print('Analytics-Worker starting...')
    
    # Connect to databases
    db_conn = connect_postgres()
    
    while True:
        try:
            print('Attempting to connect to RabbitMQ...')
            connection_params = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(connection_params)
            channel = connection.channel()

            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            print(f'[*] Waiting for messages on queue "{QUEUE_NAME}".')

            def on_message_callback(ch, method, properties, body):
                """Wrapper callback to handle message processing and ack/nack."""
                if process_message(db_conn, body):
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                else:
                    # Requeue=False to avoid infinite loops on bad messages
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            channel.basic_consume(
                queue=QUEUE_NAME,
                on_message_callback=on_message_callback
            )
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            print(f"RabbitMQ connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"An unexpected error occurred: {e}. Retrying in 5 seconds...")
            if 'db_conn' in locals() and db_conn.closed:
                 print("[PG] Reconnecting to PostgreSQL...")
                 db_conn = connect_postgres() # Reconnect if PG connection was lost
            time.sleep(5)

if __name__ == '__main__':
    main()