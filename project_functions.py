import datetime,io,os,sqlite3,math
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import requests
import seaborn as sns
import streamlit as st
from datetime import timedelta
from PIL import Image, ImageDraw, ImageFont
from project_classes import User,Vault,Pot,Transaction,Balances
from streamlit_option_menu import option_menu
from tabulate import tabulate
from time import sleep

import warnings
warnings.filterwarnings("ignore",message="The default datetime adapter is deprecated",category=DeprecationWarning)
    
def balance_transaction(con, transaction_id, pots, vaults, balances, previous_balances, user, username, balance_transaction_name, pot_name, date, amount, transaction_type):
    """
    Automatically creates a transaction for the active pot based on changes in balances.
    Prevents over-correction of pot balances and updates the pot's transactions in memory.

    Parameters:
        con: SQLite connection
        pots: dict of Pot objects
        vaults: dict of Vault objects
        user: User object
        username: str
        balances: current Balances object
        previous_balances: previous Balances object
        active_pot: str (name of the pot to adjust)
    Returns:
        Transaction object if created, else None
    """
    
    manual_transaction = 1
    balance_transaction = 1

    # Find the pot and vault
    selected_pot = next((p for p in pots.values() if p.pot_name == pot_name and p.username == username), None)
    if not selected_pot:
        print(f"Pot '{pot_name}' not found.")
        return None

    selected_vault = vaults.get(f"vault_{selected_pot.vault_id}")
    if not selected_vault:
        print(f"Vault for pot '{selected_pot}' not found.")
        return None

    # Create Transaction object
    transaction = Transaction(
        transaction_id=transaction_id,
        transaction_name=balance_transaction_name,
        date=date,
        pot=selected_pot,
        vault=selected_vault,
        manual_transaction=manual_transaction,
        balance_transaction=balance_transaction,
        type=transaction_type,
        amount=amount,
        user=user
    )

    # Add transaction to pot in memory
    selected_pot.add_transaction(transaction)

    # Insert transaction into DB
    cur = con.cursor()
    cur.execute(
        "INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            transaction_id,
            balance_transaction_name,
            date,
            selected_pot.pot_id,
            selected_vault.vault_id,
            manual_transaction,
            balance_transaction,
            transaction_type,
            amount,
            username
        )
    )
    con.commit()
    cur.close()

    # Update previous balances so next call won't repeat the same adjustment
    previous_balances.bank_balance = balances.bank_balance
    previous_balances.cash_balance = balances.cash_balance

    return transaction

def auto_transaction(con, pots, vaults, user, username, balances, previous_balances, active_pot):
    """
    Automatically creates a transaction for the active pot based on changes in balances.
    Prevents over-correction of pot balances and updates the pot's transactions in memory.

    Parameters:
        con: SQLite connection
        pots: dict of Pot objects
        vaults: dict of Vault objects
        user: User object
        username: str
        balances: current Balances object
        previous_balances: previous Balances object
        active_pot: str (name of the pot to adjust)
    Returns:
        Transaction object if created, else None
    """
    if active_pot is None:
        return None
    
    cur = con.cursor()
    # determine the balance timestamp you want to generate transactions for (e.g. latest balance row)
    cur.execute("SELECT date, balance_id FROM balances WHERE username=? ORDER BY datetime(date) DESC LIMIT 1", (username,))
    row = cur.fetchone()
    if not row:
        cur.close()
        return None
    latest_balance_date, latest_balance_id = row

    # see if an auto transaction already exists for that balance timestamp
    cur.execute("""
        SELECT 1 FROM transactions
        WHERE username=? AND transaction_name LIKE 'auto_transaction_%' AND datetime(date) >= datetime(?)
        LIMIT 1
    """, (username, latest_balance_date))
    if cur.fetchone():
        cur.close()
        return None  # nothing to do: already created

    # Calculate signed delta
    if balances.cash_currency == balances.bank_currency:
        delta = balances.combined_balance(balances) - previous_balances.combined_balance(previous_balances)
    else:
        current_balance_cash = currency_convert(balances.bank_currency, balances.cash_currency, balances.cash_balance)
        current_balance = balances.bank_balance + current_balance_cash
        previous_balance_cash = currency_convert(previous_balances.bank_currency, previous_balances.cash_currency, previous_balances.cash_balance)
        previous_balance = previous_balances.bank_balance + previous_balance_cash
        delta = current_balance - previous_balance

    if delta == 0:
        return None  # No change, exit

    transaction_type = "in" if delta > 0 else "out"
    amount = delta  # signed: +ve for in, -ve for out
    date = datetime.datetime.now()
    manual_transaction = 0
    balance_transaction = 0

    # Find the pot and vault
    selected_pot = next((p for p in pots.values() if p.pot_name == active_pot and p.username == username), None)
    if not selected_pot:
        print(f"Pot '{active_pot}' not found.")
        return None

    selected_vault = vaults.get(f"vault_{selected_pot.vault_id}")
    if not selected_vault:
        print(f"Vault for pot '{active_pot}' not found.")
        return None

    # Cap the amount to avoid overfilling or overdrawing
    if transaction_type == "in":
        max_add = selected_pot.amount - selected_pot.pot_value()
        amount = min(amount, max_add)
    else:  # out
        max_withdraw = -selected_pot.pot_value()  # negative
        amount = max(amount, max_withdraw)

    if amount == 0:
        return None  # Nothing to do

    # Generate transaction ID
    cur.execute("SELECT MAX(transaction_id) FROM transactions")
    start_transaction = (cur.fetchone()[0] or 0) + 1

    transaction_name = f"auto_transaction_{active_pot}_{start_transaction}"

    # Create Transaction object
    transaction = Transaction(
        transaction_id=start_transaction,
        transaction_name=transaction_name,
        date=date,
        pot=selected_pot,
        vault=selected_vault,
        manual_transaction=manual_transaction,
        balance_transaction=balance_transaction,
        type=transaction_type,
        amount=amount,
        user=user
    )

    # Add transaction to pot in memory
    selected_pot.add_transaction(transaction)

    # Insert transaction into DB
    cur.execute(
        "INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            start_transaction,
            transaction_name,
            date,
            selected_pot.pot_id,
            selected_vault.vault_id,
            manual_transaction,
            balance_transaction,
            transaction_type,
            amount,
            username
        )
    )
    con.commit()
    cur.close()

    # Update previous balances so next call won't repeat the same adjustment
    previous_balances.bank_balance = balances.bank_balance
    previous_balances.cash_balance = balances.cash_balance

    return transaction

