import csv
import os

input_file = 'tmp_fix.csv'
free_fix_file = 'free_fix.csv'
pre_fix_file = 'pre_fix.csv'

def transform_tips(tip, ht, at):
    if tip == '1':
        return f'{ht} wins'
    elif tip == '2':
        return f'{at} wins'
    elif tip == '12':
        return 'Any team to win'
    elif tip == '1X':
        return f'{ht} wins or draw'
    elif tip == 'X':
        return 'Draw'
    elif tip == 'X2':
        return f'{at} wins or draw'
    else:
        return tip

# Read new data from input file and transform it
new_data_free_fix = []
new_data_pre_fix = []

with open(input_file, mode='r', newline='') as infile:
    reader = csv.reader(infile)
    for row in reader:
        if not row:  # Skip empty rows if any
            continue
        time = row[0]
        league_name = row[2]
        ht = row[3]
        at = row[4]
        tips = row[5]
        try:
            odds_tips = float(row[6])
        except ValueError:
            odds_tips = 0.0  # Default to 0.0 if conversion fails
        status = row[7]
        result = row[8] if len(row) > 8 else ''

        new_row = [
            time,
            league_name,
            f"{ht} vs {at}",
            'Predictions',
            transform_tips(tips, ht, at),
            odds_tips,
            '-',
            '-',
            'now'
        ]

        if odds_tips < 1.5 and len(new_data_free_fix) < 5:
            new_data_free_fix.append(new_row)
        elif odds_tips >= 1.5 and len(new_data_pre_fix) < 5:
            new_data_pre_fix.append(new_row)

# Read existing data from the output files if they exist
existing_data_free_fix = []
existing_data_pre_fix = []

if os.path.exists(free_fix_file):
    with open(free_fix_file, mode='r', newline='') as outfile:
        reader = csv.reader(outfile)
        existing_data_free_fix = list(reader)

if os.path.exists(pre_fix_file):
    with open(pre_fix_file, mode='r', newline='') as outfile:
        reader = csv.reader(outfile)
        existing_data_pre_fix = list(reader)

# Combine new data with existing data
combined_data_free_fix = new_data_free_fix + existing_data_free_fix
combined_data_pre_fix = new_data_pre_fix + existing_data_pre_fix

# Write the combined data to the output files without headers
with open(free_fix_file, mode='w', newline='') as outfile:
    writer = csv.writer(outfile)
    writer.writerows(combined_data_free_fix)

with open(pre_fix_file, mode='w', newline='') as outfile:
    writer = csv.writer(outfile)
    writer.writerows(combined_data_pre_fix)

print(f"Data transformed and appended to {free_fix_file} and {pre_fix_file} successfully.")
