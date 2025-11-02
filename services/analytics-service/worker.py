import pika
import time
import os
import json

# --- Config ---
RABBITMQ_URL = os.environ.get('RABBITMQ_URL', 'amqp://pulseuser:pulsepassword@rabbitmq:5672')
QUEUE_NAME = 'activity_events'

def on_message_callback(ch, method, properties, body):
    """
    Callback function to process a message from the queue.
    """
    print(f"\n[analytics-service] Received message:")
    try:
        # Decode the message body from bytes to string, then parse JSON
        message = json.loads(body.decode('utf-8'))
        print(json.dumps(message, indent=2))
        
        # Acknowledge the message was processed successfully
        # This tells RabbitMQ to remove it from the queue
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except json.JSONDecodeError:
        print(" [!] Failed to decode JSON")
        # Reject the message, but don't requeue (or it will fail forever)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        print(f" [!] Error processing message: {e}")
        # Reject and requeue, maybe it's a temporary issue
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    """
    Main function to connect and start consuming messages.
    Includes retry logic for startup.
    """
    print('Analytics-Worker starting...')
    connection = None
    
    while True:
        try:
            print('Attempting to connect to RabbitMQ...')
            connection_params = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(connection_params)
            channel = connection.channel()

            # Declare the queue (idempotent - ensures it exists)
            channel.queue_declare(queue=QUEUE_NAME, durable=True)

            # Set up the consumer
            channel.basic_consume(
                queue=QUEUE_NAME,
                on_message_callback=on_message_callback
                # auto_ack=False (We do manual acknowledgement)
            )

            print(f'[*] Waiting for messages on queue "{QUEUE_NAME}". To exit press CTRL+C')
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
            time.sleep(5)

if __name__ == '__main__':
    main()