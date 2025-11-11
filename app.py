import datetime,os,sqlite3,math,io
import pandas as pd
import streamlit as st

from project_classes import User,Vault,Pot,Transaction,Balances
from project_functions import submit_transaction,convert_date,summary,create_pot,create_user,create_vault,create_profile,re_user,re_vaults,re_pots,re_transactions,re_balances,count_pots,count_transactions,count_vaults,transaction_summary,del_profile,del_vault,del_pot,del_transaction,user_exist,refresh_user_data,refresh_pot_vault_values,balance_update,auto_transaction,previous_balances_variable,pot_forecast,pot_dict,update_pot,update_transaction,active_pot_dict,balance_transaction,undo_last_balance,currency_convert
from streamlit_option_menu import option_menu
from tabulate import tabulate
from time import sleep

if "just_undid_balance" not in st.session_state:
    st.session_state.just_undid_balance = False

# Initiate back-end
vaults = {}
pots = {}
transactions = {}
currency_list = ("USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "THB", "SGD", "HKD", "CNY", "KRW", "INR", "IDR", "MYR", "PHP", "VND", "ZAR", "AED", "MXN", "TRY", "SEK", "NOK", "DKK")

db_path = "money.db"
database_exists = os.path.isfile(db_path)

# Establish a connection to the Database
con = sqlite3.connect(db_path)
cur = con.cursor()
login = "Mike"
user_exists = user_exist(con,login)

# Create user and username variables
user = re_user(con,login)
username = login

st.markdown(
    """
    <style>
        /* Desktop + Tablet (shared layout) */
        .block-container {
            width: 1000px;
            margin: auto;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
        }

        /* Mobile breakpoint */
        @media (max-width: 480px) {
            .block-container {
                max-width: 100%;
                padding-left: 1rem;
                padding-right: 1rem;
            }
        }

        /* Hide Streamlit default header */
        .stApp > header {
            display: none;
        }

        /* Adjust top spacing */
        .block-container {
            padding-top: 2.5rem !important;
        }

        h1 {
            text-align: center;
        }

    </style>
    """,
    unsafe_allow_html=True
)

# Banner Image
st.image("images/moneypots_logo_banner.png", width=1000)

# Set page configuration
st.set_page_config(layout="wide")

# Create the horizontal menu
selected = option_menu(
    menu_title=None, 
    options=["Dashboard", "Budgets", "Transactions", "Instructions", "Account"],
    icons=["graph-up", "bar-chart", "currency-dollar", "question-circle", "gear"], 
    menu_icon="cast",  
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#fafafa"},
        "icon": {"color": "orange", "font-size": "18px"}, 
        "nav-link": {"font-size": "18px", "text-align": "center", "margin":"0px", "--hover-color": "#eee"},
        "nav-link-selected": {"background-color": "#62b07d"},
    }
)

# Tab-change refresh
if "prev_selected" not in st.session_state:
    st.session_state.prev_selected = selected
else:
    if st.session_state.prev_selected != selected:
        # User switched tabs
        st.session_state.prev_selected = selected

        # Clear cached table so Budgets refreshes immediately
        if "budget_data" in st.session_state:
            del st.session_state["budget_data"]

        # Force a fresh reload when switching to Budgets
        if selected == "Budgets":
            with st.spinner("Refreshing data..."):
                vaults, vault_ids, pots, pot_ids, transactions, transaction_ids, balances, previous_balances = refresh_user_data(
                    con, user, username
                )
                pots, vaults = refresh_pot_vault_values(pots, vaults)

# Refresh user data
vaults, vault_ids,pots,pot_ids,transactions,transaction_ids,balances,previous_balances = refresh_user_data(con,user,username)
# Update Pots and Vaults values, using class methods
pots,vaults = refresh_pot_vault_values(pots,vaults)
# Create pot names dictionary and list
pot_names_dict = pot_dict(pots)
pot_names_list = list(pot_names_dict.values())
pot_names_list.insert(0,None)
# Create active pot names dictionary and list
active_pot_names_dict = active_pot_dict(pots)
active_pot_names_list = list(active_pot_names_dict.values())
active_pot_names_list.insert(0,None)
active_pot = balances.active_pot


