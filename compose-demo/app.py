import redis
import time

# Connect to Redis using the service name as hostname
client = redis.Redis(host="redis", port=6379, decode_responses=True)

print("Connected to Redis!")

# Write data
client.set("name", "Docker Compose")
client.set("lesson", "8")
client.incr("run_count")

# Read data
print(f"name     = {client.get('name')}")
print(f"lesson   = {client.get('lesson')}")
print(f"run_count = {client.get('run_count')}")
