import datetime
import sqlite3
import warnings

warnings.filterwarnings(
    "ignore",
    message="The default datetime adapter is deprecated",
    category=DeprecationWarning
)

def create_database():
    # Establish a connection to the database or create it if it doesn't exist
    db_path = "/Users/michaelfortune/Developer/projects/money/money_app/money.db" 
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Create users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT NOT NULL PRIMARY KEY
        )
    """)
    
    # Create vaults table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vaults (
            vault_id INTEGER PRIMARY KEY,
            vault_name TEXT NOT NULL,
            username TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)

    # Create pots table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pots (
            pot_id INTEGER PRIMARY KEY,
            pot_name TEXT NOT NULL,
            vault_id INTEGER,
            amount REAL NOT NULL,
            username TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            date_delta INTEGER NOT NULL,
            daily_expenditure REAL,
            FOREIGN KEY (vault_id) REFERENCES vaults(vault_id),
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)

    # Create transactions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY,
            transaction_name TEXT NOT NULL,
            date DATE NOT NULL,
            pot_id INTEGER,
            vault_id INTEGER,
            manual_transaction INTEGER NOT NULL,
            balance_transaction INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            username TEXT NOT NULL,
            FOREIGN KEY (pot_id) REFERENCES pots(pot_id),
            FOREIGN KEY (vault_id) REFERENCES vaults(vault_id),
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)

    date = datetime.datetime.today()
    
    # Create balances table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS balances (
            balance_id INT PRIMARY KEY,
            username TEXT NOT NULL,
            date DATE NOT NULL,
            bank_currency TEXT NOT NULL,
            cash_currency TEXT NOT NULL,
            bank_balance REAL NOT NULL,
            cash_balance REAL NOT NULL,
            active_pot TEXT
        )
    """)

    # --- Insert initial values ---
    # Insert user
    cur.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", ("Mike",))

    # Insert vaults
    vaults = [("Daily expenses", "Mike"), ("Miscellaneous", "Mike")]
    cur.executemany("INSERT OR IGNORE INTO vaults (vault_name, username) VALUES (?, ?)", vaults)

    # Insert balances
    cur.execute("""
        INSERT OR IGNORE INTO balances (balance_id, username, date, bank_currency, cash_currency, bank_balance, cash_balance, active_pot)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (1, "Mike", date, "NZD", "NZD", 0, 0, None))

    cur.execute("""
        INSERT OR IGNORE INTO balances (balance_id, username, date, bank_currency, cash_currency, bank_balance, cash_balance, active_pot)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (2, "Mike", date, "NZD", "NZD", 0, 0, None))

    # Commit and close the connection 
    con.commit()
    con.close()
    print("Database created and initial data inserted successfully.")

create_database()