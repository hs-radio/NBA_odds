import boto3
import pandas as pd
from datetime import datetime
import etl

def lambda_handler(event=None, context=None):

    # Create an S3 client
    s3 = boto3.client('s3')

    # Get the current timestamp and date
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Scrape the data (this is your existing etl process)
    try:
        print_results = False
        games, odds = etl.main(print_results)  # Call the main function from the etl module
        
        # Save data locally to temporary CSV files with timestamp in filename
        games_file_path = f'/tmp/games_{timestamp}.csv'
        odds_file_path = f'/tmp/odds_{timestamp}.csv'
        
        games.to_csv(games_file_path, index=False)  # Save games dataframe as CSV
        odds.to_csv(odds_file_path, index=False)    # Save odds dataframe as CSV

        # Upload CSVs to S3 with timestamp in filename, but grouped in a date-specific folder
        s3.upload_file(games_file_path, 'nba-games-odds-bucket', f'odds_data/{current_date}/games_{timestamp}.csv')
        s3.upload_file(odds_file_path, 'nba-games-odds-bucket', f'odds_data/{current_date}/odds_{timestamp}.csv')

        # Response message
        body_message = f"NBA odds scraped and saved with timestamp {timestamp}."
        response = {"statusCode": 200, "body": body_message}
        return response

    except Exception as e:
        response = {"statusCode": 500, "body": f"Error occurred: {str(e)}"}
        return response