def submit_transaction(con,transaction_id,pots,vaults,user,username,transaction_name,pot_name,date,amount,transaction_type):
    
    # Handle None or invalid transaction_id
    try:
        transaction_id = int(float(transaction_id))
    except (TypeError, ValueError):
        return None
    
    
    manual_transaction = 1
    balance_transaction = 0
    
    # Find the pot using a simple loop
    selected_pot = None
    selected_vault = None
    for pot in pots.values():
        if pot.pot_name == pot_name and pot.username == username: 
            selected_pot = pot
            selected_vault = vaults.get(f"vault_{pot.vault_id}")
            break

    if selected_pot:
        try:
            #Input all information into the Class
            transaction = Transaction(transaction_id=transaction_id,transaction_name=transaction_name,date=date,pot=selected_pot,vault=selected_vault,manual_transaction=manual_transaction,balance_transaction=balance_transaction,type=transaction_type,amount=amount,user=user)
            transaction_data = [(transaction_id,transaction_name,date,selected_pot.pot_id,selected_vault.vault_id,manual_transaction,balance_transaction,transaction_type,amount,username)]
            if transaction:
                # Save transaction to database
                cur = con.cursor()
                cur.executemany("INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?,?,?)",transaction_data)
                con.commit()
                cur.close()
            return transaction

        except ValueError as e:
            print(f"Error: {e}")
            
        except Exception as e:  
            print(f"An unexpected error occurred: {e}")
    else:
        print(f"pot '{pot_name}' not found. Please enter a valid pot name.")

def update_transaction(con, transaction_id, pots, vaults, user, username, transaction_name, pot_name, date, amount, transaction_type):
    # Handle None or invalid transaction_id
    try:
        transaction_id = int(float(transaction_id))
    except (TypeError, ValueError):
        return None
    
    manual_transaction = 1
    balance_transaction = 0

    # Find the pot and its vault
    selected_pot = None
    selected_vault = None
    for pot in pots.values():
        if pot.pot_name == pot_name and pot.username == username: 
            selected_pot = pot
            selected_vault = vaults.get(f"vault_{pot.vault_id}")
            break

    if selected_pot:
        try:
            # Create updated transaction object
            transaction = Transaction(
                transaction_id=transaction_id,
                transaction_name=transaction_name,
                date=date,
                pot=selected_pot,
                vault=selected_vault,
                manual_transaction=manual_transaction,
                balance_transaction=balance_transaction,
                type=transaction_type,
                amount=amount,
                user=user
            )

            if transaction:
                # Update transaction in database
                cur = con.cursor()
                cur.execute("""
                    UPDATE transactions
                    SET transaction_name = ?,
                        date = ?,
                        pot_id = ?,
                        vault_id = ?,
                        manual_transaction = ?,
                        balance_transaction = ?,
                        type = ?,
                        amount = ?,
                        username = ?
                    WHERE transaction_id = ?
                """, (
                    transaction_name,
                    date,
                    selected_pot.pot_id,
                    selected_vault.vault_id,
                    manual_transaction,
                    balance_transaction,
                    transaction_type,
                    amount,
                    username,
                    transaction_id
                ))
                con.commit()
                cur.close()
            return transaction

        except ValueError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
    else:
        print(f"Pot '{pot_name}' not found. Please enter a valid pot name.")

def convert_date(date_input):
    """
    Convert a string in 'YYYY-MM-DD', or a pandas Timestamp
    to a datetime.date object.
    """
    # If already a datetime.date, return as-is
    if isinstance(date_input, datetime.date) and not isinstance(date_input, datetime.datetime):
        return date_input
    
    # If pandas Timestamp, convert directly
    if isinstance(date_input, pd.Timestamp):
        return date_input.to_pydatetime().date()
    
    # If string, remove time part if present
    if isinstance(date_input, str):
        if ' ' in date_input:
            date_input = date_input.split(' ')[0]

        # Try 'YYYY-MM-DD' first
        try:
            return datetime.datetime.strptime(date_input, "%Y-%m-%d").date()
        except ValueError:
            pass
    
    # If not string or pandas Timestamp
    raise TypeError(f"Invalid type for convert_date: {type(date_input)}. Expected str or pd.Timestamp.")
    