# Display content based on the selected option
if selected == "Dashboard":
    col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 0.75, 1, 0.75, 1.5])
    with col1:
        # Try to set default index for selectbox
        try:
            default_index = active_pot_names_list.index(active_pot)
        except (ValueError, NameError):
            default_index = 0  # fallback if not found or undefined

        active_pot = st.selectbox(
            "Select active pot:",
            active_pot_names_list,
            index=default_index if pot_names_list else None
        )
        balances.update_active_pot(balances, active_pot_names_list, active_pot)
       
    with col2:
        # Bank balance tracker - ALWAYS use current database value
        db_bank_balance = balances.bank_balance

        # Update session state to match current database value
        st.session_state.bank_balance_input = str(db_bank_balance)

        bank_balance = st.text_input(
            "Current bank balance:", 
            value=st.session_state.bank_balance_input
        )
        balances.update_bank_balance(bank_balance)

    with col3:
        #bank_currency
        db_bank_currency = balances.bank_currency 
        bank_currency = st.selectbox(
            "Bank currency:",
            currency_list,
            index=currency_list.index(db_bank_currency)
        )
        balances.update_bank_currency(bank_currency)

    with col4:
        # Cash balance tracker - ALWAYS use current database value
        db_cash_balance = balances.cash_balance

        # Update session state to match current database value
        st.session_state.cash_balance_input = str(db_cash_balance)

        cash_balance = st.text_input(
            "Current cash balance:", 
            value=st.session_state.cash_balance_input
        )
        balances.update_cash_balance(cash_balance)

    with col5:
        #cash_currency
        db_cash_currency = balances.cash_currency
        cash_currency = st.selectbox(
            "Cash currency:",
            currency_list,
            index=currency_list.index(db_cash_currency),
        )
        balances.update_cash_currency(cash_currency)

    with col6:
        graph_list = ["Pot Spending Forecast","Summary of Pot Balances"]
        display_graph = st.selectbox(
            "Display graph:",
            graph_list,
            index=0,
        )

    # SUBMIT THESE COLUMNS TO THE DATABASE
    if (float(db_bank_balance) != float(bank_balance) or float(db_cash_balance) != float(cash_balance)) and not st.session_state.get('just_undid_balance', False):
        bank_reduction = float(db_bank_balance) - float(bank_balance)
        cash_reduction = float(db_cash_balance) - float(cash_balance)
        if db_bank_currency == db_cash_currency:
            total_reduction = bank_reduction + cash_reduction
        else:
            cash_reduction = currency_convert(db_bank_currency, db_cash_currency, cash_reduction)
            total_reduction = bank_reduction + cash_reduction

        active_pot_obj = next((p for p in pots.values() if p.pot_name == active_pot), None)
        active_pot_balance = active_pot_obj.pot_value() if active_pot_obj else 0

        if total_reduction > active_pot_balance:
            msg = st.empty()
            msg.error("Error: Total reduction exceeds the active pot balance! Refresh page to proceed")
            st.stop()

        # --- END CHECK ---
        
        # Update balances normally
        balance_update(con, balances, bank_balance, cash_balance, pot_names_list, bank_currency, cash_currency, active_pot)
        msg = st.empty()
        msg.success("Balance updates submitted")
        sleep(2)
        msg.empty()
        st.rerun()

    # Reset the flag after processing
    st.session_state.just_undid_balance = False

    # Create auto_transaction
    transaction_count = count_transactions(con)
    auto_transaction_variable = auto_transaction(con,pots,vaults,user,username,balances,previous_balances,active_pot)
    if auto_transaction_variable != None:
        transactions[f"transaction_{(transaction_count + 1)}"] = auto_transaction_variable
    # Refresh user data and pot/vault values
    vaults, vault_ids,pots,pot_ids,transactions,transaction_ids,balances,previous_balances = refresh_user_data(con,user,username)
    pots,vaults = refresh_pot_vault_values(pots,vaults)
    
    if display_graph == "Pot Spending Forecast":
        # Plot Forecast
        fig = pot_forecast(con,pots,active_pot,balances)
        st.pyplot(fig)

    else:
        # Plot summary chart
        fig = summary(vaults, pots, dynamic_width=True)

        # Assume 'fig' is your Matplotlib figure
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches='tight')
        buf.seek(0)

        # Scrollable wrapper
        st.markdown("""
        <div style="overflow-x:auto; overflow-y:hidden; width:100%;">
        """, unsafe_allow_html=True)

        # Use `use_container_width=False` to prevent auto-scaling
        st.image(buf, width='content')
        st.markdown("</div>", unsafe_allow_html=True)

    
    col1, col2, col3 = st.columns([2.4, 1, 2])
    with col2:
        if st.button("Undo Last Balance Update"):
            # Set flag to prevent auto-submit
            st.session_state.just_undid_balance = True

            undo = undo_last_balance(con, balances.username, balances)

            
            if undo == True:
                # Refresh user data to see if anything changed
                vaults, vault_ids, pots, pot_ids, transactions, transaction_ids, balances, previous_balances = refresh_user_data(con, user, username)
                pots, vaults = refresh_pot_vault_values(pots, vaults)

                # Update session state to match new balances
                st.session_state.bank_balance_input = str(balances.bank_balance)
                st.session_state.cash_balance_input = str(balances.cash_balance)

                msg = st.empty()
                st.success("Undo successful — reverted to previous balance.")
                sleep(2)
                msg.empty()
                st.rerun()

            elif undo == False:
                msg = st.empty()
                st.warning("No previous balance entry found to undo.")
                sleep(2)
                msg.empty()
                    

