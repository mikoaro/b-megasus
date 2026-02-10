import os
import json
import random
from datetime import datetime
from app.database import get_db_pool

# Placeholder Base64 strings (Keep your existing ones)
CLEAN_IMAGE_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=" 
FIRE_IMAGE_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==" 

class ServiceLayer:
    def __init__(self, simulator_instance=None):
        self.simulator = simulator_instance

    # --- 1. VISION TOOL ---
    async def get_virtual_camera_frame(self):
        print(f"👁️ [VISION] Capturing Virtual Frame...")
        if self.simulator:
            if self.simulator.state.value == "CRITICAL" and not self.simulator.active_derate:
                return {"image_data": FIRE_IMAGE_B64, "status": "HAZARD_DETECTED"}
            return {"image_data": CLEAN_IMAGE_B64, "status": "CLEAN"}
        return {"error": "Camera Offline"}

    # --- 2. IOT CONTROL TOOL ---
    async def send_iot_command(self, command: str, target_id: str):
        print(f"📡 [IOT GATEWAY] Transmitting: {command} -> {target_id}")
        if self.simulator:
            self.simulator.apply_iot_command(command)
            return {"status": "SUCCESS", "timestamp": "T+0.05s", "state": "DERATED"}
        return {"status": "FAILED", "reason": "Simulator Disconnected"}

    # --- 3. ERP INVENTORY ---
    async def check_inventory(self, part_number: str):
        print(f"🔧 [ERP SYSTEM] Querying SKU: {part_number}")
        pool = await get_db_pool()
        if not pool: return {"stock": 0, "available": False}
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM inventory WHERE part_number = $1", part_number)
            if row:
                return {
                    "available": True, 
                    "part_number": row['part_number'],
                    "name": row['name'],
                    "stock": row['stock_level'], 
                    "location": row['location']
                }
            return {"available": False, "stock": 0}

    # --- 4. CRM TICKETING (Extended) ---
    async def create_ticket(self, asset_id: str, priority: str, issue_type: str):
        new_id = f"CASE-{random.randint(100000, 999999)}"
        print(f"🎫 [SALESFORCE] Creating Case: {new_id}")
        
        pool = await get_db_pool()
        if pool:
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO tickets (ticket_ref, asset_id, issue_type, status, priority)
                    VALUES ($1, $2, $3, 'OPEN', $4)
                """, new_id, asset_id, issue_type, priority)
        
        return {
            "ticket_id": new_id, 
            "status": "OPEN", 
            "priority": priority,
            "sla_countdown": "4h 00m"
        }

    # --- 5. FSM DISPATCH (Extended) ---
    async def dispatch_technician(self, ticket_id: str, sector: str):
        wo_id = f"WO-{hex(random.randint(0, 16777215))[2:].upper()}"
        tech_name = random.choice(["Sarah Jenkins", "Mike Ross", "David Kim"])
        eta = f"{random.randint(10, 45)} mins"
        print(f"🚚 [SERVICEMAX] Dispatching {tech_name} ({wo_id})")

        pool = await get_db_pool()
        if pool:
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO dispatches (work_order_ref, ticket_ref, technician_name, destination, status, eta)
                    VALUES ($1, $2, $3, $4, 'EN_ROUTE', $5)
                """, wo_id, ticket_id, tech_name, sector, eta)

        return {
            "work_order": wo_id,
            "technician_id": tech_name,
            "eta": eta
        }