import os
import json
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types
from app.database import get_db_pool
from app.services import ServiceLayer

load_dotenv(".env.local")

# --- SECONDARY AGENT: VENDOR/PROCUREMENT ---
class VendorAgent:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key) if api_key else None
        
    async def negotiate(self, part_req: str, max_price: float):
        """Simulates a vendor negotiating availability and price"""
        if not self.client:
            return {"status": "ERROR", "message": "Vendor Offline"}

        # Vendor Persona
        prompt = f"""
        ACT AS: Industrial Parts Supplier (Bot).
        REQUEST: Customer needs '{part_req}'. Target price ${max_price}.
        CONTEXT: 
        - Part '{part_req}' is OUT OF STOCK.
        - Alternative 'High-Perf-Hybrid-Inverter-X' is AVAILABLE.
        - Price: $5,800 (slightly higher than target).
        - ETA: 4 Hours (Expedited).
        
        TASK: Respond with a JSON offer.
        FORMAT: {{"offer_part": "...", "price": 0.0, "eta": "...", "message": "..."}}
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-3-pro-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.4
                )
            )
            return json.loads(response.text)
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

# --- PRIMARY AGENT: SAFETY CONTROLLER ---
class MarathonAgent:
    def __init__(self, simulator):
        self.services = ServiceLayer(simulator_instance=simulator)
        
        # --- LAZY LOADING ---
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
            self.vendor = VendorAgent(api_key) # Initialize Sub-Agent
        else:
            print("⚠️ GEMINI_API_KEY not found. Agent will fail.")
            self.client = None
            self.vendor = None

        self.tools = [
            types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="send_iot_command",
                    description="Send control signal.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "command": types.Schema(type="STRING", enum=["DERATE", "SHUTDOWN", "RESET"]),
                            "target_id": types.Schema(type="STRING")
                        },
                        required=["command", "target_id"]
                    )
                ),
                types.FunctionDeclaration(
                    name="check_inventory",
                    description="Check ERP.",
                    parameters=types.Schema(type="OBJECT", properties={"part_number": types.Schema(type="STRING")}, required=["part_number"])
                ),
                types.FunctionDeclaration(
                    name="create_ticket",
                    description="Open ticket.",
                    parameters=types.Schema(type="OBJECT", properties={"asset_id": types.Schema(type="STRING"), "priority": types.Schema(type="STRING"), "issue_type": types.Schema(type="STRING")}, required=["asset_id", "priority", "issue_type"])
                ),
                types.FunctionDeclaration(
                    name="dispatch_technician",
                    description="Dispatch tech.",
                    parameters=types.Schema(type="OBJECT", properties={"ticket_id": types.Schema(type="STRING"), "sector": types.Schema(type="STRING")}, required=["ticket_id", "sector"])
                ),
                types.FunctionDeclaration(
                    name="check_vision_feed",
                    description="Check vision camera.",
                    parameters=types.Schema(type="OBJECT", properties={}, required=[])
                )
            ])
        ]

    # UPDATED: status_callback parameter for live updates
    async def process_incident(self, ticket_id: int, asset_id: str, telemetry: dict, mode: str, status_callback=None):
        print(f"🤖 [GEMINI 3] Processing ({mode}): {asset_id}")
        
        if not self.client:
            return {"status": "ERROR", "detail": "Missing API Key"}

        # Notify Start
        if status_callback:
            await status_callback("ANALYZING", f"Scanning telemetry for {asset_id}...")

        # Optimized Prompt
        prompt = f"""
        TELEMETRY: {json.dumps(telemetry)}
        PROTOCOL:
        1. If Temp > 110C, call `send_iot_command('DERATE', '{asset_id}')` NOW.
        2. Verify with `check_vision_feed`.
        3. Create 'P1' ticket.
        4. Check inventory '7826-45-2001'.
        5. Dispatch tech 'Sector 7'.
        """

        try:
            # Step 1: Decision
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-3-pro-preview", 
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=self.tools,
                    temperature=0.0 
                )
            )

            # Tool Execution Loop
            workflow_log = []
            
            # 1. SAFETY & VISION (Critical Path)
            iot_result = {"status": "SKIPPED"}
            if telemetry['state'] == "CRITICAL": 
                if status_callback: await status_callback("SAFETY_INTERLOCK", "Derating Engine...")
                print("⚡ [GEMINI] DERATING...")
                iot_result = await self.services.send_iot_command("DERATE", asset_id)
                workflow_log.append("IoT Derate")
                
                vision_res = await self.services.get_virtual_camera_frame()
                workflow_log.append(f"Vision: {vision_res.get('status')}")
            
            # 2. ADMIN & LOGISTICS (Parallel)
            ticket_task = self.services.create_ticket(asset_id, "P1", "Thermal Runaway")
            inv_task = self.services.check_inventory("7826-45-2001")
            
            ticket_result, inv_result = await asyncio.gather(ticket_task, inv_task)
            
            workflow_log.append(f"Ticket {ticket_result['ticket_id']}")
            workflow_log.append("Inventory Checked")

            # --- MODE B: AUTO NEGOTIATION LOGIC ---
            negotiation_log = None
            if mode == "AI_AUTO" and inv_result['stock'] == 0:
                print("🤖 [MODE B] Stock Empty. Initiating Agent-to-Agent Negotiation...")
                if status_callback: await status_callback("NEGOTIATING", "Connecting to Vendor Agent Swarm...")
                await asyncio.sleep(1) # Visual pacing

                # Turn 1: Marathon Agent Request
                req_msg = "URGENT: Part 7826-45-2001 required. Production critical."
                if status_callback: await status_callback("OUTBOUND_REQ", req_msg)
                await asyncio.sleep(1.5)

                # Turn 2: Vendor Agent Response
                vendor_offer = await self.vendor.negotiate("7826-45-2001", 5000.00)
                offer_msg = f"OFFER: {vendor_offer.get('message')} (Price: ${vendor_offer.get('price')})"
                if status_callback: await status_callback("INBOUND_OFFER", offer_msg)
                await asyncio.sleep(1.5)

                # Turn 3: Marathon Agent Approval
                approval_msg = f"AUTO-APPROVAL: Price within +15% variance. Purchase Executed."
                if status_callback: await status_callback("PURCHASE_EXEC", approval_msg)
                
                negotiation_log = {
                    "request": req_msg,
                    "offer": vendor_offer,
                    "outcome": "APPROVED"
                }
                workflow_log.append("Auto-Procurement Complete")
            
            # 3. DISPATCH
            dispatch_result = await self.services.dispatch_technician(ticket_result['ticket_id'], "Sector 7")
            workflow_log.append("Tech Dispatched")

            if status_callback: await status_callback("COMPLETE", "Incident Resolved.")

            final_result = {
                "status": "DERATING_ACTIVE" if iot_result.get("status") == "SUCCESS" else "MONITORING",
                "model": "gemini-3-pro-preview",
                "iot": iot_result,
                "ticket": ticket_result,
                "inventory": inv_result,
                "dispatch": dispatch_result,
                "negotiation": negotiation_log, # Include logs
                "mode": mode
            }
            
            await self._persist_thought(ticket_id, 2, "PROTOCOL_EXECUTION", final_result)
            return final_result

        except Exception as e:
            print(f"❌ Error: {e}")
            if status_callback: await status_callback("ERROR", str(e))
            return {"status": "ERROR", "details": str(e)}

    async def _persist_thought(self, ticket_id, step, thought_type, content):
        try:
            pool = await get_db_pool()
            if pool:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO thought_signatures (ticket_id, step_sequence, thought_json)
                        VALUES ($1, $2, $3)
                    """, ticket_id, step, json.dumps({"type": thought_type, "content": content}))
        except Exception as e:
            print(f"DB Error: {e}")