import pandas as pd
import boto3
import os
from glob import glob
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

nba_utc_offsets = {
    "Atlanta Hawks": -5,
    "Boston Celtics": -5,
    "Brooklyn Nets": -5,
    "Charlotte Hornets": -5,
    "Chicago Bulls": -6,
    "Cleveland Cavaliers": -5,
    "Dallas Mavericks": -6,
    "Denver Nuggets": -7,
    "Golden State Warriors": -8,  # Golden State is based in San Francisco
    "Houston Rockets": -6,
    "Indiana Pacers": -5,
    "Los Angeles Lakers": -8,
    "Memphis Grizzlies": -6,
    "Miami Heat": -5,
    "Milwaukee Bucks": -6,
    "Minnesota Timberwolves": -6,
    "New Orleans Pelicans": -6,
    "New York Knicks": -5,
    "Oklahoma City Thunder": -6,
    "Orlando Magic": -5,
    "Philadelphia 76ers": -5,
    "Phoenix Suns": -7,
    "Portland Trail Blazers": -8,
    "Sacramento Kings": -8,
    "San Antonio Spurs": -6,
    "Toronto Raptors": -5,
    "Utah Jazz": -7,
    "Washington Wizards": -5
}



def download_s3_data():
    # ---- Config ----
    bucket_name = 'nba-games-odds-bucket'
    prefix = 'odds_data/'  # Change if needed
    download_dir = 'downloaded_files'  # Local directory to store CSVs
    
    # ---- Setup ----
    s3 = boto3.client('s3')
    os.makedirs(download_dir, exist_ok=True)
    
    # ---- List and download all CSV files ----
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
    
    downloaded_files = []
    
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                if key.endswith('.csv'):
                    local_filename = os.path.join(download_dir, os.path.basename(key))
                    # print(f"Downloading: {key} -> {local_filename}")
                    s3.download_file(bucket_name, key, local_filename)
                    downloaded_files.append(local_filename)
    
    print(f"\nDownloaded {len(downloaded_files)} files to: {download_dir}")

def combine_data():
    # ---- Config ----
    download_dir = 'downloaded_files'  # or your chosen directory
    
    # ---- Helper function ----
    def combine_csv_files(pattern):
        csv_files = glob(os.path.join(download_dir, pattern))
        combined_df = pd.concat([pd.read_csv(f) for f in csv_files], ignore_index=True)
        return combined_df
    
    # ---- Combine games and odds files ----
    games_df = combine_csv_files("games_*.csv").drop_duplicates()
    odds_df = combine_csv_files("odds_*.csv").drop_duplicates()
    
    # ---- Output (optional) ----
    print(f"Combined games shape: {games_df.shape}")
    print(f"Combined odds shape: {odds_df.shape}")
    return games_df, odds_df






# looks at the data and computes what the optimal betting strategy would have been
def find_middle_strategy(game_info, game_odds, start_time, T):
    # Filter out odds recorded after the game start
    pre_game_odds = game_odds[game_odds['DateTime'] < start_time]

    # Find row with maximum AwayOdds before start time
    max_away_row = pre_game_odds.loc[pre_game_odds['AwayOdds'].idxmax()]
    away_time = max_away_row['DateTime']
    away_max_odds = max_away_row['AwayOdds']
    
    # Find row with maximum HomeOdds before start time
    max_home_row = pre_game_odds.loc[pre_game_odds['HomeOdds'].idxmax()]
    home_time = max_home_row['DateTime']
    home_max_odds = max_home_row['HomeOdds']

    P = home_max_odds  / away_max_odds 
    b1 = P * T / (1 + P)
    b2 = T - b1
    profit = b1 * (away_max_odds - 1) - b2


    # Return the result as a dictionary
    return {
        'away_time': away_time,
        'home_time': home_time,
        'away_max_odds': away_max_odds,
        'home_max_odds': home_max_odds,
        'b1': b1,
        'b2': b2,
        'profit': profit
    }




    





def fix_datetime(game_id, games_df, odds_df):
       # ---- Game information ----
    game_info = games_df[games_df['GameID'] == game_id].iloc[0]
    home_team = game_info['HomeTeam']
    start_time_syd = pd.to_timedelta(game_info['StartTime'])

    # ---- Filter for the selected game ----
    game_odds = odds_df[odds_df['GameID'] == game_id].copy()

    # ---- Convert 'Time' column to datetime if not already ----
    # Assuming 'StartDate' is in the format 'YYYY-MM-DD HH:MM:SS'
    base_date = pd.to_datetime(game_info['StartDate']).normalize()  # Get the base date, no time part
    
    # Convert 'Time' column to timedelta
    time_delta = pd.to_timedelta(game_odds['Time'])
    
    # Calculate the date by adding the timedelta to the base_date
    home_team_offset = nba_utc_offsets.get(home_team)
    game_odds['DateTime'] = base_date + time_delta - pd.Timedelta(days=1) + pd.Timedelta(hours=home_team_offset)
    start_time = base_date + start_time_syd + pd.Timedelta(hours=home_team_offset) - pd.Timedelta(hours=10)
    
    # ---- Detect first time after midnight ----
    for i in range(1, len(game_odds)):
        if game_odds.iloc[i]['Time'] < game_odds.iloc[i-1]['Time']:
            game_odds.iloc[i:, game_odds.columns.get_loc('DateTime')] += pd.Timedelta(days=1)
            break

    return game_info, game_odds, start_time





# ---- Function to plot odds data ----
def plot_odds_data(game_info, game_odds, start_time, away_max_dt, home_max_dt):

    # get required data
    home_team = game_info['HomeTeam']
    away_team = game_info['AwayTeam']
            
    # ---- Plot ----
    plt.figure(figsize=(10, 5))
    plt.plot(game_odds['DateTime'], game_odds['HomeOdds'], label=f'{home_team}', marker='o')
    plt.plot(game_odds['DateTime'], game_odds['AwayOdds'], label=f'{away_team}', marker='o')
    plt.xlabel('Time')
    plt.ylabel('Odds')
    plt.title(f'{away_team} @ {home_team}')
    
    # Plot the vertical line at the adjusted start time
    plt.axvline(x=start_time, color='k', linestyle='-', label='Game Start')
    
    # Plot vertical lines for maximum Away and Home odds times
    plt.axvline(x=away_max_dt, color='r', linestyle='--', label=f'best odds: {away_team}')
    plt.axvline(x=home_max_dt, color='r', linestyle='-.', label=f'best odds: {home_team}')

    # Add legend for the vertical lines
    plt.legend()

    # Enable grid
    plt.grid(True)

    # Format x-axis to show only time (not date)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    # Show every 4th tick (adjust as necessary)
    xticks = game_odds['DateTime'].iloc[::4]
    plt.xticks(xticks, rotation=45)

    # Ensure layout is tight
    plt.tight_layout()
    plt.savefig("nba_odds_plot.png", format='png')
    plt.show()



