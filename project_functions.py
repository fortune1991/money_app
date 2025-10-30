import datetime,os,sqlite3,math
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st
from datetime import timedelta
from project_classes import User,Vault,Pot,Transaction,Balances
from streamlit_option_menu import option_menu
from tabulate import tabulate
from time import sleep

import warnings
warnings.filterwarnings("ignore",message="The default datetime adapter is deprecated",category=DeprecationWarning)
    
def auto_transaction(con,x,pots,vaults,user,username,balances,previous_balances,active_pot):
    if active_pot == None:
        return None
    manual_transaction = 0
    date = datetime.datetime.today()
    # Count existing transactions
    start_transaction = x + 1
    if start_transaction == None:
        start_transaction = 1
    transaction_name = f"auto_transaction_{active_pot}_{start_transaction}" 

    # Collect transaction type
    while True:
        if balances.combined_balance(balances) == previous_balances.combined_balance(previous_balances):
            return
        elif balances.combined_balance(balances) < previous_balances.combined_balance(previous_balances):
            transaction_type = "out"
            break
        else:
            transaction_type = "in"
            break

    # Calculate transaction amount
    amount = (balances.combined_balance(balances) - previous_balances.combined_balance(previous_balances)) 

    # Find the pot using a simple loop
    selected_pot = None
    selected_vault = None
    for pot in pots.values():
        if pot.pot_name == active_pot and pot.username == username: 
            selected_pot = pot
            selected_vault = vaults.get(f"vault_{pot.vault_id}")
            break

    if selected_pot:
        try:
            #Input all information into the Class
            transaction = Transaction(transaction_id=start_transaction,transaction_name=transaction_name,date=date,pot=selected_pot,vault=selected_vault,manual_transaction=manual_transaction,type=transaction_type,amount=amount,user=user)
            transaction_data = [(start_transaction,transaction_name,date,selected_pot.pot_id,selected_vault.vault_id,manual_transaction,transaction_type,amount,username)]
            if transaction:
                # Save transaction to database
                cur = con.cursor()
                cur.executemany("INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?,?)",transaction_data)
                con.commit()
                cur.close()
            return transaction

        except ValueError as e:
            print_slow(f"Error: {e}")
            
        except Exception as e:  
            print_slow(f"An unexpected error occurred: {e}")
    else:
        print_slow(f"pot '{active_pot}' not found. Please enter a valid pot name.")

def submit_transaction(con,x,pots,vaults,user,username):
    print_slow_nospace("\nExcellent. Now, let me help you create a new transaction.")
    print_slow("\nPlease provide a name reference for this transaction: ")
    transaction_name = input()
    manual_transaction = 1
    today = datetime.datetime.today()
    # Count existing transactions
    start_transaction = x + 1
    if start_transaction == None:
        start_transaction = 1
    print_slow("\nWhat pot should this pot be assigned to?: ")
    pot_input = input()
    print_slow("\nExcellent. Now we'll define when the transaction took place. Please note, all date input values must be in the format DD/MM/YY")
    while True:
        date = collect_date("Date of transaction: ")
        if date <= today:
            break
        else:
            print_slow("\nTransactions cannot be submitted for the future. Please try again")
    # Collect transaction type
    while True:
        types = ["in","out"]
        print_slow('\nPlease define the type of transaction. "in" or "out": ')
        transaction_type = input()
        if transaction_type not in types:
            print_slow("\nincorrect transaction reference")
        else:
            break
    # Collect transaction amount
    print_slow("\nWhat is the transaction amount?: ")
    while True:
        amount = int_validator()
        if amount > 0:
            break
        else:
            print_slow("\namount must be greater than 0")

    if transaction_type == "out":
        amount = amount * -1
    else:
        pass

    # Find the pot using a simple loop
    selected_pot = None
    selected_vault = None
    for pot in pots.values():
        if pot.pot_name == pot_input and pot.username == username: 
            selected_pot = pot
            selected_vault = vaults.get(f"vault_{pot.vault_id}")
            break

    if selected_pot:
        try:
            #Input all information into the Class
            transaction = Transaction(transaction_id=start_transaction,transaction_name=transaction_name,date=date,pot=selected_pot,vault=selected_vault,manual_transaction=manual_transaction,type=transaction_type,amount=amount,user=user)
            transaction_data = [(start_transaction,transaction_name,date,selected_pot.pot_id,selected_vault.vault_id,manual_transaction,transaction_type,amount,username)]
            if transaction:
                print_slow_nospace("\nThanks, your transaction has been created succesfully")
                # Save transaction to database
                cur = con.cursor()
                cur.executemany("INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?,?)",transaction_data)
                con.commit()
                cur.close()
            return transaction

        except ValueError as e:
            print_slow(f"Error: {e}")
            
        except Exception as e:  
            print_slow(f"An unexpected error occurred: {e}")
    else:
        print_slow(f"pot '{pot_input}' not found. Please enter a valid pot name.")