def summary(vaults, pots, dynamic_width=True):
    # Prepare data
    data = []
    if len(pots) == 0:
        pot_value = 0
        vault_amount = 0
        initial_amount = 0
        data.append(['Daily Expenses', 'no pots created', 'Initial Amount', initial_amount])
        data.append(['Daily Expenses', 'no pots created', 'Remaining Balance', pot_value])
    else:
        for i in vaults:
            vault = vaults[i]
            vault_name_clean = vault.vault_name  # keep vault name only
            for j in pots:
                if pots[j].vault == vault:
                    pot_value = pots[j].pot_value()
                    data.append([vault_name_clean, pots[j].pot_name, 'Initial Amount', pots[j].amount])
                    data.append([vault_name_clean, pots[j].pot_name, 'Remaining Balance', pot_value])

    df = pd.DataFrame(data, columns=['Vault', 'Pot', 'Metric', 'Amount ($)'])
    pivot_df = df.pivot_table(index=['Vault', 'Pot'], columns='Metric', values='Amount ($)', fill_value=0).reset_index()

    # Seaborn styling
    sns.set_theme(style="darkgrid", palette="Blues_d")
    plt.rcParams.update({
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 12,
        "axes.labelweight": "bold",
        "legend.frameon": True,
        "legend.framealpha": 0.9,
        "legend.fancybox": True,
        "legend.loc": "upper center",
        "font.size": 11,
    })

    vaults_unique = pivot_df['Vault'].unique()
    pots_unique = pivot_df['Pot'].unique()
    num_pots = len(pots_unique)

    # Dynamic sizing
    fig_width = max(10, num_pots * 1.2)  # figure width grows with number of pots
    fig_height = 6
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    colors = {
        'Initial Amount': '#fdb43fff',
        'Remaining Balance': '#61b27eff',
    }

    bar_width = max(0.25, 0.6 / num_pots)
    vault_spacing = 0.1
    vault_positions = np.arange(len(vaults_unique)) * vault_spacing
    vault_centers = []

    for i, vault in enumerate(vaults_unique):
        vault_data = pivot_df[pivot_df['Vault'] == vault]
        x_positions = []

        for j, pot in enumerate(pots_unique):
            row = vault_data[vault_data['Pot'] == pot]
            if not row.empty:
                initial = row['Initial Amount'].values[0]
                remaining = row['Remaining Balance'].values[0]
                x = vault_positions[i] + (j - (len(vault_data)-1)/2) * bar_width
                x_positions.append(x)

                # Draw bars
                ax.bar(x, initial, width=bar_width, color=colors['Initial Amount'],
                       edgecolor='white', alpha=0.8,
                       label='Initial Amount' if i == 0 and j == 0 else "")
                ax.bar(x, remaining, width=bar_width, color=colors['Remaining Balance'],
                       edgecolor='white', alpha=0.9,
                       label='Remaining Balance' if i == 0 and j == 0 else "")

                # Pot label inside bar (only name, smaller font)
                ax.text(x, remaining / 2, pot, ha='center', va='center',
                        color='white', fontsize=7, fontweight='bold', wrap=True)

        vault_centers.append(np.mean(x_positions) if x_positions else vault_positions[i])

    # Vault labels centered
    ax.set_xticks(vault_centers)
    ax.set_xticklabels(vaults_unique, fontsize=11, fontweight='bold')

    ax.set_ylabel('Amount ($)', fontsize=12, fontweight='bold')
    ax.legend(title='Key', bbox_to_anchor=(0.5, -0.2), loc='upper center', ncol=2)
    ax.set_ylim(bottom=0)
    sns.despine(left=True, bottom=True)
    plt.tight_layout()

    return fig

def transaction_summary(transactions): 
    table = []
    for i in transactions:
        row = [transactions[i].transaction_id,transactions[i].transaction_name,transactions[i].date,transactions[i].amount]
        table.append(row)

    print(f"\n{tabulate(table,headers=["transaction_id","transaction_name","date","amount"],tablefmt="heavy_grid")}\n")
    
def create_user(con,*args):
    cur = con.cursor()
    if args:
        username = args[0] if isinstance(args[0], str) else str(args[0])
        user = User(username)
    else:
        print("Now firstly, what is your name?: ")
        username = input()
        user = User(username)

    cur.execute("INSERT INTO users VALUES(?)",(username,))
    con.commit()
    cur.close()
    return user

def create_pot(con,x,vaults,user,username,spend_type,pot_name,pot_budget,start_date,end_date):
    pot_vault = spend_type
    selected_vault = None
    for vault in vaults.values():
        if vault.vault_name == pot_vault and vault.username == username:
            selected_vault = vault
    if selected_vault:
        cur = con.cursor()
        pot_id = x + 1
        amount = pot_budget

        #Input all information into the Class
        try:
            pot = Pot(pot_id=pot_id,pot_name=pot_name,vault=selected_vault,amount=amount,user=user,start_date=start_date,end_date=end_date)
            if pot:
                # save pot to database
                pots_data = []
                pots_data.append((pot.pot_id,pot.pot_name,pot.vault_id,pot.amount,username,pot.start_date,pot.end_date,pot.date_delta,pot.daily_expenditure))
                cur.executemany("INSERT INTO pots VALUES(?,?,?,?,?,?,?,?,?)",pots_data)
                con.commit()
                cur.close()
            else:
                print("\nERROR: pot not created succesfully")
            
            return pot
        
        except ValueError as e:  
            return print(f"Error: {e}, Please try again")
            
        except Exception as e:  
            return print(f"An unexpected error occurred when creating pot: {e}, Please try again")

    else:
        return print(f"\nVault '{pot_vault}' not found when creating pot. Please enter a valid vault name.")
    
def update_pot(con, x, vaults, user, username, spend_type, pot_id, pot_name, pot_budget, start_date, end_date):
    pot_vault = spend_type
    selected_vault = None
    for vault in vaults.values():
        if vault.vault_name == pot_vault and vault.username == username:
            selected_vault = vault

    if selected_vault:
        cur = con.cursor()
        amount = pot_budget
        # Create date objects
        start_date = convert_date(start_date)
        end_date = convert_date(end_date)

        try:
            pot = Pot(
                pot_id=pot_id,
                pot_name=pot_name,
                vault=selected_vault,
                user=user,
                start_date=start_date,
                end_date=end_date,
                amount=amount
            )

            if pot:
                # UPDATE instead of INSERT
                cur.execute("""
                    UPDATE pots
                    SET pot_name = ?, vault_id = ?, amount = ?, username = ?, 
                        start_date = ?, end_date = ?, date_delta = ?, daily_expenditure = ?
                    WHERE pot_id = ?
                """, (
                    pot.pot_name,
                    pot.vault_id,
                    pot.amount,
                    username,
                    pot.start_date,
                    pot.end_date,
                    pot.date_delta,
                    pot.daily_expenditure,
                    pot.pot_id
                ))

                # Commit changes to DB
                con.commit()
                cur.close()
                return pot

            else:
                print("\nERROR: pot not created successfully")

        except ValueError as e:
            print(f"Error: {e}. Please try again.")

        except Exception as e:
            print(f"An unexpected error occurred when updating pot: {e}. Please try again.")
    else:
        print(f"\nVault '{pot_vault}' not found when updating pot. Please enter a valid vault name.")
        
