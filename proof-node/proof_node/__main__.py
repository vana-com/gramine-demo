import random
import time
import logging

from .client import process_task

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    logging.info("Starting client")

    while True:
        task = random.choice([
            {
                "validator_type": "doordash",
                "data": {
                    "id": str(random.randint(1, 1000)),
                    "name": f"User {random.randint(1, 100)}",
                    "email": f"user{random.randint(1, 100)}@example.com",
                    "phone": f"{random.randint(1000000000, 9999999999)}"
                }
            },
            {
                "validator_type": "analytics",
                "data": {
                    "duration": random.randint(30, 300),
                    "pages": [f"page_{random.randint(1, 10)}" for _ in range(random.randint(1, 10))] + 
                             random.choice([["cart"], ["checkout"], ["buy"], []])
                }
            }
        ])
        
        if task["validator_type"] == "doordash" and random.random() < 0.2:
            task["data"].pop("phone", None)
        
        logging.info(f"Generated task: {task}")
        process_task(task)
        
        time.sleep(random.uniform(1, 5))

if __name__ == "__main__":
    logging.info("Starting main")
    main()