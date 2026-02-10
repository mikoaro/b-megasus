import os
import asyncpg

# SINGLETON POOL
GLOBAL_POOL = None

async def connect_to_db():
    global GLOBAL_POOL
    dsn = os.environ.get("DB_URL")
    if not dsn:
        print("⚠️ DB_URL not set.")
        return
    try:
        GLOBAL_POOL = await asyncpg.create_pool(dsn, min_size=1, max_size=10)
        print("✅ Database Pool Created (Singleton)")
    except Exception as e:
        print(f"❌ DB Pool Creation Error: {e}")

async def close_db_connection():
    global GLOBAL_POOL
    if GLOBAL_POOL:
        await GLOBAL_POOL.close()
        print("🛑 Database Pool Closed")

async def get_db_pool():
    global GLOBAL_POOL
    if not GLOBAL_POOL:
        await connect_to_db()
    return GLOBAL_POOL

async def init_db():
    pool = await get_db_pool()
    if pool:
        try:
            async with pool.acquire() as conn:
                print("🔄 RESETTING SCHEMA (Dropping old tables)...")
                
                # --- DANGER: DROP TABLES TO FIX SCHEMA MISMATCH ---
                # This ensures the tables are recreated with the correct columns (ticket_ref, etc.)
                await conn.execute("DROP TABLE IF EXISTS tickets;")
                await conn.execute("DROP TABLE IF EXISTS dispatches;")
                # We keep inventory as it has the same schema, but dropping it guarantees a clean seed
                await conn.execute("DROP TABLE IF EXISTS inventory;")
                
                # 1. Thought Signatures (Keep Logs)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS thought_signatures (
                        id SERIAL PRIMARY KEY,
                        ticket_id BIGINT,
                        step_sequence INT,
                        thought_json JSONB,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)
                
                # 2. Incident Transcripts
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS incident_transcripts (
                        id SERIAL PRIMARY KEY,
                        session_id TEXT,
                        user_id TEXT,
                        asset_id TEXT,
                        transcript_json JSONB,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)

                # 3. Inventory (ERP Integration)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS inventory (
                        part_number TEXT PRIMARY KEY,
                        name TEXT,
                        stock_level INT,
                        unit_cost DECIMAL(10, 2),
                        location TEXT
                    );
                """)

                # 4. Tickets (CRM Integration) - RECREATED WITH CORRECT COLUMNS
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS tickets (
                        id SERIAL PRIMARY KEY,
                        ticket_ref TEXT UNIQUE,
                        asset_id TEXT,
                        issue_type TEXT,
                        status TEXT,
                        priority TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)

                # 5. Dispatches (FSM Integration)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS dispatches (
                        id SERIAL PRIMARY KEY,
                        work_order_ref TEXT UNIQUE,
                        ticket_ref TEXT,
                        technician_name TEXT,
                        destination TEXT,
                        status TEXT,
                        eta TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)

                # Seed Data
                await conn.execute("""
                    INSERT INTO inventory (part_number, name, stock_level, unit_cost, location)
                    VALUES 
                    ('7826-45-2001', 'Hybrid Inverter Pump', 0, 4500.00, 'Warehouse A'),
                    ('708-2L-00460', 'Hydraulic Pump Main', 2, 12000.00, 'Warehouse B')
                    ON CONFLICT (part_number) DO UPDATE SET stock_level = EXCLUDED.stock_level;
                """)

            print("✅ Database Schema Updated & Initialized")
        except Exception as e:
            print(f"❌ Table Init Error: {e}")