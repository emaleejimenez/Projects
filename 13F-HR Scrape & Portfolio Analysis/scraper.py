# -*- coding: utf-8 -*-
"""
Created on Tue Apr 30 10:19:28 2024

@author: ejimenez


Getting current and historical 13f-HR data from all CIKs within master list and 
putting them in their respective folders according to company name and filing date

Possible Adds:
    - PowerBI dashboard of analytics

"""

import requests
import pandas as pd
import time
import json
import os
from datetime import datetime
import re
from xml.etree import ElementTree as ET
import fnmatch

# Headers need to be declared in order for the SEC API to allow a connection
headers = {'User-Agent': "jimenezemalee@gmail.com",
			"Accept-Encoding": "gzip, deflate" }

fname = 'xml_13f'
desktop_path = 'C:\\MY_FILE_PATH\\13F-HR Scrape\\' 
cusip_to_ticker_file = os.path.join(desktop_path, 'cusip_to_ticker.xlsx')

# Check if output directory exists. if not, then create it
pExists = os.path.exists(desktop_path)
if not pExists:
	os.makedirs(desktop_path)
	print('Created output folder here: ' + desktop_path)
	print()
    
# Load ticker mapping
def load_ticker_mapping():
    tickermapping = pd.read_excel(cusip_to_ticker_file)[['CUSIP', 'SYMBOL', 'DESCRIPTION']]
    tickermapping['SYMBOL'] = tickermapping['SYMBOL'].astype(str)
    tickermapping['CUSIP'] = tickermapping['CUSIP'].astype(str).str.zfill(9)  # Pad CUSIPs to 9 characters
    tickermapping = tickermapping.drop_duplicates(subset='CUSIP', keep='first')
    tickermapping = tickermapping.set_index(['CUSIP'])
    return tickermapping
    
# Takes in a text filename that should contain xml
# XML within text file is then parsed and saved as an xml file containing only the 13F-HR filing
def extractXML(fname):
	f = open(fname + '.txt', 'r')
	lines = f.readlines()
	linenum = 0
	end_at = 0
	# String to designate the start of the 13F filing
	f13 = 'edgar/document/thirteenf/informationtable'

	for x in lines:
		if x.find(f13) != -1:
			linenum = lines.index(x)
			for k in lines[linenum:]:
				# Looks for the closing xml tag in order to properly end the file
				if fnmatch.fnmatch(k, '</*informationTable*'):
					xml_end = lines[linenum:].index(k)
					end_at = xml_end + linenum
					# Exit the for loop once the marker for the end of file is found
					break

	# Range of lines. need to parse the xml and extract values
	xml_13f = lines[linenum:end_at+1]
	f.close()

	# Write the new 13F xml file, overwriting whatever was present before
	# Overwriting is done to prevent buildup of past files
	with open(fname + '.xml', 'w') as fi:
		for j in xml_13f:
			fi.write(j)

# Read the xml file from the text file version of the 13f-HR filing
def parseXML(xmlfname):
	tree = ET.parse(xmlfname +'.xml')
	root = tree.getroot()
	finalList = []

	for child in root:
		tempList = []
		for leaf in child:
            
			if 'nameOfIssuer' in leaf.tag or 'cusip' in leaf.tag or 'value' in leaf.tag or 'titleOfClass' in leaf.tag:
				tempList.append(leaf.text)

			if 'shrsOrPrnAmt' in leaf.tag:
				for x in leaf:
					if 'sshPrnamt' in x.tag:
						tempList.append(x.text)
		finalList.append(tempList)

	return finalList

# Takes 13F filing info as a list, the CIK IF of the company, filing date of the 13F and the company name
# Outputs to an excel file on the desktop
def previous_quarter(ref_date):
    if ref_date.month < 4:
        return datetime(ref_date.year - 1, 12, 31)
    elif ref_date.month < 7:
        return datetime(ref_date.year, 3, 31)
    elif ref_date.month < 10:
        return datetime(ref_date.year, 6, 30)
    return datetime(ref_date.year, 9, 30)

def output_to_excel(myList, cik, filing_date, company, tickermapping):
    securitiesDF = pd.DataFrame(myList)
    securitiesDF = securitiesDF.rename(columns={0: 'Security', 1: 'Title of Class', 2: 'CUSIP', 3: 'Value x1000', 4: 'Number of Shares', 5: 'Share or Principal Type'})

    # Convert filing_date to datetime object to calculate the correct quarter
    filing_datetime = datetime.strptime(filing_date, "%Y-%m-%d")
    prev_quarter_date = previous_quarter(filing_datetime)
    year = prev_quarter_date.year
    quarter = (prev_quarter_date.month - 1) // 3 + 1
    quarter_folder = f"{year}Q{quarter}"

    filename = company + '_13F_' + filing_date + '.xlsx'

    # Check if the company folder exists, if not, create it
    company_folder_path = os.path.join(desktop_path+'Raw Data\\', company)
    if not os.path.exists(company_folder_path):
        os.makedirs(company_folder_path)
        print(f"Created folder for {company} at {company_folder_path}")

    # Check if the quarter folder exists within the company folder, if not, create it
    quarter_folder_path = os.path.join(company_folder_path, quarter_folder)
    if not os.path.exists(quarter_folder_path):
        os.makedirs(quarter_folder_path)
        print(f"Created quarter folder {quarter_folder} at {quarter_folder_path}")

    # Set the export path inside the company-specific and quarter-specific folder
    export_path = os.path.join(quarter_folder_path, filename)

    # Add SYMBOL column based on CUSIP
    securitiesDF['CUSIP'] = securitiesDF['CUSIP'].astype(str).str.zfill(9)
    securitiesDF = securitiesDF.set_index('CUSIP')
    securitiesDF = securitiesDF.join(tickermapping, how='left')
    securitiesDF = securitiesDF.reset_index()

    securitiesDF.to_excel(export_path, sheet_name='13f', index=False)
    return export_path