elif selected == "Budgets":
    # Refresh user data
    vaults, vault_ids, pots, pot_ids, transactions, transaction_ids, balances, previous_balances = refresh_user_data(con, user, username)
    # Update Pots and Vaults values, using class methods
    pots, vaults = refresh_pot_vault_values(pots, vaults)

    # Generate base DataFrame depending on whether pots exist
    if len(pots) == 0:
        df = pd.DataFrame(
            [
                {
                    "Spend Type": "Daily expenses",
                    "Pot_ID": None,
                    "Pot Name": None,
                    "Pot Budget": None,
                    "Pot Balance": None,
                    "Start Date": None,
                    "End Date": None,
                    "Number of Days": None,
                    "Daily Allowance": None,
                },
                {
                    "Spend Type": "Miscellaneous",
                    "Pot_ID": None,
                    "Pot Name": None,
                    "Pot Budget": None,
                    "Pot Balance": None,
                    "Start Date": None,
                    "End Date": None,
                    "Number of Days": None,
                    "Daily Allowance": None,
                },
            ]
        )

        # Convert dates to date objects
        df["Start Date"] = pd.to_datetime(df["Start Date"], errors="coerce")
        df["End Date"] = pd.to_datetime(df["End Date"], errors="coerce")
    
    else:
        df_list_of_dicts = []
        for pot in pots.values():
            df_list_of_dicts.append(
                {
                    "Spend Type": pot.vault.vault_name,
                    "Pot_ID": pot.pot_id,
                    "Pot Name": pot.pot_name,
                    "Pot Budget": pot.amount,
                    "Pot Balance": pot.pot_value(),
                    "Start Date": pot.start_date.strftime("%d/%m/%y"),
                    "End Date": pot.end_date.strftime("%d/%m/%y"),
                    "Number of Days": pot.date_delta,
                    "Daily Allowance": pot.daily_expenditure,
                }
            )

        df = pd.DataFrame(df_list_of_dicts)
        df["Start Date"] = pd.to_datetime(df["Start Date"], format="%d/%m/%y", errors="coerce")
        df["End Date"] = pd.to_datetime(df["End Date"], format="%d/%m/%y", errors="coerce")

    # Info messages
    st.info(
        "Enter **'Spend Type'**, **'Pot Name'**, **'Start Date'**, **'End Date'** and either **'Pot Budget'** or **'Daily Allowance'** — the other will be auto-calculated. "
        "If both are set, **'Pot Budget'** takes priority."
    )
    st.info(
        "The **'Pot Balance'** and **'Number of Days'** columns are auto-calculated — no user inputs required. "
        "Click **'Calculate Automatic Values'** to update."
    )

    # Create or refresh the session data
    if "budget_data" not in st.session_state:
        st.session_state.budget_data = df.copy()

    # Create editable table
    edited_df = st.data_editor(
        st.session_state.budget_data,
        num_rows="dynamic",
        disabled=["Pot_ID", "Pot Balance", "Number of Days"],
        key="budget_editor",
        column_config={
            "Spend Type": st.column_config.SelectboxColumn(
                "Spend Type",
                options=["Daily expenses", "Miscellaneous"],
                default="Daily expenses",
            ),
            "Pot_ID": st.column_config.NumberColumn("Pot_ID"),
            "Pot Name": st.column_config.TextColumn("Pot Name"),
            "Pot Budget": st.column_config.NumberColumn(
                "Pot Budget",
                min_value=0.0,  # prevents negative numbers
                step=0.01,
                help="Enter a positive amount only",
            ),
            "Pot Balance": st.column_config.NumberColumn("Pot Balance"),
            "Start Date": st.column_config.DateColumn("Start Date", format="DD/MM/YY"),
            "End Date": st.column_config.DateColumn("End Date", format="DD/MM/YY"),
            "Number of Days": st.column_config.NumberColumn("Number of Days"),
            "Daily Allowance": st.column_config.NumberColumn("Daily Allowance"),
        },
    )

    # Calculate Button
    if st.button("Calculate Automatic Values", key="calc_btn"):
        df_calc = edited_df.copy()

        # Error Checking
        required_cols = ["Spend Type", "Pot Name", "Start Date", "End Date"]
        missing_rows = df_calc[df_calc[required_cols].isnull().any(axis=1)]
        if not missing_rows.empty:
            msg = st.empty()
            msg.error("All rows must have **Spend Type, Pot Name, Start Date, and End Date** filled before calculation.")
            sleep(3)
            msg.empty()
            st.rerun()

        # Convert to datetime and validate
        df_calc["Start Date"] = pd.to_datetime(df_calc["Start Date"], errors="coerce")
        df_calc["End Date"] = pd.to_datetime(df_calc["End Date"], errors="coerce")

        if df_calc["Start Date"].isna().any() or df_calc["End Date"].isna().any():
            msg = st.empty()
            msg.error("Invalid or missing dates detected — please correct them before calculation.")
            sleep(3)
            msg.empty()
            st.rerun()

        # Ensure start date < end date
        invalid_dates = df_calc[df_calc["End Date"] < df_calc["Start Date"]]
        if not invalid_dates.empty:
            msg = st.empty()
            msg.error("Each **End Date** must be after its **Start Date**")
            sleep(3)
            msg.empty()
            st.rerun()

        # Now calculate number of days
        df_calc["Number of Days"] = (df_calc["End Date"] - df_calc["Start Date"]).dt.days

        # Start by checking the database
        next_id = count_pots(con)
        highest_id = next_id

        # Now check the DataFrame
        for _, row in df_calc.iterrows():
            pot_id = row["Pot_ID"]
            if pd.notna(pot_id) and int(pot_id) > highest_id:
                highest_id = int(pot_id)

        # Next available ID
        next_id = int(highest_id) + 1

        for i, row in df_calc.iterrows():
            pot_id = row["Pot_ID"]
            delta = row["Number of Days"]
            if pd.notna(delta) and delta > 0:
                pot_budget = row["Pot Budget"]
                daily_allowance = row["Daily Allowance"]

                if pd.notna(pot_budget) and pd.isna(daily_allowance):
                    df_calc.at[i, "Daily Allowance"] = round(pot_budget / delta, 2)
                elif pd.isna(pot_budget) and pd.notna(daily_allowance):
                    df_calc.at[i, "Pot Budget"] = round(daily_allowance * delta, 2)
                elif pd.notna(pot_budget) and pd.notna(daily_allowance):
                    df_calc.at[i, "Daily Allowance"] = round(pot_budget / delta, 2)

            if pd.isna(df_calc.at[i, "Pot_ID"]):
                df_calc.at[i, "Pot_ID"] = int(next_id)
                next_id += 1

        # Save
        st.session_state.budget_data = df_calc
        edited_df = df_calc.copy()  # optional but safe

        # Display success message
        msg = st.empty()
        msg.success("Calculation Successful")
        sleep(2)
        msg.empty()
        st.rerun()

    # Submit Button
    if st.button("Submit Updates", key="submit_btn"):
        if balances.bank_balance == 0 and balances.cash_balance == 0:
            st.error("Must update bank and cash balances before creating new pots")
            st.stop()

        if (edited_df["Pot Budget"].isna() | (edited_df["Pot Budget"] <= 0)).any():
            msg = st.empty()
            msg.error("Pot Budget must be greater than 0")
            sleep(3)
            msg.empty()
            st.rerun()

        if (edited_df["Daily Allowance"].isna() | (edited_df["Daily Allowance"] <= 0)).any():
            msg = st.empty()
            msg.error("Daily Allowance must be greater than 0")
            sleep(3)
            msg.empty()
            st.rerun()

        # Remove empty rows, check expected cols and save
        expected_cols = [
            "Spend Type",
            "Pot Name",
            "Pot Budget",
            "Start Date",
            "End Date",
            "Number of Days",
            "Daily Allowance",
        ]
        missing_rows = edited_df[edited_df[expected_cols].isnull().any(axis=1)]
        if not missing_rows.empty:
            msg = st.empty()
            msg.error('All rows must have **Spend Type, Pot Name, Pot Budget, Start Date, End Date, Number of Days and Daily Allowance** filled before submission. You may need to **Calcuate Automatic Values** first')
            sleep(5)
            msg.empty()
            st.rerun()

        final_df = edited_df.dropna(subset=expected_cols, how="any").reset_index(drop=True)

        # Calculate if pots budgets exceed balances
        total_spend = 0
        for pot in pots.values():
            total_spend += pot.pot_spend()
        total_balance = balances.combined_balance(balances)
        total_pot_budget = final_df["Pot Budget"].sum()
        total_spend_plus_balance = total_balance + total_spend
        if total_pot_budget > total_spend_plus_balance:
            st.error("Budget estimate created exceeds your bank balance and previous spending! Add more money to your balances or reduce your budget estimates")
            st.stop()

        # Save
        st.session_state.budget_data = final_df.copy()
        edited_df = final_df.copy()

        # Display success message
        msg = st.empty()
        msg.success("Updates submitted")
        sleep(2)
        msg.empty()

        # Submit to Database
        # Compare dataframes. Add deleted pots to a set and use to delete from db
        deleted_pot_ids = set(df["Pot_ID"]) - set(edited_df["Pot_ID"])
        for pot_id in deleted_pot_ids:
            del_pot(con, user, pots, username, pot_names_dict, pot_id)

        # Compare dataframes. Add new pots to a set and use to submit to the db
        new_pot_ids = set(edited_df["Pot_ID"]) - set(df["Pot_ID"])
        for pot in new_pot_ids:
            # Create new variables for pot object
            pot_count = count_pots(con)
            spend_type = edited_df.loc[edited_df["Pot_ID"] == pot, "Spend Type"].iloc[0]
            pot_name = edited_df.loc[edited_df["Pot_ID"] == pot, "Pot Name"].iloc[0]
            pot_budget = edited_df.loc[edited_df["Pot_ID"] == pot, "Pot Budget"].iloc[0]
            start_date = edited_df.loc[edited_df["Pot_ID"] == pot, "Start Date"].iloc[0]
            end_date = edited_df.loc[edited_df["Pot_ID"] == pot, "End Date"].iloc[0]

            if spend_type != None:
                # Convert date objects
                start_date = convert_date(start_date)
                end_date = convert_date(end_date)

                # Create Pot object
                pots[f"pot_{(pot_count + 1)}"] = create_pot(
                    con,
                    pot_count,
                    vaults,
                    user,
                    username,
                    spend_type,
                    pot_name,
                    pot_budget,
                    start_date,
                    end_date,
                )

        # Iterate through edited df and UPDATE each row in the database
        edited_df.columns = edited_df.columns.str.replace(" ", "_")
        for row in edited_df.itertuples(index=False):
            spend_type = row._asdict().get("Spend_Type")
            pot_id = row._asdict().get("Pot_ID")
            pot_name = row._asdict().get("Pot_Name")
            pot_budget = row._asdict().get("Pot_Budget")
            start_date = row._asdict().get("Start_Date")
            end_date = row._asdict().get("End_Date")

            if spend_type != None:
                # Convert date objects
                start_date = convert_date(start_date)
                end_date = convert_date(end_date)

                # Update Pot object
                update_pot(
                    con,
                    pot_id,
                    vaults,
                    user,
                    username,
                    spend_type,
                    pot_id,
                    pot_name,
                    pot_budget,
                    start_date,
                    end_date,
                )

        # Recalculate pots and vaults from updated database 
        vaults, vault_ids, pots, pot_ids, transactions, transaction_ids, balances, previous_balances = refresh_user_data(con, user, username)
        pots, vaults = refresh_pot_vault_values(pots, vaults)
        
        # Clear cached table data to ensure pot balances refresh
        if "budget_data" in st.session_state:
            del st.session_state["budget_data"]
        st.rerun()