def create_vault(con,x,user,username,vault_name):
    cur = con.cursor()
    vault_id = x + 1    
    #Input all information into the Class
    vault = Vault(vault_id=vault_id,vault_name=vault_name,user=user)
    if vault:
        # save vault to database
        vaults_data = []
        vaults_data.append((vault.vault_id,vault.vault_name,username))
        cur.executemany("INSERT INTO vaults VALUES(?,?,?)",vaults_data)
        con.commit()
        cur.close()
    else:
        print("ERROR: vault not created succesfully")
    return vault

def create_profile(con):
    # Create a User object
    user = create_user(con)
    username = user.username
    # Count number of existing vaults in database. if not exist = 0
    start_vault = count_vaults(con)
    if start_vault == None:
        start_vault = 0
    # Count number of existing pots in database. if not exist = 0
    start_pot = count_pots(con)
    if start_pot == None:
        start_pot = 0
    # Create a Vault object with valid data
    no_vaults = 2
    options=["Daily expenses", "Miscellaneous"]
    vaults = {}
    try:
        for x in range(no_vaults):
            vaults["vault_{0}".format(start_vault+x)] = create_vault(con,(start_vault+x),user,username,options[x])
    except ValueError as e:  
        print(f"\nError: {e}")
    except Exception as e:  
        print(f"\nAn unexpected error occurred: {e}")

    # Create Pot objects with valid data
    pots = {}

    # Create Previous Balances object
    balance_id = 0
    date = datetime.datetime.today()
    bank_currency = "NZD"
    bank_balance = 0.00
    cash_currency = "NZD"
    cash_balance = 0.00
    previous_balances = Balances(balance_id,username,date,bank_currency,bank_balance,cash_currency,cash_balance)

    # Create Balances object
    balance_id = 1
    date = datetime.datetime.today()
    bank_currency = "NZD"
    bank_balance = 0.00
    cash_currency = "NZD"
    cash_balance = 0.00
    balances = Balances(balance_id,username,date,bank_currency,bank_balance,cash_currency,cash_balance)

    # Submit Balances to DB
    balance_update(con,previous_balances,balances,bank_balance,cash_balance)

    #refresh user data
    vaults, vault_ids,pots,pot_ids,transactions,transaction_ids,balances,previous_balances = refresh_user_data(con,user,username)
    #refresh pot/vault values
    pots,vaults = refresh_pot_vault_values(pots,vaults)

    # Summary of the vaults and pots values
    print("\nSee below list of vaults and their summed values")
    summary(vaults,pots)
    return user,vaults, vault_ids,pots,pot_ids,transactions,transaction_ids,balances
    

def balance_update(con, balances, bank_balance, cash_balance, pot_names_list, bank_currency, cash_currency, active_pot=None):
    # New timestamp
    date = datetime.datetime.today()
    # Connect to the db
    cur = con.cursor()

    # Fetch latest recorded balance for this user
    cur.execute("""
        SELECT bank_balance, cash_balance, bank_currency, cash_currency, active_pot
        FROM balances
        WHERE username = ?
        ORDER BY date DESC
        LIMIT 1
    """, (balances.username,))
    last = cur.fetchone()

    # Detect if any change occurred 
    if last:
        last_bank_balance, last_cash_balance, last_bank_currency, last_cash_currency, last_active_pot = last
        if (
            float(last_bank_balance) == float(bank_balance) and
            float(last_cash_balance) == float(cash_balance) and
            last_bank_currency == bank_currency and
            last_cash_currency == cash_currency and
            last_active_pot == active_pot
        ):
            # No changes — skip updating
            cur.close()
            return balances

    # Something changed → Update object and insert new row
    balances.update_date(date)
    balances.update_bank_balance(bank_balance)
    balances.update_cash_balance(cash_balance)
    balances.update_bank_currency(bank_currency)
    balances.update_cash_currency(cash_currency)
    if active_pot is not None:
        balances.update_active_pot(balances, pot_names_list, active_pot)

    # Get the current highest balance_id for this user
    cur.execute("SELECT MAX(balance_id) FROM balances WHERE username = ?", (balances.username,))
    result = cur.fetchone()
    max_balance_id = result[0] if result[0] is not None else 0

    # New balance_id
    new_balance_id = max_balance_id + 1

    # Prepare data for insertion
    balances_data = (
        new_balance_id,
        balances.username,
        balances.date,
        balances.bank_currency,
        balances.cash_currency,
        balances.bank_balance,
        balances.cash_balance,
        balances.active_pot
    )

    # Insert new row
    cur.execute("INSERT INTO balances VALUES (?,?,?,?,?,?,?,?)", balances_data)
    con.commit()
    cur.close()

    # Update the object's balance_id to the new one
    balances.balance_id = new_balance_id

    return balances

def re_user(con, name):
    cur = con.cursor()
    # Search the users database for all information for the defined user
    res = cur.execute("SELECT * FROM users WHERE username = ?", (name,))
    returned_user = res.fetchall()
    if returned_user:
        username = returned_user[0][0]  
        user = User(username=username)
    else:
        print(f"User {name} not found.")
        user = None
    cur.close()
    return user

def re_vaults(con,name,user):
    cur = con.cursor()
    # Create vault and vault_ids variables
    vaults = {}
    vault_ids = []
    # Searcb the vaults database for all information for defined user 
    res = cur.execute("SELECT * FROM vaults WHERE username = ?", (str(name),))
    returned_vaults = res.fetchall()
    for vault in returned_vaults:
        # Create variables
        vault_ids.append(int(vault[0]))
        vault_id = int(vault[0])
        vault_name = vault[1]
        # Create vault instance
        vault = Vault(vault_id=vault_id,vault_name=vault_name,user=user)
        # Add instance to vaults object dictionary
        vaults["vault_{0}".format(vault_id)] = vault
    cur.close()
    return vaults,vault_ids