def print_slow(txt):
    for x in txt: 
        print(x,end='',flush=True)
        sleep(0) #0.025 for slow text
    print()
    print()

def print_slow_nospace(txt):
    for x in txt: 
        print(x,end='',flush=True)
        sleep(0) #0.025 for slow text
    print()

def int_validator():
    while True:
        try:
            value = int(input())
            break
        except ValueError:
            print_slow("\nInvalid input. Please enter a valid integer: ")
    return value

def collect_date(message):
    while True:
        try:
            print_slow(message) 
            date_input = input().strip()
            date = datetime.datetime.strptime(date_input,"%d/%m/%y")
            return date 
        except ValueError as err:
            print_slow_nospace(f"\nInvalid date: {err}. Please use DD/MM/YY format\n")

def convert_date(date_input):
    """Convert string from DB to datetime, ignoring microseconds."""
    import datetime

    if isinstance(date_input, datetime.datetime):
        return date_input.replace(microsecond=0)  # remove microseconds

    if not date_input:
        return datetime.datetime.today().replace(microsecond=0)

    if isinstance(date_input, str):
        # truncate microseconds if present
        if "." in date_input:
            date_input = date_input.split(".")[0]
        try:
            return datetime.datetime.strptime(date_input, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            print(f"Warning: couldn't parse date_input={date_input!r}")
            return datetime.datetime.today().replace(microsecond=0)
    
    return datetime.datetime.today().replace(microsecond=0)
        
def summary(vaults, pots, dynamic_width=True):
    # Prepare data
    data = []
    for i in vaults:
        vault = vaults[i]
        vault_amount = vault.initial_vault_value()
        for j in pots:
            if pots[j].vault == vault:
                pot_value = pots[j].pot_value()
                data.append(['Vault Name: ' + vault.vault_name + '\n' + 'Initial Amount: $' + f'{vault_amount}', pots[j].pot_name + f'\n${pot_value}', 'Initial Amount', pots[j].amount])
                data.append(['Vault Name: ' + vault.vault_name + '\n' + 'Initial Amount: $' + f'{vault_amount}', pots[j].pot_name + f'\n${pot_value}', 'Remaining Balance', pot_value])

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
    if dynamic_width:
        fig_width = min(max(6, len(vaults_unique) * len(pots_unique) * 1.5), 16)
    else:
        fig_width = 8
    fig_height = 6
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    colors = {
        'Initial Amount': '#fdb43fff',
        'Remaining Balance': '#61b27eff',
    }

    # Bar width and vault spacing
    bar_width = max(0.15, 0.6 / num_pots)
    vault_spacing = 0.1
    vault_positions = np.arange(len(vaults_unique)) * vault_spacing

    # Plot bars and track vault centers
    vault_centers = []
    for i, vault in enumerate(vaults_unique):
        vault_data = pivot_df[pivot_df['Vault'] == vault]
        x_positions = []

        for j, pot in enumerate(pots_unique):
            row = vault_data[vault_data['Pot'] == pot]
            if not row.empty:
                initial = row['Initial Amount'].values[0]
                remaining = row['Remaining Balance'].values[0]

                # Center bars per vault
                x = vault_positions[i] + (j - (len(vault_data)-1)/2) * bar_width
                x_positions.append(x)

                ax.bar(x, initial, width=bar_width, color=colors['Initial Amount'],
                       edgecolor='white', alpha=0.8,
                       label='Initial Amount' if i == 0 and j == 0 else "")
                ax.bar(x, remaining, width=bar_width, color=colors['Remaining Balance'],
                       edgecolor='white', alpha=0.9,
                       label='Remaining Balance' if i == 0 and j == 0 else "")

                # Label the pot
                ax.text(x, remaining / 2, pot, ha='center', va='center',
                        color='white', fontsize=9, fontweight='bold')

        # Compute center for vault label
        vault_centers.append(np.mean(x_positions) if x_positions else vault_positions[i])

    # Vault labels centered
    ax.set_xticks(vault_centers)
    ax.set_xticklabels(vaults_unique, fontsize=11, fontweight='bold')

    ax.set_ylabel('Amount ($)', fontsize=12, fontweight='bold')
    ax.set_title('Summary of Pot Balances', fontsize=14, fontweight='bold', pad=20)

    # Legend below chart
    ax.legend(
        title='Key',
        bbox_to_anchor=(0.5, -0.2),
        loc='upper center',
        ncol=2,
    )

    sns.despine(left=True, bottom=True)
    plt.tight_layout()

    return fig  # Return fig for Streamlit (use st.pyplot(fig, use_container_width=True))

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
        print_slow("Now firstly, what is your name?: ")
        username = input()
        user = User(username)

    cur.execute("INSERT INTO users VALUES(?)",(username,))
    con.commit()
    cur.close()
    return user

def create_pot(con,x,vaults,user,username):
    print_slow("\nWhat vault will this pot be assigned to? ")
    pot_vault = input()
    selected_vault = None
    for vault in vaults.values():
        if vault.vault_name == pot_vault and vault.username == username:
            selected_vault = vault
    if selected_vault:
        cur = con.cursor()
        print_slow("\nWhat is your preferred name for the pot?: ")
        pot_name = input()
        pot_id = x + 1
        print_slow("\nWhat is the amount of money in the pot?: ")
        while True:
            amount = int_validator()
            if amount > 0:
                break
            else:
                print_slow("\namount must be greater than 0")
        # Collect start date data and create date object
        print_slow("\nExcellent. Now we'll define when the pot will be in use. Please note, all date input values must be in the format DD/MM/YY")
        start_date = collect_date("What is the start date that this pot will be active?: ")
        # Collect end date data and create date object
        end_date = collect_date("\nWhat is the end date that this pot will be active?: ") 

        #Input all information into the Class
        try:
            pot = Pot(pot_id=pot_id,pot_name=pot_name,vault=selected_vault,amount=amount,user=user,start_date=start_date,end_date=end_date)
            if pot:
                print_slow_nospace("\nThanks, your pot has been created succesfully")
                # save pot to database
                pots_data = []
                pots_data.append((pot.pot_id,pot.pot_name,pot.vault_id,pot.amount,username,pot.start_date,pot.end_date,pot.date_delta,pot.daily_expenditure))
                cur.executemany("INSERT INTO pots VALUES(?,?,?,?,?,?,?,?,?)",pots_data)
                con.commit()
                cur.close()
            else:
                print_slow("\nERROR: pot not created succesfully")
            
            return pot
        
        except ValueError as e:  
            return print_slow(f"Error: {e}, Please try again")
            
        except Exception as e:  
            return print_slow(f"An unexpected error occurred: {e}, Please try again")

    else:
        return print_slow_nospace(f"\nVault '{pot_vault}' not found. Please enter a valid vault name.")
        
def create_vault(con,x,user,username):
    cur = con.cursor()
    print_slow("\nWhat is your preferred name for the vault?: ")
    vault_name = input()
    vault_id = x + 1    
    #Input all information into the Class
    vault = Vault(vault_id=vault_id,vault_name=vault_name,user=user)
    if vault:
        print_slow("\nThanks, your vault has been created succesfully")
        # save vault to database
        vaults_data = []
        vaults_data.append((vault.vault_id,vault.vault_name,username))
        cur.executemany("INSERT INTO vaults VALUES(?,?,?)",vaults_data)
        con.commit()
        cur.close()
    else:
        print_slow("ERROR: vault not created succesfully")
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
    print_slow(f"\nHi {username}, let me help you create some vaults. How many do you want to create?: ")
    no_vaults = 2
    vaults = {}
    try:
        for x in range(no_vaults):
            vaults["vault_{0}".format(start_vault+x)] = create_vault(con,(start_vault+x),user,username)
    except ValueError as e:  
        print_slow(f"\nError: {e}")
    except Exception as e:  
        print_slow(f"\nAn unexpected error occurred: {e}")

    # Create Pot objects with valid data
    print_slow("Now, let me help you create some pots. How many do you want to create?: ")
    no_pots = int_validator()
    pots = {}
    try:
        for x in range(no_pots):
            create_pot(con,(x+start_pot),vaults,user,username)
                            
    except ValueError as e:  
        print_slow(f"Error: {e}")

    except Exception as e:  
        print_slow(f"An unexpected error occurred: {e}")

    # Create Balances object
    print_slow("\nNow, let me help you submit your existing bank and cash balances")
    balances = create_balance(con,username)

    #refresh user data
    vaults, vault_ids,pots,pot_ids,transactions,transaction_ids,balances = refresh_user_data(con,user,username)
    #refresh pot/vault values
    pots,vaults = refresh_pot_vault_values(pots,vaults)

    # Summary of the vaults and pots values
    print_slow("\nSee below list of vaults and their summed values")
    summary(vaults,pots)
    return user,vaults, vault_ids,pots,pot_ids,transactions,transaction_ids,balances

def create_balance(con,username):
    currencies = ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "THB", "SGD", "HKD", "CNY", "KRW", "INR", "IDR", "MYR", "PHP", "VND", "ZAR", "AED", "MXN", "TRY", "SEK", "NOK", "DKK"]
    
    # bank_currency
    while True:
        print_slow("What is your banks currency?:")
        bank_currency = input()
        if bank_currency in currencies:
            break
        print_slow("\nCurrency not found")

    # bank_balance
    while True:
        print_slow("\nWhat is your bank balance?:")
        try:
            bank_balance = float(input())
            break
        except ValueError:
            print_slow("Invalid balance submitted. Please try again")

    # cash_currency
    while True:
        print_slow("\nWhat is your cash currency?:")
        cash_currency = input()
        if cash_currency in currencies:
            break
        print_slow("\nCurrency not found")

    # cash_balance
    while True:
        print_slow("\nWhat is your cash balance?:")
        try:
            cash_balance = float(input())
            break
        except ValueError:
            print_slow("Invalid balance submitted. Number must be to two decimal places. Please try again")

    # Create list of variables
    balances_data = []

    balances_data.append(username)
    balances_data.append(bank_currency)
    balances_data.append(cash_currency)
    balances_data.append(bank_balance)
    balances_data.append(cash_balance)

    # Save balances to database
    cur = con.cursor()
    cur.execute("INSERT INTO balances VALUES(?,?,?,?,?)",balances_data)
    con.commit()
    cur.close()

    # Create transaction instance
    balances = Balances(username=username,bank_currency=bank_currency,cash_currency=cash_currency,bank_balance=bank_balance,cash_balance=cash_balance)

    return balances
    