elif selected == "Transactions":
    # Refresh user data
    vaults, vault_ids, pots, pot_ids, transactions, transaction_ids, balances, previous_balances = refresh_user_data(con, user, username)
    pots, vaults = refresh_pot_vault_values(pots, vaults)

    # Base data
    if len(transactions) == 0:
        transactions_df = pd.DataFrame(
            [
                {
                    "Transaction_ID": None,
                    "Transaction Name": None,
                    "Date": None,
                    "Pot Name": None,
                    "Amount": None,
                }
            ]
        )
        transactions_df["Date"] = pd.to_datetime(transactions_df["Date"], errors="coerce")

    else:
        transactions_df_list_of_dicts = []
        for transaction in transactions.values():
            # Exclude auto-generated transactions
            if transaction.manual_transaction == 0 or transaction.balance_transaction == 1:
                continue

            transaction_dict = {
                "Transaction_ID": f"{transaction.transaction_id}",
                "Transaction Name": f"{transaction.transaction_name}",
                "Date": transaction.date.strftime("%d/%m/%y"),
                "Pot Name": pot_names_dict.get(str(transaction.pot_id), ""),
                "Amount": (transaction.amount * -1),
            }
            transactions_df_list_of_dicts.append(transaction_dict)

        # Recheck for empty after filtering
        if len(transactions_df_list_of_dicts) == 0:
            transactions_df = pd.DataFrame(
                [
                    {
                        "Transaction_ID": None,
                        "Transaction Name": None,
                        "Date": None,
                        "Pot Name": None,
                        "Amount": None,
                    }
                ]
            )
            transactions_df["Date"] = pd.to_datetime(transactions_df["Date"], format="%d/%m/%y", errors="coerce")
        else:
            transactions_df = pd.DataFrame(transactions_df_list_of_dicts)
            transactions_df["Date"] = pd.to_datetime(transactions_df["Date"], format="%d/%m/%y", errors="coerce")

    # Session setup 
    if "transactions_submitted" not in st.session_state:
        st.session_state.transactions_submitted = False

    # Editable section
    if not st.session_state.transactions_submitted:
        st.info("Edit existing transactions, delete rows, or add new ones at the bottom.")

        transactions_edited_df = st.data_editor(
            transactions_df,
            num_rows="dynamic",
            key="transactions_editor",
            column_config={
                "Transaction_ID": st.column_config.TextColumn("Transaction_ID", disabled=True),
                "Transaction Name": st.column_config.TextColumn("Transaction Name"),
                "Date": st.column_config.DateColumn("Date", format="DD/MM/YY"),
                "Pot Name": st.column_config.SelectboxColumn(
                    "Pot Name",
                    options=pot_names_list,
                    help="Select the pot this transaction belongs to",
                ),
                "Amount": st.column_config.NumberColumn(
                    "Amount",
                    min_value=0.0,
                    step=0.01,
                    help="Enter a positive amount only",
                ),
            },
        )

        # Submission
        if st.button("Submit"):
            # Remove empty rows and validate before saving
            today= datetime.date.today()

            # Convert the 'Date' column to dates (no time)
            transaction_dates = pd.to_datetime(transactions_edited_df["Date"], errors="coerce").dt.date

            if (transaction_dates > today).any():
                msg = st.empty()
                msg.error("Transaction dates cannot be in the future.")
                sleep(3)
                msg.empty()
                st.rerun()

            expected_cols = ["Transaction Name", "Date", "Pot Name", "Amount"]
            missing_rows = transactions_edited_df[transactions_edited_df[expected_cols].isnull().any(axis=1)]
            
            if not missing_rows.empty:
                msg = st.empty()
                msg.error('All rows must have **Transaction Name, Date, Pot Name and Amount** filled before submission')
                sleep(3)
                msg.empty()
                st.rerun()

            transactions_final_df = transactions_edited_df.dropna(how="all").reset_index(drop=True)

            # Success message
            msg = st.empty()
            msg.success("Transactions updated successfully")
            sleep(2)
            msg.empty()

            # Delete removed transactions
            old_ids = set(transactions_df["Transaction_ID"].dropna().astype(int))
            new_ids = set(transactions_edited_df["Transaction_ID"].dropna().astype(int))
            deleted_transaction_ids = old_ids - new_ids
            for transaction_id in deleted_transaction_ids:
                del_transaction(con, user, transactions, username, transaction_id)

                # Find and delete any linked balance transaction
                for t in list(transactions.values()):  # list() copy to avoid mutation during iteration
                    # Match by naming convention (Balance + original name)
                    if t.transaction_name.startswith("Balance "):
                        original_name = t.transaction_name.replace("Balance ", "")
                        if transactions.get(f"transaction_{transaction_id}") and \
                        transactions[f"transaction_{transaction_id}"].transaction_name == original_name:
                            del_transaction(con, user, transactions, username, t.transaction_id)

            # Add new transactions
            existing_ids = {int(t.transaction_id) for t in transactions.values()}
            next_available_id = max(existing_ids) + 1 if existing_ids else 1
            transaction_type = "out"

            new_rows = transactions_edited_df[
                transactions_edited_df["Transaction_ID"].isnull() | (transactions_edited_df["Transaction_ID"] == "")
            ]

            for _, row in new_rows.iterrows():
                transaction_id = next_available_id
                next_available_id += 1

                transaction_name = row["Transaction Name"]
                date = row["Date"]
                pot_name = row["Pot Name"]
                amount = (row["Amount"] * -1)

                if transaction_name:
                    date = convert_date(date)
                    transactions[f"transaction_{transaction_id}"] = submit_transaction(
                        con,
                        transaction_id,
                        pots,
                        vaults,
                        user,
                        username,
                        transaction_name,
                        pot_name,
                        date,
                        amount,
                        transaction_type,
                    )

                # Balance-transaction logic
                transaction_pot = next((p for p in pots.values() if p.pot_name == pot_name), None)
                if not transaction_pot:
                    continue

                if pot_name in active_pot_names_list and len(transaction_pot.transactions) > 0:
                    balance_transaction_name = "Balance " + transaction_name
                    transaction_id += 1
                    next_available_id += 1
                    balance_transaction_type = "in"
                    balance_amount = -amount
                    transactions[f"transaction_{transaction_id}"] = balance_transaction(
                        con,
                        transaction_id,
                        pots,
                        vaults,
                        balances,
                        previous_balances,
                        user,
                        username,
                        balance_transaction_name,
                        pot_name,
                        date,
                        balance_amount,
                        balance_transaction_type,
                    )

            # Update all transactions in DB
            transactions_edited_df.columns = transactions_edited_df.columns.str.replace(" ", "_")

            for row in transactions_edited_df.itertuples(index=False):
                row_dict = row._asdict()
                transaction_id = row_dict.get("Transaction_ID")
                transaction_name = row_dict.get("Transaction_Name")
                date = row_dict.get("Date")
                pot_name = row_dict.get("Pot_Name")
                amount = (row_dict.get("Amount") * -1)

                if transaction_name:
                    date = convert_date(date)
                    update_transaction(
                        con,
                        transaction_id,
                        pots,
                        vaults,
                        user,
                        username,
                        transaction_name,
                        pot_name,
                        date,
                        amount,
                        transaction_type,
                    )

            # 🔄 Refresh everything from the DB (ensures Transaction_IDs are up to date)
            vaults, vault_ids, pots, pot_ids, transactions, transaction_ids, balances, previous_balances = refresh_user_data(con, user, username)
            pots, vaults = refresh_pot_vault_values(pots, vaults)

            # 🧱 Rebuild fresh DataFrame from updated DB (like Budgets tab)
            transactions_final_list = []
            for transaction in transactions.values():
                if transaction.manual_transaction == 0 or transaction.balance_transaction == 1:
                    continue
                transactions_final_list.append({
                    "Transaction_ID": f"{transaction.transaction_id}",
                    "Transaction Name": f"{transaction.transaction_name}",
                    "Date": transaction.date.strftime("%d/%m/%y"),
                    "Pot Name": pot_names_dict.get(str(transaction.pot_id), ""),
                    "Amount": (transaction.amount * -1),
                })

            if len(transactions_final_list) == 0:
                transactions_final_df = pd.DataFrame(
                    [{"Transaction_ID": None, "Transaction Name": None, "Date": None, "Pot Name": None, "Amount": None}]
                )
                transactions_final_df["Date"] = pd.to_datetime(transactions_final_df["Date"], errors="coerce")
            else:
                transactions_final_df = pd.DataFrame(transactions_final_list)
                transactions_final_df["Date"] = pd.to_datetime(transactions_final_df["Date"], format="%d/%m/%y", errors="coerce")

            # Save to session and refresh
            st.session_state.transactions_submitted = True
            st.session_state.transactions_final = transactions_final_df.copy()

            if "transactions_editor" in st.session_state:
                del st.session_state["transactions_editor"]

            st.rerun()

    else:
        # Display final table in read-only mode
        st.data_editor(
            st.session_state.transactions_final,
            disabled=True,
            key="transactions_final_view",
        )
        st.session_state.transactions_submitted = False
        st.rerun()


