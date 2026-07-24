import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/camera/ws"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            
            # Wait for init message
            init_msg = await websocket.recv()
            print(f"Received INIT: {init_msg}")
            
            # Subscribe to video and telemetry
            subscribe_msg = {
                "action": "subscribe",
                "types": ["video", "telemetry"]
            }
            await websocket.send(json.dumps(subscribe_msg))
            print("Sent subscribe request")
            
            # Receive frames
            for _ in range(5):
                response = await websocket.recv()
                data = json.loads(response)
                
                if data.get("action") == "video":
                    print(f"Received video frame! Timestamp: {data.get('timestamp')}, Size: {len(data.get('frame', ''))} bytes")
                elif data.get("action") == "telemetry":
                    print(f"Received telemetry: {data.get('status')}")
                else:
                    print(f"Received other: {data}")
                    
    except ConnectionRefusedError:
        print("Connection refused. Make sure the server is running!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
