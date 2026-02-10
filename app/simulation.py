import random
import time
from enum import Enum
from dataclasses import dataclass, asdict

class MachineState(Enum):
    NORMAL = "NORMAL"
    CRITICAL = "CRITICAL"

@dataclass
class TelemetryData:
    asset_id: str
    timestamp: float
    rpm: int
    torque_nm: float
    core_temp_c: float          
    thermal_runaway_risk: int   
    capacitor_current: float    
    state: str
    hef_score: float
    cap_health: float
    inv_health: float
    pump_health: float
    valve_health: float
    is_derated: bool

class ExcavatorSimulator:
    def __init__(self, asset_id="HB-001"):
        self.asset_id = asset_id
        self.state = MachineState.NORMAL
        self.core_temp = 55.0       
        self.risk_level = 15        
        self.cap_current = 39.8     
        self.last_fault_timestamp = 0
        self.cooldown_period = 10 
        self.fault_pending = False 
        self.current_mode = "HUMAN"
        self.active_derate = False 
        
        # Component Health
        self.cap_health = 98.0
        self.inv_health = 99.0
        self.pump_health = 97.0
        self.valve_health = 95.0

    def apply_iot_command(self, command: str):
        if command == "DERATE":
            print("🛡️ IOT: ACTIVE DERATING ENGAGED")
            self.active_derate = True
        elif command == "RESET":
            self.active_derate = False
            self.state = MachineState.NORMAL
            self.core_temp = 55.0
            self.risk_level = 15
            self.cap_current = 39.8

    def calculate_hef(self):
        return round((0.1 * self.cap_health) + (0.4 * self.inv_health) + (0.3 * self.pump_health) + (0.2 * self.valve_health), 1)

    def generate_next_frame(self) -> tuple[dict, bool]:
        current_time = time.time()
        trigger_event = False

        # --- PHYSICS ENGINE ---
        if self.fault_pending:
            self.core_temp = 105.0 
            self.risk_level = 85
            self.cap_current = 110.5
            self.fault_pending = False
        
        elif self.state == MachineState.CRITICAL:
            if self.active_derate:
                # DERATED: Cooling down rapidly
                self.core_temp = max(75.0, self.core_temp - 3.0) # Faster cooling
                self.risk_level = max(45, self.risk_level - 5)
                self.cap_current = max(65.0, self.cap_current - 5.0)
            else:
                # UNPROTECTED: Heating up fast (Visual Urgency)
                # Tuned for ~3s response time from Agent
                self.core_temp += random.uniform(0.8, 1.5) 
                self.risk_level = min(100, int(self.risk_level + 5))
                self.cap_current += random.uniform(1.0, 3.0)
                self.inv_health = max(0, self.inv_health - 0.5)

        else:
            # NORMAL
            self.core_temp = 55.0 + random.uniform(-1.0, 1.0)
            self.risk_level = 15 + random.randint(-2, 2)
            self.cap_current = 39.8 + random.uniform(-1.5, 1.5)

        # --- TRIGGER LOGIC ---
        if self.core_temp > 95.0 and self.state == MachineState.NORMAL:
            if (current_time - self.last_fault_timestamp) > self.cooldown_period:
                self.state = MachineState.CRITICAL
                self.last_fault_timestamp = current_time
                self.active_derate = False 
                trigger_event = True 

        # --- OUTPUT ---
        rpm = 1200 if self.active_derate else 1800
        torque = 595.0 if self.active_derate else 850.0

        data = TelemetryData(
            asset_id=self.asset_id,
            timestamp=current_time,
            rpm=rpm,
            torque_nm=torque,
            core_temp_c=round(self.core_temp, 1),
            thermal_runaway_risk=int(self.risk_level),
            capacitor_current=round(self.cap_current, 1),
            state=self.state.value,
            hef_score=self.calculate_hef(),
            cap_health=round(self.cap_health, 1),
            inv_health=round(self.inv_health, 1),
            pump_health=round(self.pump_health, 1),
            valve_health=round(self.valve_health, 1),
            is_derated=self.active_derate
        )
        return asdict(data), trigger_event

    def force_fault(self):
        self.fault_pending = True