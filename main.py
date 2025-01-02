import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from mftool import Mftool
from datetime import datetime

# Function Definitions


def calc_returns(invested_amount, current_nav, units_hold):
    return (((units_hold * current_nav) - invested_amount) / invested_amount) * 100


def calc_returns_on_today_invest(invested_amount, current_nav, units_hold, suppose_invest_amount):
    buying_units = suppose_invest_amount / current_nav
    units_hold += buying_units
    invested_amount += suppose_invest_amount
    return [(((units_hold * current_nav) - invested_amount) / invested_amount) * 100, units_hold, invested_amount, invested_amount / units_hold]


def find_most_matched_sentence(sentences, keywords):
    max_matches = 0
    best_sentence = None
    best_code = None
    best_original_sentence = None
    

    for code, sentence in sentences:
        ori_sentence = sentence
        sentence = sentence.lower().replace('-', ' ')
        matches = sum(1 for keyword in keywords if keyword.lower() in sentence)
        if matches > max_matches:
            max_matches = matches
            best_sentence = sentence
            best_code = code
            best_original_sentence = ori_sentence

    return best_code, best_sentence,best_original_sentence


def remove_words(string, words_to_remove):
    string = string.lower()
    for word in words_to_remove:
        string = string.replace(word.lower(), '')
    return string.strip()


# Streamlit UI
st.title("Mutual Fund Transaction Analyzer")
st.sidebar.title("Settings")

uploaded_file = st.sidebar.file_uploader("Upload Mutual Fund Transactions (Excel)", type=["xlsx"])

# Date input
start_date = st.sidebar.date_input("Pick a date:",
    value=datetime(2024, 1, 1).date(),  # Default value is today's date
    min_value=datetime(2015, 1, 1).date(),  # Minimum selectable date
    max_value=datetime(2030, 12, 31).date()  # Maximum selectable date
)
# selected_date = st.date_input(
#     "Pick a date:",
#     value=datetime.now().date(),  # Default value is today's date
#     min_value=datetime(2015, 1, 1).date(),  # Minimum selectable date
#     max_value=datetime(2030, 12, 31).date()  # Maximum selectable date
# )

# Display the selected date
st.write("You selected date:", start_date)

if uploaded_file:
    st.success("File uploaded successfully!")
    transaction_df = pd.read_excel(uploaded_file)
    transaction_df['Date'] = pd.to_datetime(transaction_df['Date'], errors='coerce')
    try:
        transaction_df['Amount'] = transaction_df['Amount'].str.replace(',', '').astype(float)
    except:
        pass

    mf = Mftool()

    scheme_code_mapping = {}
    for sn in transaction_df['Scheme Name'].unique():
        trimed_word = remove_words(sn, ['Direct', 'Plan', 'Growth', 'Fund', 'Cap', 'Opportunities'])
        result = mf.get_available_schemes(trimed_word)
        code, most_matched,most_matched_original = find_most_matched_sentence(list(result.items()), ['Direct', 'Plan', 'Growth', 'Fund'])
        if(code == None):
            st.write(sn, 'Code Not Found')
        else:
            scheme_code_mapping[most_matched_original] = code
            transaction_df['Scheme Name'] = transaction_df['Scheme Name'].str.replace(sn, most_matched_original)
    # print(transaction_df)
            
    # start_date = st.sidebar.date_input("Select Start Date", pd.Timestamp("2024-01-01"))
    for mutual_fund_name in scheme_code_mapping.keys():
        mutual_fund_code = scheme_code_mapping[mutual_fund_name]
        transaction_data = transaction_df[transaction_df['Scheme Name'] == mutual_fund_name]

        mf_history_nav_df = mf.get_scheme_historical_nav(mutual_fund_code, as_Dataframe=True).reset_index()
        mf_history_nav_df['nav'] = mf_history_nav_df['nav'].astype(float)
        mf_history_nav_df['date'] = pd.to_datetime(mf_history_nav_df['date'], format='%d-%m-%Y')
        mf_history_nav_df = mf_history_nav_df[mf_history_nav_df['date'] >= pd.to_datetime(start_date)]
        mf_history_nav_df = mf_history_nav_df.sort_values('date').reset_index(drop=True)

        invested_amount = 0
        units_hold = 0
        avg_nav_on_every_transaction = {'date': [], 'name': [], 'avg_nav': []}

        for i, row in transaction_data.iterrows():
            avg_nav_on_every_transaction['date'].append(row['Date'])
            avg_nav_on_every_transaction['name'].append(f"Transaction {i}")
            avg_nav_on_every_transaction['avg_nav'].append(
                calc_returns_on_today_invest(invested_amount, row['NAV'], units_hold, row['Amount'])[3]
            )
            if row['Transaction Type'] == 'PURCHASE':
                invested_amount += row['Amount']
                units_hold += row['Units']
            elif row['Transaction Type'] == 'REDEEM':
                invested_amount -= row['Amount']
                units_hold -= row['Units']
        # print("Current working",mutual_fund_name)
        avg_nav_on_every_transaction_df = pd.DataFrame(avg_nav_on_every_transaction)
        current_nav = mf_history_nav_df.tail(1)['nav'].values[0]
        if(units_hold!=0):
            avg_nav = invested_amount / units_hold
        else:
            st.write("ERROR: Units Hold:", units_hold)

        # Plotting
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=mf_history_nav_df['date'],
                                 y=mf_history_nav_df['nav'], mode='lines', name=mutual_fund_name))
        fig.add_trace(go.Scatter(x=transaction_data['Date'], y=transaction_data['NAV'],
                                 mode='markers', name=f"Transactions", marker=dict(color='red')))
        fig.add_trace(go.Scatter(x=[min(mf_history_nav_df['date']), max(mf_history_nav_df['date'])], y=[
                      current_nav, current_nav], mode='lines', name='Current NAV', line=dict(color='orange', dash='dash')))
        fig.add_trace(go.Scatter(x=[min(mf_history_nav_df['date']), max(mf_history_nav_df['date'])], y=[
                      avg_nav, avg_nav], mode='lines', name='Avg NAV', line=dict(color='blue', dash='dash')))

        # st.write(invested_amount,units_hold,current_nav)
        for amount in range(1000, 20_000, 2000):
            new_avg_nav = calc_returns_on_today_invest(invested_amount,current_nav,units_hold,amount)[3]
            fig.add_trace(go.Scatter(
                x=[min(mf_history_nav_df['date']), max(mf_history_nav_df['date'])],
                y=[new_avg_nav, new_avg_nav],
                mode='lines',
                name='New Avg Nav - If Invest '+ str(amount)+' Rs' ,
                line=dict(color='green' if new_avg_nav<avg_nav else 'red', dash='dash')
            ))
        fig.update_layout(
            legend=dict(
                orientation="h",   # Horizontal legend
                yanchor="bottom",  # Anchor the legend to the bottom of the map
                y=1.1,             # Place the legend above the map
                xanchor="center",  # Center the legend horizontally
                x=0.5              # Center the legend horizontally
            )
        )

        st.plotly_chart(fig)
        st.write("Invested Amount:", invested_amount)
        st.write("Units Hold:", units_hold)
        st.write("Average NAV:", avg_nav)
        st.write("Current NAV:", current_nav)
        st.write("Current Value:", units_hold*current_nav)
        st.write("Returns:", calc_returns(invested_amount, current_nav, units_hold))
