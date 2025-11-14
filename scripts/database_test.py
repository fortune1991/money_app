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

    # Insert pots
    pots_data = [
        (1, 'Thailand', 1, 1025.00, 'Mike', '2025-11-03', '2025-11-09', 7, 146.43),
        (2, 'Malaysia', 1, 1225.00, 'Mike', '2025-11-10', '2025-11-16', 7, 175.00),
        (3, 'Singapore', 1, 1750.00, 'Mike', '2025-11-17', '2025-11-23', 7, 250.00)
    ]
    cur.executemany("INSERT OR IGNORE INTO pots (pot_id, pot_name, vault_id, amount, username, start_date, end_date, date_delta, daily_expenditure) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", pots_data)

    # Insert auto transactions for balance updates
    auto_transactions = [
        (1, 'auto_transaction_Thailand_1', '2025-11-04', 1, 1, 0, 0, 'out', -250.0, 'Mike'),
        (2, 'auto_transaction_Thailand_2', '2025-11-07', 1, 1, 0, 0, 'out', -250.0, 'Mike'),
        (3, 'auto_transaction_Thailand_3', '2025-11-10', 1, 1, 0, 0, 'out', -250.0, 'Mike'),
        (4, 'auto_transaction_Malaysia_1', '2025-11-14', 2, 1, 0, 0, 'out', -250.0, 'Mike')
    ]
    cur.executemany("INSERT OR IGNORE INTO transactions (transaction_id, transaction_name, date, pot_id, vault_id, manual_transaction, balance_transaction, type, amount, username) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", auto_transactions)

    # Insert balances
    balances_data = [
        (1, 'Mike', '2025-11-03', 'NZD', 'NZD', 4000.00, 0, 'Thailand'),
        (2, 'Mike', '2025-11-04', 'NZD', 'NZD', 3750.00, 0, 'Thailand'),
        (3, 'Mike', '2025-11-07', 'NZD', 'NZD', 3500.00, 0, 'Thailand'),
        (4, 'Mike', '2025-11-10', 'NZD', 'NZD', 3250.00, 0, 'Malaysia'),
        (5, 'Mike', '2025-11-14', 'NZD', 'NZD', 3000.00, 0, 'Malaysia')
    ]
    cur.executemany("INSERT OR IGNORE INTO balances (balance_id, username, date, bank_currency, cash_currency, bank_balance, cash_balance, active_pot) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", balances_data)

    # Commit and close the connection 
    con.commit()
    con.close()
    print("Database created and initial data inserted successfully.")

create_database()