def balance_update(con,balances,previous_balances,bank_balance,cash_balance):
    # Update Object
    balances.update_bank_balance(bank_balance)
    balances.update_cash_balance(cash_balance)

    # Create list of variables
    balances_data = []

    username = balances.username
    balances_data.append(username)

    bank_currency = balances.bank_currency
    balances_data.append(bank_currency)

    cash_currency = balances.cash_currency
    balances_data.append(cash_currency)

    bank_balance = balances.bank_balance
    balances_data.append(bank_balance)

    cash_balance = balances.cash_balance
    balances_data.append(cash_balance)

    # Save balances to database
    cur = con.cursor()
    cur.execute("INSERT OR REPLACE INTO balances VALUES(?,?,?,?,?)",balances_data)
    con.commit()
    cur.close()
    
    return balances,previous_balances

def balance_summary(balances):
    table = []
    row = [balances.bank_balance,balances.bank_currency, balances.cash_balance, balances.cash_currency, balances.combined_balance(balances), balances.bank_currency]
    table.append(row)
    print_slow_nospace("\n\033[1;31mBank & Cash Balances\033[0m")
    print(f"\n{tabulate(table,headers=["Bank Balance","Currency","Cash Balance","Local Currency", "Combined Balance", "Currency"],tablefmt="heavy_grid")}\n")
    return

