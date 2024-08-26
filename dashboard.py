import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px

# Load the CSV file into a DataFrame
df = pd.read_csv('pre_fix.csv', header=None)
df.columns = ['Date', 'League', 'Home vs Away', 'Match Info', 'Prediction', 'Odds', 'Match Result', 'Win/Lose', 'Match Status']

# Convert the 'Date' column to datetime format, allowing for mixed formats
df['Date'] = pd.to_datetime(df['Date'], errors='coerce', utc=True)
df = df.dropna(subset=['Date'])

# Convert 'Win/Lose' column to integers
df['Win/Lose'] = df['Win/Lose'].astype(int)

# Calculate metrics
total_bets = len(df)
total_wins = df['Win/Lose'].sum()
total_losses = total_bets - total_wins
winning_rate = (total_wins / total_bets) * 100
losing_rate = (total_losses / total_bets) * 100
average_odds = df['Odds'].mean()
total_days = df['Date'].dt.normalize().nunique()
bets_per_day = total_bets / total_days
total_profit = (df['Win/Lose'] * df['Odds'] * 100).sum() - total_bets * 100
yield_per_bet = (total_profit / (total_bets * 100)) * 100
roi = (total_profit / (total_bets * 100)) * 100
return_all = total_profit
return_day = return_all / total_days
total_months = df['Date'].dt.to_period('M').nunique()
return_monthly = return_all / total_months

# Static Visualization with Matplotlib and Seaborn
plt.figure(figsize=(18, 10))

# Pie chart for winning/losing rates
plt.subplot(2, 2, 1)
plt.pie([winning_rate, losing_rate], labels=['Wins', 'Losses'], autopct='%1.1f%%', colors=['#66b3ff','#ff9999'])
plt.title('Winning vs Losing Rate')

# Bar graph for return metrics
plt.subplot(2, 2, 2)
sns.barplot(x=['Yield per Bet', 'ROI', 'Return (Day)', 'Return (Monthly)'], y=[yield_per_bet, roi, return_day, return_monthly], palette='viridis')
plt.title('Return Metrics')
plt.ylabel('Value in $')

# Bar graph for overall statistics
plt.subplot(2, 2, 3)
sns.barplot(x=['Total Bets', 'Total Wins', 'Total Losses', 'Bets per Day'], y=[total_bets, total_wins, total_losses, bets_per_day], palette='magma')
plt.title('Overall Betting Statistics')

# Bar graph for financial metrics
plt.subplot(2, 2, 4)
sns.barplot(x=['Total Profit', 'Average Odds'], y=[total_profit, average_odds], palette='plasma')
plt.title('Financial Metrics')
plt.ylabel('Value')

plt.tight_layout()
plt.show()

# Interactive Dashboard with Plotly
fig1 = px.pie(values=[winning_rate, losing_rate], names=['Wins', 'Losses'], title='Winning vs Losing Rate')
fig1.show()

fig2 = px.bar(x=['Yield per Bet', 'ROI', 'Return (Day)', 'Return (Monthly)'], y=[yield_per_bet, roi, return_day, return_monthly], title='Return Metrics', labels={'x': 'Metrics', 'y': 'Value in $'})
fig2.show()

fig3 = px.bar(x=['Total Bets', 'Total Wins', 'Total Losses', 'Bets per Day'], y=[total_bets, total_wins, total_losses, bets_per_day], title='Overall Betting Statistics', labels={'x': 'Statistics', 'y': 'Value'})
fig3.show()

fig4 = px.bar(x=['Total Profit', 'Average Odds'], y=[total_profit, average_odds], title='Financial Metrics', labels={'x': 'Metrics', 'y': 'Value'})
fig4.show()
