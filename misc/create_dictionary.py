# Script to read data from 'fader_data_struct.txt' and create a dictionary

def create_dictionary_from_file(file_path):
    data_dict = {}

    with open(file_path, 'r', encoding='utf-8') as file:
        line_number = 0
        for line in file:
            line_number += 1
            # Strip leading/trailing whitespace and skip empty lines
            line = line.strip()
            if not line:
                print(f"Skipping empty line at {line_number}")
                continue

            # Split the line by whitespace
            parts = line.split()
            if len(parts) == 4:
                fader_index, float_value, float_hex, node_value = parts
                try:
                    # Attempt to convert float_value to a float and add to the dictionary
                    float_value = float(float_value)
                    data_dict[node_value] = float_value
                except ValueError as e:
                    print(f"Skipping line {line_number} due to conversion error: {e}")
                    print(f"Problematic line: {line}")
            else:
                print(f"Skipping line {line_number} due to unexpected format: {line}")

    return data_dict

# Specify the path to your file
file_path = 'fader data struct.txt'

# Create the dictionary
result_dict = create_dictionary_from_file(file_path)

# Print the result dictionary
print(result_dict)

# Optionally, save the dictionary to a file
import json
with open('output_dictionary.json', 'w', encoding='utf-8') as json_file:
    json.dump(result_dict, json_file, indent=4, ensure_ascii=False)