def check_balances(con,balances,previous_balances):
    balance_summary(balances)
    print_slow("Is this accurate?")
    while True:
        balance_check = input("Enter Y or N: ").strip().upper()
        if balance_check in ("Y", "N"):
            break
        else:
            print("Invalid input. Please enter Y or N.")

    if balance_check == "N":
        #Preserve old balances object
        previous_balances = previous_balances_variable(balances)
        
        # Bank
        print_slow("\nOK. Please enter your current bank balance:")
        try:
            bank_balance = float(input())
        except ValueError:
            print_slow("That's not a valid balance. Please try again.")

        # Cash
        print_slow("\nOK. Please enter your current cash balance:")
        try:
            cash_balance = float(input())
        except ValueError:
            print_slow("That's not a valid balance. Please try again.")
        
        balances,previous_balances = balance_update(con,balances,previous_balances,bank_balance,cash_balance)
        print_slow_nospace("\nBalance updated")

        return balances,previous_balances
    
    return balances,previous_balances

def instructions():
    return """In this program, your savings are organized into two categories: vaults and pots.

- A vault is a collection of Pots
- A pot represents an individual budget within a Vault

For example, you might create a 'Travelling' vault
to manage your holiday expenses. This vault could contain multiple pots, each
representing a budget for a different destination. 

Once you've set up your vaults and pots, the program will track your bank and cash balances via regular updates.
Using this it automatically infers your recent expenditure and you can also enter transactions manually. 
From this data, a "Forecasting" graph can be created in the summary section to see (based on today's date) if your 
spending is on track with the pot's budget.


After set-up or login, the programme enters an infinite loop where you can choose from the following options:

1. "New" to submit a new item (profile, vaults, pots, transactions),
2. "Update" to manually update your balances,
3. "Summary" to get either a balance report or transactions summary,
4. "Delete" to remove an item,
6. "Instructions" to get further information on how to use Money Pots,
6. "Exit" to terminate the programme

We hope you enjoy using Money Pots!"""

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
                type = (transaction[6])
                amount = int(transaction[7])
                pot = pots[f"pot_{transaction[3]}"] # Dictionary key format is "Pot_1: Object"
                vault = vaults[f"vault_{transaction[4]}"] # Dictionary key format is "Vault_1: Object"
                # Create transaction instance
                transaction = Transaction(transaction_id=transaction_id,transaction_name=transaction_name,date=date,pot=pot,vault=vault,manual_transaction=manual_transaction,type=type,amount=amount,user=user)
                # Add instance to transactions object dictionary
                transactions[f"transaction_{transaction.transaction_id}"] = transaction
                # Append transaction_id to list
                transaction_ids.append(transaction_id)

    cur.close()
    return transactions,transaction_ids