def re_pots(con,vaults,vault_ids,user):
    cur = con.cursor()
    # Create pots and pot_id variables
    pots = {}
    pot_ids = []
    # Searcb the vaults database for all information for defined vault_ids
    for vault in vault_ids:
        res = cur.execute("SELECT * FROM pots WHERE vault_id = ?",(vault,))
        returned_pots = res.fetchall()
        for pot in returned_pots:
            # Create variables
            pot_id = int(pot[0])
            pot_name = pot[1]
            amount = int(pot[3])
            vault = vaults[f"vault_{pot[2]}"]
            start_date = convert_date(pot[5])
            end_date = convert_date(pot[6])
            # Convert dates
            start_date = convert_date(start_date)
            end_date = convert_date(end_date)
            # Create pot instance
            pot = Pot(pot_id=pot_id,pot_name=pot_name,vault=vault,amount=amount,user=user,start_date=start_date,end_date=end_date)
            # Add instance to pots object dictionary
            pots[f"pot_{pot.pot_id}"] = pot
            # Append pot_id to list
            pot_ids.append(pot_id)

    cur.close()
    return pots,pot_ids

def re_transactions(con,pots,vaults,pot_ids,user):
    cur = con.cursor()
    # Create transaction_id variables
    transactions = {}
    transaction_ids = []
    # Searcb the pots database for all information for defined pot_ids
    for pot in pot_ids:
        res = cur.execute("SELECT * FROM transactions WHERE pot_id = ?",(pot,))
        returned_transactions = res.fetchall()

        for transaction in returned_transactions:
            # Create variables
                transaction_id = int(transaction[0])
                transaction_name = transaction[1]
                date = convert_date(transaction[2])
                manual_transaction = (transaction[5])
                balance_transaction = (transaction[6])
                type = (transaction[7])
                amount = int(transaction[8])
                pot = pots[f"pot_{transaction[3]}"] # Dictionary key format is "Pot_1: Object"
                vault = vaults[f"vault_{transaction[4]}"] # Dictionary key format is "Vault_1: Object"
                # Create transaction instance
                transaction = Transaction(transaction_id=transaction_id,transaction_name=transaction_name,date=date,pot=pot,vault=vault,manual_transaction=manual_transaction,balance_transaction=balance_transaction,type=type,amount=amount,user=user)
                # Add instance to transactions object dictionary
                transactions[f"transaction_{transaction.transaction_id}"] = transaction
                # Append transaction_id to list
                transaction_ids.append(transaction_id)

    cur.close()
    return transactions,transaction_ids

def re_balances(con,username):
    cur = con.cursor()
    # Searcb the database for balances related to username
    res = cur.execute("""
        SELECT * FROM balances
        WHERE username = ?
        AND balance_id = (
            SELECT MAX(balance_id) FROM balances WHERE username = ?
        )
    """, (username, username))

    returned_balances = res.fetchall()
    if not returned_balances:
        raise ValueError("No balances found for this user.")

    # Unpack the list and create variables
    (balance_id, username, date, bank_currency, cash_currency, bank_balance, cash_balance, active_pot) = returned_balances[0]

    # Create balance instance
    balances = Balances(balance_id=balance_id,username=username,date=date,bank_currency=bank_currency,cash_currency=cash_currency,bank_balance=bank_balance,cash_balance=cash_balance,active_pot=active_pot)
    cur.close()
    return balances

def count_pots(con):
    cur = con.cursor()
    res = cur.execute("""
        SELECT pot_id 
        FROM pots 
        ORDER BY pot_id DESC 
        LIMIT 1;
    """)
    highest_pot = res.fetchone() 
    cur.close()
    return highest_pot[0] if highest_pot else 0
        
def count_vaults(con):
    cur = con.cursor()
    res = cur.execute("""
        SELECT vault_id
        FROM vaults
        ORDER BY vault_id DESC
        LIMIT 1;             
    """)
    highest_vault = res.fetchone() 
    cur.close()
    return highest_vault[0] if highest_vault else 0
        
def count_transactions(con):
    cur = con.cursor()
    res = cur.execute("""
        SELECT transaction_id 
        FROM transactions
        ORDER BY transaction_id DESC 
        LIMIT 1;
    """)
    highest_transaction = res.fetchone()  
    cur.close()
    return highest_transaction[0] if highest_transaction else 0

def del_profile(con,user,username):
    try:
        # Delete all related data first
        cur = con.cursor()
        cur.execute("DELETE FROM balances WHERE username = ?",(username,))
        cur.execute("DELETE FROM transactions WHERE username = ?",(username,))
        cur.execute("DELETE FROM pots WHERE username = ?",(username,))
        cur.execute("DELETE FROM vaults WHERE username = ?",(username,))
        # Finally,delete the user
        cur.execute("DELETE FROM users WHERE username = ?",(username,))
        con.commit()
        cur.close()
        print("\nProfile deleted successfully.")

    except sqlite3.Error as e:
        print(f"\nError deleting profile: {e}")

def del_vault(con,user,vaults,username,vault_name):
    # Search for the vault that matches both the name and the username
    selected_vault = None
    for vault in vaults.values():
        if vault.vault_name == vault_name and vault.username == username:
            selected_vault = vault
            break

    if selected_vault:
        vault_id = selected_vault.vault_id
        # Proceed with deletion of related data first
        cur = con.cursor()
        cur.execute("DELETE FROM transactions WHERE vault_id = ?",(vault_id,))
        cur.execute("DELETE FROM pots WHERE vault_id = ?",(vault_id,))
        # Finally delete the vault
        cur.execute("DELETE FROM vaults WHERE vault_id = ?",(vault_id,))
        con.commit()
        cur.close()
        return True

    else:
        print(f"\nVault '{vault_name}' not found for user '{username}'.")
        print(f"Available vaults for {username}: {[v.vault_name for v in vaults.values() if v.username == username]}\n")
        return False