# Retreive 13f-HR filing from the SEC API and save the text file version of the filing
# Saving the text version because the naming is standardized
# CIK ID is the 10 digit CIK number with leading zeros plus "CIK"
def getPayload(cik):
    # Converting to uppercase and removing any leading or trailing spaces
    cik = cik.upper().strip()
    if cik.startswith('CIK') and len(cik) == 13:
        # No formatting to be done
        pass
    elif cik.startswith('CIK') and len(cik) < 13:
        cik = cik.replace('CIK', '')
        cik = 'CIK' + cik.zfill(10)
    elif cik.startswith('CIK') and len(cik) > 13:
        raise Exception("Invalid CIK number")
    elif not cik.startswith('CIK') and len(cik) <= 10:
        cik = 'CIK' + cik.zfill(10)
    elif not cik.startswith('CIK') and len(cik) > 10:
        raise Exception("Invalid CIK number")
    else:
        raise Exception("Invalid CIK number")
    
    # Formatting the CIK number in order to search archives
    cik_num = cik.replace('CIK', '')
    cik_num = cik_num.lstrip('0')
    
    url = "https://data.sec.gov/submissions/" + cik + ".json"
    
    response = requests.get(url, headers=headers).json()
    time.sleep(1)
    
    # Extract company name and format it to remove special characters
    company_name = response["name"]
    company_name_formatted = re.sub(r'[\\/*?:"<>|]', "", company_name).replace(",", "").replace("'", "").replace(".", "").replace(" ", "_")
    
    # Filter Data for 13-F-HR forms
    filings = response["filings"]["recent"]
    filings_df = pd.DataFrame(filings)
    filings_df = filings_df[filings_df.form == "13F-HR"]
    
    if filings_df.empty:
        print(f"There are no 13F-HR forms for {company_name}")

    all_filings_info = []
    
    for index, row in filings_df.iterrows():
        access_number_unformatted = row['accessionNumber']
        access_number = access_number_unformatted.replace("-", "")
        file_name = access_number_unformatted + ".txt"
        file_url = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{access_number}/{file_name}"
        req_content = requests.get(file_url, headers=headers).content.decode("utf-8")
        
        # Retrieve the filing date
        filing_date = row['filingDate']
        
        # Prepare data for output
        filing_info = {
            'content': req_content,
            'filing_date': filing_date,
            'company_name_formatted': company_name_formatted
        }
        all_filings_info.append(filing_info)
    
    return all_filings_info

# Main Program
def main():
    # Load the Excel file into a DataFrame
    ciks_path = 'Z:\\WIT Market Research & Projects\\Portfolio Management Team\\Adhoc Projects\\13F-HR Scrape\\master_list.xlsx'
    ciks_df = pd.read_excel(ciks_path, 'Sheet1')
    
    # Make sure there is a column for the most recent filing date
    if 'Most Recent Filing' not in ciks_df.columns:
        ciks_df['Most Recent Filing'] = pd.NaT  # Initializes the column with Not-a-Time (NaT)
    
    tickermapping = load_ticker_mapping()
    
    for i, row in ciks_df.iterrows():
        print(f"\n\nPulling Data for {row['Company Name']}\n\n")
        cik = row['CIK']
        company_name = row['Company Name']
        pull_historical = row['Pull Historical']
        
        if pull_historical == -1:
            print(f"Skipping data pull for {row['Company Name']} due to settings.")
            continue  # Skip to the next iteration of the loop
        
        time.sleep(2)
        try:
            # Get all filings for the CIK
            all_filings = getPayload(cik)
            if not all_filings:
                continue
            
            all_filings = sorted(all_filings, key=lambda x: datetime.strptime(x['filing_date'], "%Y-%m-%d"), reverse=True)
            
            # Conditionally truncate all_filings based on pull_historical
            if pull_historical == 0:
                all_filings = [all_filings[0]]  # Keep only the first filing
            elif pull_historical == 1:
                all_filings = all_filings  # Keep all filings
                
            # Update the most recent filing date in the DataFrame
            most_recent_date = all_filings[0]['filing_date']
            ciks_df.at[i, 'Most Recent Filing'] = most_recent_date
            
            for filing in all_filings:
                filing_date = filing['filing_date']
                print('Filing for ' + company_name + ' found from ' + filing_date + '\n')
                
                # Process each filing
                with open(desktop_path + 'Raw Data\\' + fname + ".txt", "w") as f:
                    f.write(filing['content'])
    
                # Extract and parse XML from the text file
                extractXML(desktop_path + 'Raw Data\\' + fname)
                myList = parseXML(desktop_path + 'Raw Data\\' + fname)
    
                # Output the data to an Excel file
                output_path = output_to_excel(myList, cik, filing_date, company_name, tickermapping)
                print('Saving excel file to ' + output_path)
        
        except Exception as e:
            print('')
            print(e)
            print('Error retrieving or processing data for CIK ' + cik)
            print('')
            continue
    
    # Save the updated DataFrame back to the Excel file
    ciks_df.to_excel(ciks_path, index=False)
    print('Updated the original Excel file with the most recent filing dates.')
