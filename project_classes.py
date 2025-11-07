from __future__ import annotations
import datetime
import json
import pandas as pd
import requests
import os

class User:
    def __init__(self, username):
        """
        Initialize a User object.

        :param username: The username of the user.
        """
        self.username = username
    
class Vault:
    def __init__(self, vault_id, vault_name, user):
        """
        Initialize a Vault object.

        :param vault_id: The ID of the vault (must be an integer).
        :param vault_name: The name of the vault.
        :param username: The username of the user associated with the vault (optional).
                       If not provided, it will use the username from the User class.
        """

        # Validations
        if not isinstance(vault_id, int):
            raise ValueError("ID must be an integer value!")
        
        if not isinstance(user, User): 
            raise ValueError("user must be an instance of the User class!")

        # Assign to self object
        self.vault_id = vault_id
        self.vault_name = vault_name
        self.user = user 
        self.username = user.username 
        self.pots = []  

    def __str__(self):
        return f"Vault(vault_id={self.vault_id}, vault_name={self.vault_name}, username={self.username})"
    
    def add_pot(self, pot):
        """
        Add a Pot instance to the Vault's list of pots.

        :param pot: The Pot instance to add.
        """
        if not isinstance(pot, Pot):
            raise ValueError("pot must be an instance of the Pot class!")
        self.pots.append(pot)

    def vault_value(self):
        """Returns current value of vault (sum of all pot current values)"""
        return sum(pot.pot_value() for pot in self.pots)
    
    def initial_vault_value(self):
        """Returns current value of vault (sum of all pot current values)"""
        return sum(pot.amount for pot in self.pots)
    
class Pot:
    def __init__(self, pot_id, pot_name, vault, user, start_date, end_date, amount=0.00):
        """
        Initialize a Pot object.

        :param pot_id: The ID of the pot (must be an integer and unique to Pot).
        :param pot_name: The name of the pot.
        :param vault: The Vault object associated with the pot.
        :param username: The username of the user associated with the pot (optional).
        :param start_date: The date that pot starts being used to withdraw funds.
        :param end_date: The date that pot finishes being used to withdraw funds.
        :param amount: The amount of the pot. Default is 0.00.
        """

        # Validations
        try:
            if not isinstance(pot_id, int):
                raise ValueError(f"pot_id must be int, got {type(pot_id)} (value={pot_id})")
        except (TypeError, ValueError) as e:
            print(f"[VALIDATION ERROR] pot_id check failed -> {e}")
            raise

        try:
            if not isinstance(vault, Vault):
                raise ValueError(f"vault must be Vault, got {type(vault)} (value={vault})")
        except (TypeError, ValueError) as e:
            print(f"[VALIDATION ERROR] vault check failed -> {e}")
            raise

        try:
            if not isinstance(start_date, datetime.date):
                raise ValueError(f"start_date must be datetime.date, got {type(start_date)} (value={start_date})")
        except (TypeError, ValueError) as e:
            print(f"[VALIDATION ERROR] start_date check failed -> {e}")
            raise

        try:
            if not isinstance(end_date, datetime.date):
                raise ValueError(f"end_date must be datetime.date, got {type(end_date)} (value={end_date})")
        except (TypeError, ValueError) as e:
            print(f"[VALIDATION ERROR] end_date check failed -> {e}")
            raise

        try:
            if not isinstance(user, User):
                raise ValueError(f"user must be User, got {type(user)} (value={user})")
        except (TypeError, ValueError) as e:
            print(f"[VALIDATION ERROR] user check failed -> {e}")
            raise
        
         # Assign unique Pot attributes
        self.pot_id = pot_id
        self.pot_name = pot_name
        self.vault = vault  
        self.vault_id = vault.vault_id 
        self.amount = amount
        self.transactions = [] 
        self.user = user 
        self.username = user.username
        self.start_date = start_date
        self.end_date = end_date
        self.date_delta = round((self.end_date - self.start_date).days)
        # Avoid division by zero
        if self.date_delta <= 0:
            raise ValueError("End date must be after start date")
        self.daily_expenditure = amount / self.date_delta
        
    def add_transaction(self, transaction):
        """
        Add a transaction instance to the pots list of transactions.
        :param transaction: The transaction instance to add.
        """
        if not isinstance(transaction, Transaction):
            raise ValueError("transaction must be an instance of the Transaction class!")
        self.transactions.append(transaction)
    
    def pot_value(self):
        """Return current value (base amount + valid transactions to date)."""
        total = self.amount
        today = datetime.date.today()
        
        for transaction in self.transactions:
            # Ensure correct type comparison
            tx_date = transaction.date.date() if isinstance(transaction.date, datetime.datetime) else transaction.date
            if tx_date <= today:
                # if transaction.amount < 0: # Removed this. Check correctness
                total += transaction.amount

        return total
    
    def pot_spend(self):
        """Returns sum of transactions to date)"""
        sum = 0
        today = datetime.date.today()
        for transaction in self.transactions:
            if transaction.date <= today and transaction.balance_transaction == 0:
                if transaction.amount < 0:
                    sum += transaction.amount
        return abs(sum)
            