def del_pot(con,user,pots,username,pot_names_dict,pot_id):
    # Search for the pot that matches both the name and the username
    selected_pot = None
    for pot in pots.values():
        if pot.pot_id == pot_id and pot.username == username:
            selected_pot = pot
            break

    if selected_pot:
        pot_id = selected_pot.pot_id
        # Proceed with deletion of related data first
        cur = con.cursor()
        cur.execute("DELETE FROM transactions WHERE pot_id = ?",(pot_id,))
        # Finally delete the pot
        cur.execute("DELETE FROM pots WHERE pot_id = ?",(pot_id,))
        con.commit()
        cur.close()
        return True

    else:
        if pot_id == None:
            return False
        pot_name = pot_names_dict[str(pot_id)]
        print(f"\nPot '{pot_name}' not found for user '{username}'.")
        print(f"Available pots for {username}: {[p.pot_name for p in pots.values() if p.username == username]}")
        return False

def del_transaction(con,user,transactions,username,transaction_id):
    # Search for the transaction that matches both the id and the username
    selected_transaction = None
    for transaction in transactions.values():
        if transaction.transaction_id == transaction_id and transaction.username == username:
            selected_transaction = transaction
            break
    if selected_transaction:
        # Delete the transaction
        cur = con.cursor()
        cur.execute("DELETE FROM transactions WHERE transaction_id = ?",(transaction_id,))
        con.commit()
        cur.close()
        return True
    else:
        print(f"\nTransaction '{transaction_id}' not found for user '{username}'.")
        print(f"Available transactions for {username}: {[t.transaction_id for t in transactions.values() if t.username == username]}")
        return False

def user_exist(con,login):
    # SQL query to determine if user exists
    cur = con.cursor()
    res = cur.execute("SELECT username FROM users")
    returned_users = res.fetchall()
    cur.close()
    for user in returned_users:
        if login == user[0]:
            return True  
    return False  

def refresh_user_data(con,user,username):
    cur = con.cursor()
    #reinstantiate vaults
    vaults,vault_ids = re_vaults(con,username,user)
    #reinstantiate pots
    pots,pot_ids = re_pots(con,vaults,vault_ids,user)
    #reinstantiate transactions
    res = cur.execute("SELECT * FROM transactions")
    transaction_exists = bool(res.fetchall())
    transactions, transaction_ids = re_transactions(con,pots,vaults,pot_ids,user) if transaction_exists else ({}, [])
    #reinstantiate balances
    balances = re_balances(con,username)
    #reinstantiate previous balances
    previous_balances = previous_balances_variable(con,username)
    
    cur.close()
    return vaults,vault_ids,pots,pot_ids,transactions,transaction_ids,balances,previous_balances

def refresh_pot_vault_values(pots,vaults):
    for pot in pots.values():
        pot.pot_value()
        for vault in vaults.values():
            vault.vault_value()
    return pots,vaults

def previous_balances_variable(con,username):
    cur = con.cursor()
    # Searcb the database for balance_id one less than max
    res = cur.execute("""
        SELECT * FROM balances
        WHERE username = ?
        ORDER BY balance_id DESC
        LIMIT 1 OFFSET 1
    """, (username,))

    returned_balances = res.fetchall()
    if not returned_balances:
        raise ValueError("No balances found for this user.")

    # Unpack the list and create variables
    (balance_id,username, date, bank_currency, cash_currency, bank_balance, cash_balance, active_pot) = returned_balances[0]

    # Create previous_balances instance
    previous_balances = Balances(balance_id=balance_id,username=username,date=date,bank_currency=bank_currency,cash_currency=cash_currency,bank_balance=bank_balance,cash_balance=cash_balance,active_pot=active_pot)
    cur.close()
    return previous_balances

def build_forecast(pots):
    """Build forecast data using planned daily expenditures"""
    total_budget = sum(pot.amount for pot in pots.values() if pot)
    forecast_data = []
    
    # Get overall date range
    all_start_dates = [pot.start_date for pot in pots.values() if pot]
    all_end_dates = [pot.end_date for pot in pots.values() if pot]
    
    if not all_start_dates:
        return forecast_data
    
    start_date = min(all_start_dates)
    end_date = max(all_end_dates)
    
    # Create a dictionary to track remaining budget for each pot
    pot_budgets = {}
    for pot_id, pot in pots.items():
        if pot:
            pot_budgets[pot_id] = pot.amount
    
    current_date = start_date
    
    while current_date <= end_date:
        daily_total_spend = 0.0
        
        # Calculate total daily spend from all active pots on this date
        for pot_id, pot in pots.items():
            if pot and pot.start_date <= current_date <= pot.end_date:
                # Only spend from pots that still have budget
                if pot_budgets[pot_id] > 0:
                    daily_spend = min(pot.daily_expenditure, pot_budgets[pot_id])
                    daily_total_spend += daily_spend
                    pot_budgets[pot_id] -= daily_spend
        
        forecast_data.append([current_date, total_budget])
        total_budget -= daily_total_spend
        current_date += timedelta(days=1)
    
    return forecast_data

