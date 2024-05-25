import csv
import os

input_file = 'tmp_fix.csv'
output_file = 'free_fix.csv'

def transform_tips(tip):
    if tip == '1':
        return 'HT wins'
    elif tip == '2':
        return 'AT wins'
    elif tip == '12':
        return 'Any team to win'
    elif tip == '1X':
        return 'HT wins or draw'
    elif tip == 'X':
        return 'Draw'
    elif tip == 'X2':
        return 'AT wins or draw'
    else:
        return tip

# Read new data from input file and transform it
new_data = []
with open(input_file, mode='r', newline='') as infile:
    reader = csv.reader(infile)
    for row in reader:
        time = row[0]
        league_name = row[2]
        ht = row[3]
        at = row[4]
        tips = row[5]
        odds_tips = row[6]
        status = row[7]
        result = row[8] if len(row) > 8 else ''

        new_row = [
            time,
            league_name,
            f"{ht} vs {at}",
            'Predictions',
            transform_tips(tips),
            odds_tips,
            result,
            '',
            'new'
        ]
        new_data.append(new_row)

# Read existing data from the output file if it exists
existing_data = []
if os.path.exists(output_file):
    with open(output_file, mode='r', newline='') as outfile:
        reader = csv.reader(outfile)
        for row in reader:
            existing_data.append(row)

# Combine new data with existing data
combined_data = new_data + existing_data

# Write the combined data to the output file without headers
with open(output_file, mode='w', newline='') as outfile:
    writer = csv.writer(outfile)
    writer.writerows(combined_data)

print(f"Data transformed and prepended to {output_file} successfully.")
