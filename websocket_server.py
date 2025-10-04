import asyncio
import websockets

async def handle_websocket(websocket, path):
    print("CALLED!", websocket, path)
    print(f"New client connected: {websocket.remote_address}, path: {path}")
    try:
        async for message in websocket:
            print(f"Received: {message}")
            await websocket.send(f"Echo: {message}")
    except websockets.exceptions.ConnectionClosed:
        print(f"Client {websocket.remote_address} disconnected.")

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 12345
    start_server = websockets.serve(handle_websocket, host, port)
    print(f"WebSocket server running at ws://{host}:{port}")
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
