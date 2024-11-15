import os
import traceback
import gspread
import csv
import matplotlib.pyplot as plt
import pandas as pd
from google.oauth2.service_account import Credentials
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

# Define the path to your service account credentials JSON file
SERVICE_ACCOUNT_FILE = 'creds1.json'

# Define the scope required for accessing Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Directory for storing images and PDF
OUTPUT_DIR = 'output_files'

# Authenticate with Google Sheets API
def authenticate_google_sheets():
    try:
        credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        print(f"Authentication failed: {e}")
        return None

# Fetch data from Google Sheets
def fetch_google_sheet_data(sheet_id, sheet_name):
    try:
        # Authenticate the Google Sheets client
        client = authenticate_google_sheets()
        if not client:
            raise RuntimeError("Google Sheets client authentication failed.")
        
        try:
            # Open the Google Sheet by ID and access the specified sheet name
            sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
        except gspread.SpreadsheetNotFound:
            raise ValueError(f"Google Sheet with ID '{sheet_id}' not found. Check the ID.")
        except gspread.WorksheetNotFound:
            raise ValueError(f"Worksheet '{sheet_name}' not found in the sheet. Check the sheet name.")

        # Fetch all rows as a list of dictionaries
        data = sheet.get_all_records()
        
        if not data:
            print("The sheet is empty or contains no records.")
        else:
            print("Fetched data from the sheet:")
            print(data)
        
        return data

    except FileNotFoundError:
        print(f"Service account credentials file not found. Ensure the path is correct: {SERVICE_ACCOUNT_FILE}")
    except gspread.exceptions.APIError as api_error:
        print(f"Google Sheets API returned an error: {api_error}")
    except ValueError as value_error:
        print(f"Value Error: {value_error}")
    except RuntimeError as runtime_error:
        print(f"Runtime Error: {runtime_error}")
    except Exception as e:
        print("An unexpected error occurred:")
        traceback.print_exc()
    
    # Return None if any exception occurs
    return None

# Save the data to a CSV file
def save_to_csv(data, filename="sheet_data.csv"):
    if data:
        try:
            # Ensure the output directory exists
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            # Writing to a CSV file
            with open(filepath, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=data[0].keys())
                writer.writeheader()  # Write the header row
                writer.writerows(data)  # Write the data rows
            print(f"Data has been successfully saved to {filepath}.")
        except Exception as e:
            print(f"An error occurred while saving to CSV: {e}")
    else:
        print("No data to save to CSV.")

# Plot graphs dynamically based on the fields in the data and group by the DATE field
def plot_graphs(data):
    try:
        if not data:
            print("No data available to plot.")
            return
        
        # Convert the data into a pandas DataFrame
        df = pd.DataFrame(data)

        # Ensure that 'DATE' column is in datetime format
        if 'DATE' in df.columns:
            df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')

            # Group the data by 'DATE' and compute the mean for each group
            grouped_df = df.groupby(df['DATE'].dt.date).mean(numeric_only=True)  # Only numeric columns

            # Iterate over the columns and plot graphs for numerical fields
            for column in grouped_df.columns:
                try:
                    # Plotting a simple line graph for grouped data
                    if grouped_df[column].isnull().sum() == 0:  # Only plot if data is not null
                        plt.figure(figsize=(10, 6))
                        grouped_df[column].plot(kind='line', title=f"Graph of {column} grouped by DATE")
                        plt.xlabel('Date')
                        plt.ylabel(column)
                        plt.grid(True)

                        # Ensure the output directory exists
                        os.makedirs(OUTPUT_DIR, exist_ok=True)
                        image_filename = os.path.join(OUTPUT_DIR, f'{column}_grouped_by_date_plot.png')
                        plt.savefig(image_filename)
                        plt.close()
                    else:
                        print(f"Skipping column '{column}' due to invalid or missing values.")
                except Exception as e:
                    print(f"Error plotting {column}: {e}")
        else:
            print("No 'DATE' field found in the data.")

    except Exception as e:
        print(f"Error generating plots: {e}")

# Generate PDF report with the graphs (this will generate even if graphs aren't plotted)
def generate_pdf_report(pdf_filename="report.pdf"):
    try:
        # Ensure the output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        pdf_filepath = os.path.join(OUTPUT_DIR, pdf_filename)
        
        c = canvas.Canvas(pdf_filepath, pagesize=letter)
        c.setFont("Helvetica", 12)

        # Title for the PDF
        c.drawString(100, 750, "Google Sheets Data Report")

        # Add a note if no graphs are generated
        y_position = 730
        graphs_generated = False

        for column in ["Column1", "Column2"]:  # Replace with actual column names or dynamically add images
            try:
                image_filename = os.path.join(OUTPUT_DIR, f"{column}_plot.png")
                c.drawImage(image_filename, 100, y_position, width=400, height=300)
                y_position -= 310  # Adjust the position for the next plot
                graphs_generated = True
            except Exception as e:
                print(f"Skipping image for {column} due to error: {e}")
        
        if not graphs_generated:
            c.drawString(100, y_position, "No graphs were generated. Data is available in the sheet.")

        # Save the PDF
        c.save()
        print(f"PDF report saved as {pdf_filepath}")
    
    except Exception as e:
        print(f"Error generating PDF: {e}")

# Test with your Google Sheets ID and Sheet Name
SHEET_ID = "14Lw2-WIOPPFJaogMSrgm7SBrqszW84ZuZwjEvzYSblI"
SHEET_NAME = "Sheet1"  # Replace with your sheet name

if __name__ == "__main__":
    data = fetch_google_sheet_data(SHEET_ID, SHEET_NAME)
    if data:
        save_to_csv(data)
        plot_graphs(data)  # Attempt to generate plots
        generate_pdf_report()  # Generate the PDF report regardless of plotting success
