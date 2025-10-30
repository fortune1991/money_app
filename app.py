import datetime,os,sqlite3,math
import pandas as pd
import streamlit as st

from database import create_database
from project_classes import User,Vault,Pot,Transaction,Balances
from project_functions import submit_transaction,print_slow,print_slow_nospace,int_validator,collect_date,convert_date,summary,create_pot,create_user,create_vault,create_profile,instructions,re_user,re_vaults,re_pots,re_transactions,re_balances,count_pots,count_transactions,count_vaults,transaction_summary,del_profile,del_vault,del_pot,del_transaction,user_exist,refresh_user_data,refresh_pot_vault_values,create_balance,balance_update,balance_summary,check_balances,auto_transaction,previous_balances_variable,active_pot_confirmation,pot_forecast, pot_dict
from streamlit_option_menu import option_menu
from tabulate import tabulate
from time import sleep

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
    menu_title=None,  # No title for the menu itself
    options=["Dashboard", "Budgets", "Transactions", "Instructions", "Account"],
    icons=["graph-up", "bar-chart", "currency-dollar", "question-circle", "gear"], 
    menu_icon="cast",  # Optional icon for the menu button (if collapsed)
    default_index=0,  # Default selected option
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#fafafa"},
        "icon": {"color": "orange", "font-size": "18px"}, 
        "nav-link": {"font-size": "18px", "text-align": "center", "margin":"0px", "--hover-color": "#eee"},
        "nav-link-selected": {"background-color": "#62b07d"},
    }
)