elif selected == "Instructions":
    st.markdown("""### Introduction
                
Money Pots helps you manage your travel savings on long trips.
All you need is a separate bank account loaded with your trip funds. From there, you can use Money Pots to plan and track your budget for each part of your journey.
 
### Categories

Your money is divided into two main categories:

##### Daily Expenses
For everyday costs such as food, drinks, hotels, tourist activities, and souvenirs.

##### Other 
For planned or unexpected expenses that arent part of your daily spending, like phone bills, insurance payments, or repairs.

### Creating Pots

Within each category, you can create individual Pots in the Budgets tab.

For example, under **Daily Expenses**, you might create a Pot for each destination on your trip.  
To set a budget, enter your planned **daily expenditure** (e.g. $100/day) and the **start and end dates** for that location.  

Using this data, Money Pots automatically generates a **forecast graph** showing whether your spending is on track throughout your trip.

##### Tracking and Updates

Your **daily expenditure** is automatically calculated each time you enter your **bank and cash balances**, which you can update as often as you like.  

If you would like to add more detail to your spending, you can also submit daily expenditures manually in the **Transactions** tab.

### **Other** Category

For the **Other** category, Pot balances are updated manually. Simply create a **Transaction** whenever you make a payment from your bank.  

*This works best if you dont have any direct debits set up on the account you are using*
""", unsafe_allow_html=True)

elif selected == "Account":
    database_password = "password"
    st.markdown("## Change Password")
    old_password = st.text_input("Old Password", "")
    new_password = st.text_input("New Password", "")
    confirm_password = st.text_input("Confirm Password", "")
    if st.button("Submit"):
        if old_password == database_password and new_password == confirm_password:
            st.write("Password Changed")
        else:
            st.write("Incorrect Passwords")


    st.markdown("## Delete Account")
    if st.button("Delete Account"):
        st.write("Account Deleted, Logging Out")