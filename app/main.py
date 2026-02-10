import asyncio
import json
from fastapi import FastAPI, WebSocket, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from app.simulation import ExcavatorSimulator, MachineState
from app.agent_core import MarathonAgent
from app.database import init_db, get_db_pool, connect_to_db, close_db_connection
from app.services import ServiceLayer 

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

simulator = ExcavatorSimulator()
agent = MarathonAgent(simulator)
services = ServiceLayer(simulator_instance=simulator) 

latest_agent_decision = None
templates = Jinja2Templates(directory="app/templates")

@app.on_event("startup")
async def startup_event():
    print("🚀 BACKEND STARTING...")
    await connect_to_db()
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 BACKEND SHUTTING DOWN...")
    await close_db_connection()

# --- SYSTEM OF RECORD ENDPOINTS ---
@app.get("/api/crm/tickets")
async def get_tickets():
    pool = await get_db_pool()
    if not pool: return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM tickets ORDER BY created_at DESC LIMIT 10")
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"DB Error: {e}")
        return []

@app.get("/api/erp/inventory")
async def get_inventory():
    pool = await get_db_pool()
    if not pool: return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM inventory ORDER BY part_number ASC")
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"DB Error: {e}")
        return []

@app.get("/api/fsm/dispatches")
async def get_dispatches():
    pool = await get_db_pool()
    if not pool: return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM dispatches ORDER BY created_at DESC LIMIT 10")
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"DB Error: {e}")
        return []

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

class TranscriptPayload(BaseModel):
    session_id: str
    user_id: str
    asset_id: str
    transcript: List[Dict[str, Any]]

@app.get("/api/vision/feed")
async def get_vision_feed():
    return await services.get_virtual_camera_frame()

@app.post("/api/save-transcript")
async def save_transcript_endpoint(payload: TranscriptPayload):
    try:
        pool = await get_db_pool()
        if pool:
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO incident_transcripts (session_id, user_id, asset_id, transcript_json)
                    VALUES ($1, $2, $3, $4)
                """, payload.session_id, payload.user_id, payload.asset_id, json.dumps(payload.transcript))
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.post("/simulate/fault")
async def trigger_fault_manual(request: Request):
    global latest_agent_decision
    try:
        body = await request.json()
        mode = body.get("mode", "HUMAN")
        print(f"🔥 FAULT TRIGGER RECEIVED. MODE: {mode}")
        simulator.state = MachineState.NORMAL 
        simulator.temp = 85.0
        simulator.active_derate = False 
        simulator.force_fault()
        simulator.current_mode = mode 
        latest_agent_decision = None
        return {"status": "Fault Initiated", "mode": mode}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/simulate/reset")
async def reset_simulation(request: Request):
    global latest_agent_decision
    try:
        print("🔄 SYSTEM RESET COMMAND RECEIVED")
        simulator.apply_iot_command("RESET")
        latest_agent_decision = None
        return {"status": "System Reset to Normal"}
    except Exception as e:
        print(f"Reset Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Global WS Manager (Simple version for demo)
active_connections: List[WebSocket] = []

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    global latest_agent_decision
    await websocket.accept()
    active_connections.append(websocket)
    
    if simulator.state == MachineState.CRITICAL:
        await websocket.send_json({"type": "EVENT", "payload": "CRITICAL_FAULT"})
        if latest_agent_decision:
             await websocket.send_json({"type": "AGENT_DECISION", "payload": latest_agent_decision})
    try:
        while True:
            data, is_new_fault = simulator.generate_next_frame()
            if is_new_fault:
                print("🚨 CRITICAL FAULT -> AGENT ACTIVATED")
                await websocket.send_json({"type": "EVENT", "payload": "CRITICAL_FAULT"})
                
                # --- DEFINE CALLBACK FOR LIVE CHAT ---
                async def broadcast_status(status_type, message):
                    payload = {"status": status_type, "context": message}
                    # Send to ALL connected clients
                    for conn in active_connections:
                        try:
                            await conn.send_json({"type": "AGENT_STATUS", "payload": payload})
                        except: pass

                # Pass callback to agent
                mode = getattr(simulator, 'current_mode', 'HUMAN')
                asyncio.create_task(agent.process_incident(int(data['timestamp']), data['asset_id'], data, mode, broadcast_status))

            if latest_agent_decision:
                 await websocket.send_json({"type": "AGENT_DECISION", "payload": latest_agent_decision})
            
            await websocket.send_json({"type": "DATA", "payload": data})
            await asyncio.sleep(0.1) 
    except Exception as e:
        print(f"WS Disconnected: {e}")
    finally:
        active_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)