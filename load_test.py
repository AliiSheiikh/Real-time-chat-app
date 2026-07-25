import asyncio
import statistics
import sys
import time

import websockets

HOST = "ws://127.0.0.1:8000/ws"


async def run_client(client_id: int) -> float:
    username = f"loadtest_{client_id}"

    async with websockets.connect(f"{HOST}?username={username}") as ws:
        while True:
            message = await ws.recv()
            if message == f"{username} joined the chat":
                break

        send_time = time.monotonic()
        await ws.send("ping")

        while True:
            message = await ws.recv()
            if message == f"{username}: ping":
                break

        return time.monotonic() - send_time


async def main(num_clients: int):
    start = time.monotonic()
    latencies = await asyncio.gather(*(run_client(i) for i in range(num_clients)))
    total_time = time.monotonic() - start

    latencies_ms = sorted(latency * 1000 for latency in latencies)
    p95_index = int(len(latencies_ms) * 0.95)

    print(f"Concurrent clients: {num_clients}")
    print(f"Total wall time: {total_time:.2f}s")
    print(f"Connection throughput: {num_clients / total_time:.1f} clients/sec")
    print(
        "Message round-trip latency (ms) — "
        f"min: {latencies_ms[0]:.1f}, "
        f"median: {statistics.median(latencies_ms):.1f}, "
        f"p95: {latencies_ms[p95_index]:.1f}, "
        f"max: {latencies_ms[-1]:.1f}"
    )


if __name__ == "__main__":
    num_clients = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    asyncio.run(main(num_clients))