class Transaction:
    def __init__(self, transaction_id, transaction_name, date, pot, vault, user, manual_transaction, balance_transaction, type="out", amount=0.00):
        """
        Initialize a Transaction object.

        :param transaction_id: The ID of the transaction (must be an integer and unique to the transaction).
        :param transaction_name: Description of the transaction
        :param date: date the transaction occured
        :param amount: The amount of the transaction. Default is 0.00.
        """

        # Validations
        if not isinstance(transaction_id, int):
            raise ValueError("Transaction ID must be an integer value!")
        
        if not isinstance(pot, Pot): 
            raise ValueError("pot must be an instance of the Pot class!")
        
        if type not in ["in", "out"]:
            raise ValueError('Transaction type must be either "in" or "out"!')
        
        if manual_transaction not in [1,0]:
            raise ValueError("manual_transaction must be == 1 (true) or 0 (false)")
        
        if balance_transaction not in [1,0]:
            raise ValueError("balance_transaction must be == 1 (true) or 0 (false)")
        
        # Normalize all date-like inputs
        if isinstance(date, datetime.datetime):
            self.date = date.date()
        elif isinstance(date, datetime.date):
            self.date = date
        else:
            raise ValueError(f"Must be a valid date object, got {type(date)}")
        
         # Assign unique Pot attributes
        self.transaction_id = transaction_id
        self.transaction_name = transaction_name
        self.pot = pot  
        self.pot_id = pot.pot_id 
        self.vault = vault  
        self.vault_id = vault.vault_id
        self.manual_transaction = manual_transaction 
        self.balance_transaction = balance_transaction
        self.type = type
        self.amount = amount
        self.user = user 
        self.username = user.username 
        
        # Add this transaction to the pots list of transactions
        pot.add_transaction(self)

