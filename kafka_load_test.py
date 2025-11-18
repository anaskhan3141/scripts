from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import time
import logging
import random
import string
import threading

# ===== CONFIG =====
BROKER = "10.10.32.16:9092,10.10.32.15:9092,10.10.32.17:9092,"
TOPIC = "test-topic"
USERNAME = "admin"
PASSWORD = "admin-secret"
LOG_INTERVAL = 3     # seconds between summaries
MESSAGE_SIZE = 200   # characters per message
GROUP_ID = "load-tester"

# ===== LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)

# ===== PRODUCER =====
def create_producer():
    return KafkaProducer(
        bootstrap_servers=BROKER,
        security_protocol="SASL_PLAINTEXT",
        sasl_mechanism="PLAIN",
        sasl_plain_username=USERNAME,
        sasl_plain_password=PASSWORD,
        value_serializer=lambda v: v.encode("utf-8"),
        linger_ms=20,            # batch messages for up to 20 ms
        batch_size=32768,        # 32 KB per batch
        retries=3
    )

# ===== CONSUMER =====
def create_consumer():
    return KafkaConsumer(
        TOPIC,
        bootstrap_servers=BROKER,
        security_protocol="SASL_PLAINTEXT",
        sasl_mechanism="PLAIN",
        sasl_plain_username=USERNAME,
        sasl_plain_password=PASSWORD,
        auto_offset_reset="earliest",
        group_id=GROUP_ID,
        enable_auto_commit=True,
        fetch_max_bytes=10 * 1024 * 1024,  # up to 10 MB fetch
        max_poll_records=500,              # more records per poll
        consumer_timeout_ms=1000,
        value_deserializer=lambda v: v.decode("utf-8")
    )

# ===== MESSAGE GENERATOR =====
def random_message():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=MESSAGE_SIZE))

# ===== GLOBAL COUNTERS =====
sent = 0
received = 0
lock = threading.Lock()

# ===== PRODUCER THREAD =====
def produce_loop(producer):
    global sent
    while True:
        try:
            for _ in range(1000):  # burst send 1000 at once
                msg = random_message()
                producer.send(TOPIC, msg)
                with lock:
                    sent += 1
        except KafkaError as e:
            logging.error(f"Producer error: {e}")
            time.sleep(2)
            producer = create_producer()

# ===== CONSUMER THREAD =====
def consume_loop(consumer):
    global received
    while True:
        try:
            for message in consumer:
                with lock:
                    received += 1
        except KafkaError as e:
            logging.error(f"Consumer error: {e}")
            time.sleep(2)
            consumer = create_consumer()

# ===== MAIN =====
producer = create_producer()
consumer = create_consumer()
logging.info("Kafka producer and consumer connected")

threading.Thread(target=produce_loop, args=(producer,), daemon=True).start()
threading.Thread(target=consume_loop, args=(consumer,), daemon=True).start()

last = time.time()
while True:
    time.sleep(LOG_INTERVAL)
    with lock:
        total = sent + received
        rate = total / LOG_INTERVAL
        logging.info(f"Msgs/sec={rate:.1f}, Produced={sent}, Consumed={received}")
        sent = received = 0

