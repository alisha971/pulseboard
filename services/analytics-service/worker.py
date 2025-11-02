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

pg_conn = None

def connect_postgres():
    """Connects to PostgreSQL database with retry logic."""
    global pg_conn
    while True:
        try:
            pg_conn = psycopg2.connect(POSTGRES_URL)
            pg_conn.autocommit = True  # Auto-commit after each query
            print("[PG] Connected to PostgreSQL successfully.")
            return
        except psycopg2.OperationalError as e:
            print(f" [!] PostgreSQL connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def on_message_callback(ch, method, properties, body):
    """
    Callback function to process a message from the queue.
    """
    global pg_conn
    print(f"\n[analytics-service] Received message:")
    cursor = None
    
    try:
        message = json.loads(body.decode('utf-8'))
        print(json.dumps(message, indent=2))
        
        # Extract data from message
        user_id = message.get('user_id')
        event_type = message.get('event_type')
        # Parse timestamp and get the date
        event_date = datetime.fromisoformat(message.get('timestamp').replace('Z', '+00:00')).date()

        if not user_id or not event_type:
            print(" [!] Skipping message: missing user_id or event_type")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Check connection and reconnect if needed
        if not pg_conn or pg_conn.closed:
            print("[PG] Reconnecting to PostgreSQL...")
            connect_postgres()
        
        # --- MODIFIED SQL QUERY ---
        # This is the "UPSERT" logic
        # It attempts to INSERT a new row.
        # If a row for that (user_id, metric_date) already exists (violating UNIQUE constraint),
        # it will UPDATE the existing row instead.
        sql = """
            INSERT INTO daily_user_metrics (user_id, metric_date, event_count, tasks_created, tasks_completed)
            VALUES (%(user_id)s, %(metric_date)s, 1, 
                    CASE WHEN %(event_type)s = 'task_created' THEN 1 ELSE 0 END,
                    CASE WHEN %(event_type)s = 'task_completed' THEN 1 ELSE 0 END
                   )
            ON CONFLICT (user_id, metric_date) 
            DO UPDATE SET
                event_count = daily_user_metrics.event_count + 1,
                tasks_created = daily_user_metrics.tasks_created + CASE WHEN %(event_type)s = 'task_created' THEN 1 ELSE 0 END,
                tasks_completed = daily_user_metrics.tasks_completed + CASE WHEN %(event_type)s = 'task_completed' THEN 1 ELSE 0 END;
        """
        
        params = {
            "user_id": user_id,
            "metric_date": event_date,
            "event_type": event_type
        }
        
        cursor = pg_conn.cursor()
        cursor.execute(sql, params)
        # No cursor.commit() needed because pg_conn.autocommit = True
        
        print(f"[PG] Metric updated for user {user_id} on {event_date}.")
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except psycopg2.Error as e:
        print(f" [!] Database error: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    except json.JSONDecodeError:
        print(" [!] Failed to decode JSON")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        print(f" [!] Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    finally:
        if cursor:
            cursor.close()

def main():
    """
    Main function to connect and start consuming messages.
    """
    print('Analytics-Worker starting...')
    connect_postgres() # Connect to PG on startup
    
    connection = None
    while True:
        try:
            print('Attempting to connect to RabbitMQ...')
            connection_params = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(connection_params)
            channel = connection.channel()

            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_message_callback)

            print(f'[*] Waiting for messages on queue "{QUEUE_NAME}".')
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            print(f"Connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("Consumer stopped.")
            if connection:
                connection.close()
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}. Retrying in 5 seconds...")
            if connection and not connection.is_closed:
                connection.close()
            time.sleep(5)

if __name__ == '__main__':
    main()