class Balances:
    def __init__(self, balance_id, username, date, bank_currency, cash_currency, bank_balance=0.00, cash_balance=0.00, active_pot=None):
        """
        Initialize a Balances object.

        :param bank_currency: Must be one of: "USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "THB", "SGD", "HKD", "CNY", "KRW", "INR", "IDR", "MYR", "PHP", "VND", "ZAR", "AED", "MXN", "TRY", "SEK", "NOK", "DKK"
        :param cash_currency: Must be one of: "USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "THB", "SGD", "HKD", "CNY", "KRW", "INR", "IDR", "MYR", "PHP", "VND", "ZAR", "AED", "MXN", "TRY", "SEK", "NOK", "DKK"
        :param bank_balance: Users bank balance as a decimel number
        :param cash_balance: Users cash balance as a decimel number
        """

        # Convert string or other date types to datetime
        date = self.convert_date_balances(date)
        
        # Validations
        if bank_currency not in ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "THB", "SGD", "HKD", "CNY", "KRW", "INR", "IDR", "MYR", "PHP", "VND", "ZAR", "AED", "MXN", "TRY", "SEK", "NOK", "DKK"]:
            raise ValueError('Currency types supported are: ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "THB", "SGD", "HKD", "CNY", "KRW", "INR", "IDR", "MYR", "PHP", "VND", "ZAR", "AED", "MXN", "TRY", "SEK", "NOK", "DKK"]')
        
        if cash_currency not in ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "THB", "SGD", "HKD", "CNY", "KRW", "INR", "IDR", "MYR", "PHP", "VND", "ZAR", "AED", "MXN", "TRY", "SEK", "NOK", "DKK"]:
            raise ValueError('Currency types supported are: ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "THB", "SGD", "HKD", "CNY", "KRW", "INR", "IDR", "MYR", "PHP", "VND", "ZAR", "AED", "MXN", "TRY", "SEK", "NOK", "DKK"]')
        
        if not isinstance(bank_balance, float):
            raise ValueError("Bank Balance must be a decimel number!")
        
        if not isinstance(cash_balance, float):
            raise ValueError("Cash Balance must be a decimel number!")
        
        # Normalize all date-like inputs
        if isinstance(date, datetime.datetime):
            self.date = date.date()
        elif isinstance(date, datetime.date):
            self.date = date
        else:
            raise ValueError(f"Must be a valid date object, got {type(date)}")
                
         # Assign unique Pot attributes
        self.balance_id = balance_id
        self.username = username
        self.date = date
        self.bank_currency = bank_currency
        self.cash_currency = cash_currency
        self.bank_balance = bank_balance
        self.cash_balance = cash_balance
        self.active_pot = active_pot

    @staticmethod
    def convert_date_balances(date_input):
        """
        Convert a string in '2025-11-03 08:07:03.859' or a datetime-like object
        to a datetime.datetime object.
        """
        # If already a datetime.datetime, return as-is
        if isinstance(date_input, datetime.datetime):
            return date_input

        # If pandas Timestamp, convert to datetime
        if isinstance(date_input, pd.Timestamp):
            return date_input.to_pydatetime()

        # If string, try parsing
        if isinstance(date_input, str):
            # Try datetime with microseconds
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.datetime.strptime(date_input, fmt)
                except ValueError:
                    continue
            raise ValueError(f"String '{date_input}' is not in a recognized datetime format.")
        
        # Anything else is invalid
        raise TypeError(f"Invalid type for convert_date_balances: {type(date_input)}. Expected str, datetime, or pd.Timestamp.")

    def update_bank_currency(self, currency):
        """Function to update User's home bank currency"""
        if currency in ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "THB", "SGD", "HKD", "CNY", "KRW", "INR", "IDR", "MYR", "PHP", "VND", "ZAR", "AED", "MXN", "TRY", "SEK", "NOK", "DKK"]:
            self.bank_currency = currency
            return f"User's bank currency updated to {currency}"
        else:
            return f"This currency can't be found. User's bank currency remains as {self.bank_currency}"

    def update_cash_currency(self, currency):
        """Function to update the type of currency in use by the User"""
        if currency in ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "THB", "SGD", "HKD", "CNY", "KRW", "INR", "IDR", "MYR", "PHP", "VND", "ZAR", "AED", "MXN", "TRY", "SEK", "NOK", "DKK"]:
            self.bank_currency = currency
            return f"User's cash currency type updated to {currency}"
        else:
            return f"This currency can't be found. User's cash currency type remains as {self.bank_currency}"
    
    def update_bank_balance(self, balance) -> str:
        """Updates a User's bank balance"""
        try:
            self.bank_balance = float(balance)
        except (ValueError, TypeError):
            raise ValueError("Balance must be an integer.")
        return "User's bank balance updated"
    
    def update_cash_balance(self, balance) -> str:
        """Updates a User's cash balance"""
        try:
            self.cash_balance = float(balance)
        except (ValueError, TypeError):
            raise ValueError("Balance must be an integer.")
        return "User's cash balance updated"
    
    def update_date(self, date) -> str:
        """Updates an existing balance's date of change"""
        date = Balances.convert_date_balances(date)

        if not isinstance(date, datetime.datetime):
            raise ValueError(f"Must use a datetime object, got {type(date)}")

        self.date = date
        return "date updated"
    
    def combined_balance(self, balance) -> int:
        """Calculates a User's combined balance
           in their banking currency"""
        
        # Get currency conversion list with bank_currency as the base
        bank_currency = balance.bank_currency
        cash_currency = balance.cash_currency
        conversion_list = requests.get(f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{bank_currency.lower()}.json")
        formatted_conversion_list = conversion_list.json()
        conversion_value = formatted_conversion_list[bank_currency.lower()][cash_currency.lower()]

        # Calculate combined_balance
        cash_balance_home_currency = balance.cash_balance / conversion_value
        combined_balance =  balance.bank_balance + cash_balance_home_currency
        
        return combined_balance
    
    def update_active_pot(self, balance, pot_names_list, active_pot) -> str:
        """Update's the user's active pot"""
        
        if active_pot in pot_names_list:
            balance.active_pot = active_pot
        else:
            balance.active_pot = None
        
        return "User's active pot updated"
    
    