def re_balances(con,username):
    cur = con.cursor()
    # Searcb the database for balances related to username
    res = cur.execute("SELECT * FROM balances WHERE username = ?",(username,))
    returned_balances = res.fetchall()
    if not returned_balances:
        raise ValueError("No balances found for this user.")

    # Unpack the list and create variables
    (username, bank_currency, cash_currency, bank_balance, cash_balance) = returned_balances[0]

    # Create transaction instance
    balances = Balances(username=username,bank_currency=bank_currency,cash_currency=cash_currency,bank_balance=bank_balance,cash_balance=cash_balance)
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
        cur.execute("DELETE FROM transactions WHERE username = ?",(username,))
        cur.execute("DELETE FROM pots WHERE username = ?",(username,))
        cur.execute("DELETE FROM vaults WHERE username = ?",(username,))
        # Finally,delete the user
        cur.execute("DELETE FROM users WHERE username = ?",(username,))
        con.commit()
        cur.close()
        print_slow_nospace("\nProfile deleted successfully.")

    except sqlite3.Error as e:
        print_slow(f"\nError deleting profile: {e}")

def del_vault(con,user,vaults,username):
    vault_name = input("\nEnter the name of the Vault you want to delete: \n\n").strip()
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
        print_slow_nospace("\nVault deleted succesfully")
        return True

    else:
        print_slow(f"\nVault '{vault_name}' not found for user '{username}'.")
        print_slow_nospace(f"Available vaults for {username}: {[v.vault_name for v in vaults.values() if v.username == username]}\n")
        return False

def del_pot(con,user,pots,username):
    pot_name = input("\nEnter the name of the Pot you want to delete: \n\n").strip()
    # Search for the pot that matches both the name and the username
    selected_pot = None
    for pot in pots.values():
        if pot.pot_name == pot_name and pot.username == username:
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
        print_slow_nospace("\nPot deleted succesfully")
        return True

    else:
        print_slow(f"\nPot '{pot_name}' not found for user '{username}'.")
        print_slow_nospace(f"Available pots for {username}: {[p.pot_name for p in pots.values() if p.username == username]}")
        return False

