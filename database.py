import sqlite3

DB_NAME = "secure_vault.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Table Clients
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            full_name TEXT,
            risk_level TEXT
        )
    ''')
    
    # Table Cards
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            card_number TEXT PRIMARY KEY,
            owner_email TEXT,
            is_active BOOLEAN,
            last_error TEXT
        )
    ''')
    
    # Seeding
    cursor.execute("INSERT OR REPLACE INTO users VALUES ('chris@savy.com', 'Christopher Artigas', 'LOW')")
    cursor.execute("INSERT OR REPLACE INTO users VALUES ('jc.delatour@prestance-luxe.fr', 'Jean-Christophe de la Tour', 'MEDIUM')")
    
    cursor.execute("INSERT OR REPLACE INTO cards VALUES ('4556 1234 5678 9012', 'chris@savy.com', 1, 'Transaction declined: Insufficient funds (Mexico)')")
    cursor.execute("INSERT OR REPLACE INTO cards VALUES ('1234 5678 9012 3456', 'jc.delatour@prestance-luxe.fr', 1, 'No recent issues')")
    
    conn.commit()
    conn.close()

def get_card_info(real_card_number: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT is_active, last_error FROM cards WHERE card_number = ?", (real_card_number,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"active": bool(row[0]), "recent_error": row[1]}
    return None

def get_user_info(real_email: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT risk_level, full_name FROM users WHERE email = ?", (real_email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"risk_level": row[0], "full_name": row[1]}
    return None

def block_card(real_card_number: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE cards SET is_active = 0 WHERE card_number = ?", (real_card_number,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def unblock_card(real_card_number: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE cards SET is_active = 1 WHERE card_number = ?", (real_card_number,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def get_all_cards():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT card_number, owner_email, is_active, last_error FROM cards")
    rows = cursor.fetchall()
    conn.close()
    return [
        {"card_number": r[0], "owner": r[1], "active": bool(r[2]), "status_text": r[3]}
        for r in rows
    ]

if __name__ == "__main__":
    init_db()
    print("Database initialized with dummy data.")