vaults = {}
pots = {}
transactions = {}
currency_list = ("USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "THB", "SGD", "HKD", "CNY", "KRW", "INR", "IDR", "MYR", "PHP", "VND", "ZAR", "AED", "MXN", "TRY", "SEK", "NOK", "DKK")

db_path = "/Users/michaelfortune/Developer/projects/money/money_app/money.db"
database_exists = os.path.isfile(db_path)

# Establish a connection to the Database
con = sqlite3.connect(db_path)
cur = con.cursor()
login = "Mike"
user_exists = user_exist(con,login)

# Create user and username variables
user = re_user(con,login)
username = login
# Refresh user data
vaults, vault_ids,pots,pot_ids,transactions,transaction_ids,balances = refresh_user_data(con,user,username)
# Create previous balances object
previous_balances = previous_balances_variable(balances)
# Update Pots and Vaults values, using class methods
pots,vaults = refresh_pot_vault_values(pots,vaults)
# Display content based on the selected option
if selected == "Dashboard":
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        #active_pot
        active_pot = st.text_input("Pot currently in use:", "Thailand")

    with col2:
        #bank_balance
        active_pot_2 = st.text_input("Current bank balance:", "100")

    with col3:
        #bank_currency
        active_pot_3 = st.selectbox(
            "Bank currency:",
            currency_list,
            index=0,
        )

    with col4:
        #cash_balance
        active_pot_4 = st.text_input("Current cash balance:", "5000")

    with col5:
        #cash_currency
        active_pot_5 = st.selectbox(
            "Cash currency:",
            currency_list,
            index=0,
        )

    # Create auto_transaction
    transaction_count = count_transactions(con)
    auto_transaction_variable = auto_transaction(con,transaction_count,pots,vaults,user,username,balances,previous_balances,active_pot)
    if auto_transaction_variable != None:
        transactions[f"transaction_{(transaction_count + 1)}"] = auto_transaction_variable
    pots,vaults = refresh_pot_vault_values(pots,vaults)
    
    # Plot
    fig = pot_forecast(pots,active_pot)
    st.pyplot(fig)

elif selected == "Budgets":
    # Update Pots and Vaults values, using class methods
    pots, vaults = refresh_pot_vault_values(pots, vaults)

    # Plot summary chart
    fig = summary(vaults, pots)
    st.pyplot(fig)

    # Generate base DataFrame depending on whether pots exist
    if len(pots) == 0:
        df = pd.DataFrame(
            [
                {
                    "Spend Type": "Daily expenses",
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
    else:
        df_list_of_dicts = []
        for pot in pots.values():
            df_list_of_dicts.append(
                {
                    "Spend Type": "Miscellaneous",  # Map to vaults
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

    # Create session
    if "budget_data" not in st.session_state:
        st.session_state.budget_data = df.copy()

    # create editable table
    edited_df = st.data_editor(
        st.session_state.budget_data,
        num_rows="dynamic",
        disabled=["Pot Balance", "Number of Days"],
        key="budget_editor",
        column_config={
            "Spend Type": st.column_config.SelectboxColumn(
                "Spend Type",
                options=["Daily expenses", "Miscellaneous"],
                default="Daily expenses",
            ),
            "Pot Name": st.column_config.TextColumn("Pot Name"),
            "Pot Budget": st.column_config.NumberColumn("Pot Budget"),
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

        df_calc["Number of Days"] = (
            pd.to_datetime(df_calc["End Date"], errors="coerce")
            - pd.to_datetime(df_calc["Start Date"], errors="coerce")
        ).dt.days

        for i, row in df_calc.iterrows():
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

        # Save
        st.session_state.budget_data = df_calc

        # Display success message
        msg = st.empty()
        msg.success("Calculation Successful")
        sleep(2)
        msg.empty()
        st.rerun()

    # Submit Button
    if st.button("Submit Updates", key="submit_btn"):
        # Save
        final_df = edited_df.dropna(how="all").reset_index(drop=True)
        st.session_state.budget_data = final_df.copy()

        # Display success message
        msg = st.empty()
        msg.success("Transaction submitted")
        sleep(2)
        msg.empty()

        # Add DB submission logic here
        #st.rerun()
    
elif selected == "Transactions":
    # Base data
    if len(transactions) == 0:
        df = pd.DataFrame(
            [
                {
                    "Transaction Name": None,
                    "Date": None,
                    "Pot Name": None,
                    "Amount": None,
                },
            ]
        )
    
    else:
        df_list_of_dicts = []
        pot_names_dict = pot_dict(pots)
        for transaction in transactions.values():
            if transaction.manual_transaction == 0:
                continue
            else:
                dict = {
                "Transaction Name": f"{transaction.transaction_name}",
                "Date": transaction.date.strftime("%d/%m/%y"),
                "Pot Name": f"{pot_names_dict[f"{transaction.pot_id}"]}",
                "Amount": transaction.amount,
                }

                df_list_of_dicts.append(dict)
        
        
        # Re-check as auto transactions aren't displayed
        if len(df_list_of_dicts) == 0:
            df = pd.DataFrame(
                [
                    {
                        "Transaction Name": None,
                        "Date": None,
                        "Pot Name": None,
                        "Amount": None,
                    },
                ]
            )
        
        else:
            df = pd.DataFrame(df_list_of_dicts)
            # Convert date strings
            df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%y").dt.date

    # Track submission
    if "transactions_submitted" not in st.session_state:
        st.session_state.transactions_submitted = False

    if not st.session_state.transactions_submitted:
        st.info(
            "Existing data is read-only. You can delete rows or add new transactions at the bottom."
        )

        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            key="transactions_editor",
            column_config={
                "Transaction Name": st.column_config.TextColumn("Transaction Name"),
                "Date": st.column_config.DateColumn("Date", format="DD/MM/YY"),
                "Pot Name": st.column_config.TextColumn("Pot Name"),
                "Amount": st.column_config.NumberColumn("Amount"),
            },
        )
        
        if st.button("Submit"):
            # Remove completely blank rows
            final_df = edited_df.dropna(how="all").reset_index(drop=True)
            # Display success message
            msg = st.empty()
            msg.success("Transaction submitted")
            sleep(2)
            msg.empty()
            # Submit to database
            pass
            #st.rerun()
            # Update flag
            st.session_state.transactions_submitted = True
            # Submit to session state
            st.session_state.transactions_final = final_df.copy()

    else:
        # Rerender table using session state values
        st.data_editor(
            st.session_state.transactions_final,
            disabled=True,
            key="transactions_final_view",
        )
        
        # Reset flag before rerun
        st.session_state.transactions_submitted = False
    
  
elif selected == "Instructions":
    st.markdown(
    """
    <iframe width="950" height="600" src="https://www.youtube.com/embed/lrfcxQguHVk?si=i2OkK9OduA3l9Tqo" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
    """,
    unsafe_allow_html=True
)

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