def del_transaction(con,user,transactions,username):
    try:
        transaction_id = int(input("\nEnter the transaction_id that you want to delete: \n\n").strip())
    except ValueError:
        print_slow("\nInvalid transaction ID. Must be a number.")
        return False
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
        print_slow_nospace("\nTransaction deleted succesfully")
        return True
    else:
        print_slow(f"\nTransaction '{transaction_id}' not found for user '{username}'.")
        print_slow_nospace(f"Available transactions for {username}: {[t.transaction_id for t in transactions.values() if t.username == username]}")
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
    
    cur.close()
    return vaults,vault_ids,pots,pot_ids,transactions,transaction_ids,balances

def refresh_pot_vault_values(pots,vaults):
    for pot in pots.values():
        pot.pot_value()
        for vault in vaults.values():
            vault.vault_value()
    return pots,vaults

def previous_balances_variable(balances):
    previous_balances = Balances(
    username=balances.username,
    bank_currency=balances.bank_currency,
    cash_currency=balances.cash_currency,
    bank_balance=balances.bank_balance,
    cash_balance=balances.cash_balance
    )
    return previous_balances

def active_pot_confirmation(pots):
    while True:
        print_slow("\nPlease confirm the Pot you are currently using to withdraw funds")
        active_pot = input()
        if active_pot == "None":
            active_pot = None
            print_slow_nospace(f"\nThanks, {active_pot} has been confirmed as your active pot")
            return active_pot
        pot_names = []
        for pot in pots.values():
            pot_names.append(pot.pot_name)
        if active_pot in pot_names:
            break
        else:
            print_slow_nospace("\nPot name not found")

    print_slow_nospace(f"\nThanks, {active_pot} has been confirmed as your active pot")
    return active_pot

def pot_forecast(pots, pot_name, dynamic_width=True):
    # Assign pot to a variable
    pot = next((p for p in pots.values() if p.pot_name == pot_name), None)
    if pot is None:
        raise KeyError(f"No pot found with name '{pot_name}'")
    # Prepare forecast data
    forecast_data = {}
    start_date = pot.start_date
    end_date = pot.end_date
    date = start_date
    amount = pot.amount
    while date <= end_date:
        forecast_data[date] = amount
        date += timedelta(days=1)
        amount -= pot.daily_expenditure

    df = pd.DataFrame(list(forecast_data.items()), columns=["Date", "Forecast Balance"])
    
    # Prepare actual balance data
    actual_balance = pot.pot_value()
    actual_date = datetime.datetime.today()

    # --- Seaborn theme (match existing) ---
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

    # --- Create figure ---
    fig, ax = plt.subplots(figsize=(8, 6))

    # --- Plot forecast line ---
    ax.plot(df["Date"], df["Forecast Balance"], color="#61b27eff",
            linewidth=2.5, label="Forecast Balance")

    # --- Plot actual balance point ---
    ax.scatter(actual_date, actual_balance, color="#fdb43fff", s=100,
               edgecolor="white", linewidth=1.5, zorder=5, label="Actual Balance")

    # --- Style axes ---
    ax.set_title(f"Forecasted Pot Balance: {pot.pot_name}", pad=20)
    ax.set_xlabel("Date")
    ax.set_ylabel("Balance ($)")

    # Format date axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    plt.gcf().autofmt_xdate()

    # --- Legend below chart (same style) ---
    ax.legend(
        title="Key",
        bbox_to_anchor=(0.5, -0.2),
        loc="upper center",
        ncol=2,
    )

    sns.despine(left=True, bottom=True)
    plt.tight_layout()
    
    return fig  # for Streamlit compatibility

def active_pot_confirmation(pots):
    while True:
        print_slow("\nPlease confirm the Pot you are currently using to withdraw funds")
        active_pot = input()
        if active_pot == "None":
            active_pot = None
            print_slow_nospace(f"\nThanks, {active_pot} has been confirmed as your active pot")
            return active_pot
        pot_names = []
        for pot in pots.values():
            pot_names.append(pot.pot_name)
        if active_pot in pot_names:
            break
        else:
            print_slow_nospace("\nPot name not found")

    print_slow_nospace(f"\nThanks, {active_pot} has been confirmed as your active pot")
    return active_pot
    
def pot_dict(pots):
    pot_dict = {}
    for pot in pots.values():
        pot_dict[f"{pot.pot_id}"] = pot.pot_name
    return pot_dict





    