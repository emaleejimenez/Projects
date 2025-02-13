# -*- coding: utf-8 -*-
"""
Created on Fri May 17 10:59:38 2024

@author: ejimenez

"""

import sys
import os
import glob
import pandas as pd
from datetime import datetime
import yfinance as yf

# Define the path to the directory containing scraper.py
desktop_path = 'C:\\MY_FILE_PATH\\13F-HR Scrape\\'

# Add the directory to the system path
sys.path.append(desktop_path)

# Import the scraper module
import scraper

def convert_quarter_to_date(quarter_folder):
    """
    Convert a folder name like '2024Q1' to a date string like '2024-03-31'.
    """
    year, quarter = int(quarter_folder[:4]), int(quarter_folder[5])
    if quarter == 1:
        return f'{year}-03-31'
    elif quarter == 2:
        return f'{year}-06-30'
    elif quarter == 3:
        return f'{year}-09-30'
    elif quarter == 4:
        return f'{year}-12-31'
    return None

def get_stock_price_on_date(ticker, date, value=None, shares=None):
    """
    Get the stock price for a given ticker on or before a specific date using Yahoo Finance.
    If the price does not exist and this is the first known occurrence, calculate it as value / shares.
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period='max')

        # Convert the date to a datetime object and localize to the same timezone as the historical data
        date_obj = pd.to_datetime(date).tz_localize(hist.index.tz)

        # Find the last known price on or before the given date
        if date_obj in hist.index:
            return hist.loc[date_obj]['Close']
        else:
            # Get the closest date before the specified date
            closest_date = hist.index[hist.index <= date_obj].max()
            if pd.notna(closest_date):
                return hist.loc[closest_date]['Close']
            else:
                # Calculate the price as value / shares if it's the first known occurrence
                if shares > 0:
                    calculated_price = value / shares
                    print(f"Calculated price for {ticker} on {date} as {calculated_price:.2f}")
                    return calculated_price
                else:
                    print(f"No price data available for {ticker} before {date} and cannot calculate price as shares are zero.")
                    return None
    except Exception as e:
        print(f"Error fetching price for {ticker} on {date}: {e}")
        return None

def track_changes_in_shares_and_value(company_name, company_folder, pull_historical):
    """
    Track changes in shares and portfolio value over time for a given company.
    """
    # Get all Excel files for the company
    excel_files = glob.glob(os.path.join(company_folder, '**/*.xlsx'), recursive=True)
    
    # Sort files by date
    excel_files = sorted(excel_files, key=lambda x: datetime.strptime(convert_quarter_to_date(os.path.basename(os.path.dirname(x))), "%Y-%m-%d"))

    # DataFrames to store the summaries
    shares_summary_df = pd.DataFrame()
    value_summary_df = pd.DataFrame()

    for file in excel_files:
        filename = os.path.basename(file)
        print(f"Processing {filename}")
        df = pd.read_excel(file, sheet_name='13f')
        folder_name = os.path.basename(os.path.dirname(file))
        date = convert_quarter_to_date(folder_name)
        
        # Get stock prices and calculate value
        df['Price'] = df.apply(lambda row: get_stock_price_on_date(row['SYMBOL'], date, row['Value x1000'], row['Number of Shares']) if pd.notna(row['SYMBOL']) else None, axis=1)
        df['Value'] = df['Price'] * df['Number of Shares']
        
        # Aggregate and summarize
        total_value = df['Value'].sum()
        shares_summary = df.pivot_table(index='SYMBOL', values='Number of Shares', aggfunc='sum').T
        value_summary = df.pivot_table(index='SYMBOL', values='Value', aggfunc='sum').T
        
        shares_summary['Date'] = date
        value_summary['Date'] = date
        value_summary['Total Portfolio'] = total_value
        shares_summary.set_index('Date', inplace=True)
        value_summary.set_index('Date', inplace=True)

        shares_summary_df = pd.concat([shares_summary_df, shares_summary])
        value_summary_df = pd.concat([value_summary_df, value_summary])

    # Calculate changes in shares and value
    change_in_shares_df = shares_summary_df.diff().fillna(0)
    change_in_value_df = value_summary_df.diff().fillna(0)
    change_in_value_df['Total Portfolio'] = value_summary_df['Total Portfolio'].diff().fillna(0)

    # Identify positions that have been closed out
    all_symbols = shares_summary_df.columns
    for symbol in all_symbols:
        for i in range(1, len(shares_summary_df)):
            if shares_summary_df.iloc[i][symbol] == 0 and shares_summary_df.iloc[i-1][symbol] != 0:
                change_in_shares_df.at[shares_summary_df.index[i], symbol] = -shares_summary_df.iloc[i-1][symbol]

    # Organize DataFrames
    shares_summary_df = shares_summary_df.sort_index()
    value_summary_df = value_summary_df.sort_index()
    change_in_shares_df = change_in_shares_df.sort_index()
    change_in_value_df = change_in_value_df.sort_index()

    # Make sure 'Total Portfolio' is the first column in value-related DataFrames
    cols_value = ['Total Portfolio'] + [col for col in value_summary_df.columns if col != 'Total Portfolio']
    value_summary_df = value_summary_df[cols_value]
    change_in_value_df = change_in_value_df[cols_value]

    summary_file = os.path.join(desktop_path+'Portfolio Analysis\\', f"{company_name}_portfolio_summary.xlsx")
    
    if pull_historical == 1: # Pull Full History of all 13F-HRs
        # Create an Excel writer object and save the DataFrames to separate sheets
        with pd.ExcelWriter(summary_file) as writer:
            shares_summary_df.to_excel(writer, sheet_name='Number of Shares')
            value_summary_df.to_excel(writer, sheet_name='Value')
            change_in_shares_df.to_excel(writer, sheet_name='Change in Shares')
            change_in_value_df.to_excel(writer, sheet_name='Change in Value')
        print(f"Saved summary to {summary_file}")
    
    elif pull_historical == 0: # Pull Latest 13F-HR only
        if os.path.exists(summary_file):
            existing_data = pd.ExcelFile(summary_file)
            last_date_in_file = None

            # Check if data is already there by comparing dates
            if 'Number of Shares' in existing_data.sheet_names:
                existing_shares_df = pd.read_excel(summary_file, sheet_name='Number of Shares')
                last_date_in_file = existing_shares_df['Date'].max() if 'Date' in existing_shares_df.columns else None
            
            if last_date_in_file and last_date_in_file >= shares_summary_df.index[-1]:
                print(f"Data for {shares_summary_df.index[-1]} already exists in {summary_file}. Skipping update.")
            else:
                with pd.ExcelWriter(summary_file, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
                    shares_summary_df.iloc[-1:].to_excel(writer, sheet_name='Number of Shares', header=False, startrow=writer.sheets['Number of Shares'].max_row)
                    value_summary_df.iloc[-1:].to_excel(writer, sheet_name='Value', header=False, startrow=writer.sheets['Value'].max_row)
                    change_in_shares_df.iloc[-1:].to_excel(writer, sheet_name='Change in Shares', header=False, startrow=writer.sheets['Change in Shares'].max_row)
                    change_in_value_df.iloc[-1:].to_excel(writer, sheet_name='Change in Value', header=False, startrow=writer.sheets['Change in Value'].max_row)
                print(f"Updated summary file {summary_file} with the latest data.")
        else:
            print(f"Summary file {summary_file} does not exist. Cannot update with the latest data.")

def main_wrapper():
    # Run the scraper to make sure data is up to date
    #scraper.main()
    
    # Load the master list to get company names
    master_list_path = os.path.join(desktop_path, 'master_list.xlsx')
    master_df = pd.read_excel(master_list_path)

    for _, row in master_df.iterrows():
        company_name = row['Company Name']
        pull_historical = row['Pull Historical']
        print(f"Processing {company_name} with Pull Historical = {pull_historical}")
        
        if pull_historical == -1: # Skip this company, no 13F-HRs pulled
            print(f"Skipping {company_name} due to settings.")
            continue
        
        company_folder = os.path.join(desktop_path+'Raw Data\\', company_name)
        
        if os.path.exists(company_folder):
            track_changes_in_shares_and_value(company_name, company_folder, pull_historical)
        else:
            print(f"Folder for {company_name} does not exist.")

if __name__ == "__main__":
    main_wrapper()