def build_balances(pots, transactions):
    """Build actual balances data using transaction history"""
    total_budget = pot_total_budget(pots)
    balances_data = []
    
    # Get today's date
    today = datetime.date.today()
    
    # Get all unique dates across all pot periods AND transaction dates
    all_dates = set()
    
    # Add all pot period dates
    for pot in pots.values():
        if pot:
            current_date = pot.start_date
            while current_date <= pot.end_date:
                all_dates.add(current_date)
                current_date += timedelta(days=1)
    
    # Add all transaction dates
    for transaction in transactions.values():
        if isinstance(transaction, Transaction):
            all_dates.add(transaction.date)
        
    if not all_dates:
        return balances_data
    
    # Sort dates chronologically
    sorted_dates = sorted(all_dates)
    
    # Group transactions by date
    daily_transactions = {}
    for transaction in transactions.values():
        if not isinstance(transaction, Transaction):
            continue
        if transaction.balance_transaction == 1:
            continue
            
        tx_date = transaction.date
        tx_amount = transaction.amount
        
        if transaction.type == "out":
            amount = -abs(tx_amount)
        else:  # "in"
            amount = abs(tx_amount)
        
        if tx_date not in daily_transactions:
            daily_transactions[tx_date] = 0.0
        daily_transactions[tx_date] += amount
    
    # Build timeline
    current_balance = total_budget
    
    for date in sorted_dates:
        # Stop at today
        if date > today:
            break
            
        # Apply transactions for this date
        daily_net = daily_transactions.get(date, 0.0)
        current_balance += daily_net
        
        # Add entry for this date
        entry = [date, current_balance] 
        balances_data.append(entry)
    
    return balances_data

def pot_forecast(con, pots, pot_name, balances, transactions, dynamic_width=True):
    # Build Forecast Data Frame
    forecast_data = build_forecast(pots)
    # Shift green line to the left
    forecast_df_original = pd.DataFrame(forecast_data, columns=["Date", "Forecast Balance"])
    forecast_df = pd.DataFrame(forecast_data, columns=["Date", "Forecast Balance"])
    forecast_df["Date"] = pd.to_datetime(forecast_df["Date"]) - pd.Timedelta(days=1)

    # Build Actual Balances Data
    balances_data = build_balances(pots, transactions)
    balances_df = pd.DataFrame(balances_data, columns=["Date", "Actual Balance"])

    # Plot Graph
    sns.set_theme(style="darkgrid", palette="Blues_d")
    plt.rcParams.update({
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 12,
        "axes.labelweight": "bold",
        "legend.frameon": True,
        "legend.framealpha": 0.9,
        "legend.fancybox": True,
        "legend.loc": "upper center",
        "font.size": 11,
    })

    fig, ax = plt.subplots(figsize=(10, 6))

    # Calculate y_max safely
    y_max_values = []
    
    if not forecast_df.empty and not forecast_df["Forecast Balance"].isna().all():
        y_max_values.append(forecast_df["Forecast Balance"].max())
    
    if not balances_df.empty and not balances_df["Actual Balance"].isna().all():
        y_max_values.append(balances_df["Actual Balance"].max())
    
    # Set default y_max if no valid data
    if y_max_values:
        y_max = max(y_max_values)
    else:
        y_max = 1000  # Default value when no data
    
    # Forecast line (green) - only if we have forecast data
    if not forecast_df.empty and not forecast_df["Forecast Balance"].isna().all():
        ax.plot(forecast_df["Date"], forecast_df["Forecast Balance"],
                color="#61b27eff", linewidth=2.5, label="Forecast Balance")

    # Actual line (orange) - only if we have actual data
    if not balances_df.empty and not balances_df["Actual Balance"].isna().all():
        ax.plot(balances_df["Date"], balances_df["Actual Balance"],
                color="#fdb43fff", linewidth=2.5, linestyle="--", label="Actual Balance")

        # Highlight last actual point with time-based positioning
        last_row = balances_df.iloc[-1]
        current_time = datetime.datetime.now().time()
        
        # Discrete positions based on time of day
        if current_time.hour < 12:
            time_label = "Morning"
            x_offset = 0.25  # 25% through the day
        elif current_time.hour < 18:
            time_label = "Afternoon" 
            x_offset = 0.5   # 50% through the day
        else:
            time_label = "Evening"
            x_offset = 0.75  # 75% through the day
        
        dot_date = last_row["Date"] + datetime.timedelta(days=x_offset)
        
        ax.scatter(dot_date, last_row["Actual Balance"],
                   color="#fdb43fff", s=100, edgecolor="white",
                   linewidth=1.5, zorder=5, label=f"Current Balance ({time_label})")

    # Add pot name labels only if we have pots
    valid_pots = [pot for pot in pots.values() if pot is not None]
    if valid_pots and y_max > 0:
        for pot in valid_pots:
            # Add vertical line at pot start date
            ax.axvline(x=pot.start_date, color='gray', linestyle=':', alpha=0.7, linewidth=1)
            
            # Add pot name label to the RIGHT of the line
            date_delta = pot.end_date - pot.start_date
            label_date = pot.start_date + date_delta / 2
            ax.text(label_date, y_max * 1.02, pot.pot_name, 
                   ha='left', va='bottom', fontsize=10, fontweight='bold',  
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))

    # Axes & formatting with safe limits
    ax.set_xlabel("Date")
    ax.set_ylabel("Balance ($)")
    
    # Set safe y-axis limits
    if y_max > 0:
        ax.set_ylim(bottom=0, top=y_max * 1.1)
    else:
        ax.set_ylim(bottom=0, top=1000)  # Default range
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    plt.gcf().autofmt_xdate()
    ax.legend(title="Key", bbox_to_anchor=(0.5, -0.2), loc="upper center", ncol=2)
    sns.despine(left=True, bottom=True)
    plt.tight_layout()

    return fig

def pot_dict(pots):
    pot_dict = {}
    for pot in pots.values():
        pot_dict[f"{pot.pot_id}"] = pot.pot_name
    return pot_dict

def active_pot_dict(pots):
    active_pot_dict = {}
    for pot in pots.values():
        if pot.vault.vault_name == "Daily expenses":
            active_pot_dict[f"{pot.pot_id}"] = pot.pot_name
    return active_pot_dict

def undo_last_balance(con, username, balances):
    cur = con.cursor()

    # Get the two most recent balances for this user
    cur.execute("""
        SELECT balance_id, date
        FROM balances
        WHERE username = ?
        ORDER BY date DESC
        LIMIT 2
    """, (username,))
    rows = cur.fetchall()

    if len(rows) < 2:
        cur.close()
        return False

    latest_id, latest_ts = rows[0]
    _, prev_ts = rows[1]

    # Delete the latest balance entry
    cur.execute("DELETE FROM balances WHERE balance_id = ?", (latest_id,))

    # Delete any auto-transactions created after the previous balance timestamp
    cur.execute("""
        DELETE FROM transactions
        WHERE username = ?
        AND transaction_name LIKE 'auto_transaction_%'
        AND date > ?
    """, (username, prev_ts))

    # Get the desired amounts for objects
    cur.execute("""
        SELECT bank_balance, cash_balance
        FROM balances
        WHERE username = ?
        ORDER BY date DESC
        LIMIT 1
    """, (username,))
    rows = cur.fetchall()

    bank_balance, cash_balance = rows[0]
    
    # Update objects
    balances.update_bank_balance(bank_balance)
    balances.update_cash_balance(cash_balance)

    con.commit()
    cur.close()

    return True

def currency_convert(base_currency, conversion_currency, conversion_amount):
    # Get currency conversion list with bank_currency as the base
        conversion_list = requests.get(f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{base_currency.lower()}.json")
        formatted_conversion_list = conversion_list.json()
        conversion_value = formatted_conversion_list[base_currency.lower()][conversion_currency.lower()]

        # Calculate combined_balance
        converted_currency = conversion_amount / conversion_value
        
        return converted_currency

def financial_status(pots):
    today = pd.Timestamp(datetime.datetime.today().date())  # Convert to pd timestamp
    pot_total_budget = 0
    pot_total_balance = 0
    colors = ["green", "red", "black"]
    status = []    
    
    for pot in pots.values():
        tomorrow_forecast = None  #reset each iteration
        # --- Pot balance ---
        pot_balance = pot.pot_value()
        pot_total_balance += pot_balance
        
        # --- Prepare forecast data ---
        forecast_data = {}
        start_date = pd.Timestamp(pot.start_date)
        end_date = pd.Timestamp(pot.end_date)
        current_date = start_date
        amount = pot.amount
        
        while current_date < end_date:
            forecast_data[current_date] = amount
            current_date += timedelta(days=1)
            amount -= pot.daily_expenditure

        # Create DataFrame of forecast
        df = pd.DataFrame(list(forecast_data.items()), columns=["Date", "Forecast Balance"])

        # --- Determine which forecast value to use for today ---
        if today < start_date:
            # Pot hasn’t started yet — full budget still available
            pot_total_budget += pot.amount

        elif today > end_date:
            # Pot is fully completed — nothing left
            pot_total_budget += 0

        else:
            tomorrow = today + pd.Timedelta(days=1)
            if tomorrow > end_date:
                pot_total_budget += 0
            else:
                tomorrow_forecast = df[df["Date"] == tomorrow]["Forecast Balance"]
                if not tomorrow_forecast.empty:
                    pot_total_budget += tomorrow_forecast.values[0]
                else:
                    df["Date_Diff"] = (df["Date"] - tomorrow).abs()
                    closest_row = df.loc[df["Date_Diff"].idxmin()]
                    pot_total_budget += closest_row["Forecast Balance"]
    
    # --- Calculate status amount ---
    status_amount = pot_total_budget - pot_total_balance
    
    # --- Determine status color ---
    if pot_total_balance == pot_total_budget:
        status_color = colors[2]  # black  
    elif pot_total_balance >= pot_total_budget:
        status_color = colors[0]  # green    
    else:
        status_color = colors[1]  # red

    status_amount = abs(round(status_amount))
    
    status.append(status_color)
    status.append(status_amount)
    
    return status

def generate_forecast_bmp(status):
    # status is a tuple like ("green", "500")
    color = status[0]
    value = status[1]

    # --- Image settings ---
    width, height = 1000, 50
    background = "white"

    # Create blank image
    img = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(img)

    # Load fonts (fallback to default if not found)
    title_font = ImageFont.load_default(28)
    text_font = ImageFont.load_default(28)

    # --- Text content ---
    title_text = "Active Pot Spending Forecast "
    message_text = f"${value} in the {color}"
    text_content = title_text + message_text

    # --- Measure text sizes (new method) ---
    text_bbox = draw.textbbox((0, 0), text_content, font=title_font)

    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]

    # --- Centered positioning ---
    text_x = ((width - text_w) / 2) + 30
    text_y = (height / 2) - 10

    # --- Draw text ---
    draw.text((text_x, text_y), title_text, fill="black", font=title_font)
    draw.text((text_x + 400, text_y), message_text, fill=color, font=text_font)

    # --- Output as BMP (for Streamlit) ---
    output = io.BytesIO()
    img.save(output, format="BMP")
    output.seek(0)

    return output

def generate_summary_bmp():
    # --- Image settings ---
    width, height = 1000, 50
    background = "white"

    # Create blank image
    img = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(img)

    # Load fonts (fallback to default if not found)
    title_font = ImageFont.load_default(28)

    # --- Text content ---
    text_content = "Summary of Pot Balances"

    # --- Measure text sizes (new method) ---
    text_bbox = draw.textbbox((0, 0), text_content, font=title_font)

    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]

    # --- Centered positioning ---
    text_x = ((width - text_w) / 2) + 33
    text_y = (height / 2) - 10

    # --- Draw text ---
    draw.text((text_x, text_y), text_content, fill="black", font=title_font)
    
    # --- Output as BMP (for Streamlit) ---
    output = io.BytesIO()
    img.save(output, format="BMP")
    output.seek(0)

    return output

def pot_total_budget(pots):
    pot_total_budget = 0
    for pot in pots.values():
        pot_total_budget += pot.amount
    return pot_total_budget