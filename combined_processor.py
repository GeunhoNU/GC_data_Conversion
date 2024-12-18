import os
import pandas as pd
from natsort import natsorted
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def extract_and_validate_peak_table(file_path, peak_table='Ch1'):
    try:
        with open(file_path, 'r', encoding='ISO-8859-1') as file:
            lines = file.readlines()
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return pd.DataFrame(columns=['R.Time', 'Area', 'Height'])

    section_header = f"[Peak Table ({peak_table})]"
    start_index = next((i for i, line in enumerate(lines) if section_header in line), None)

    if start_index is None:
        logging.warning(f"Section {section_header} not found in {file_path}.")
        return pd.DataFrame(columns=['R.Time', 'Area', 'Height'])

    header_line = lines[start_index + 2].strip().split("\t")
    relevant_columns = ['R.Time', 'Area', 'Height']
    column_indices = {col: header_line.index(col) for col in relevant_columns if col in header_line}

    missing_columns = set(relevant_columns) - set(column_indices.keys())
    if missing_columns:
        logging.warning(f"Missing columns {missing_columns} in file {file_path}.")
        return pd.DataFrame(columns=relevant_columns)

    extracted_data = []
    for line in lines[start_index + 3:]:
        if not line.strip():
            break
        row = line.strip().split("\t")
        extracted_data.append({col: row[idx] for col, idx in column_indices.items()})

    return pd.DataFrame(extracted_data)


def process_and_separate_files_naturally_sorted(folder_path, output_csv, peak_table='Ch1'):
    try:
        sorted_files = natsorted(
            [f for f in os.listdir(folder_path) if f.lower().endswith('.txt') and os.path.isfile(os.path.join(folder_path, f))]
        )
        if not sorted_files:
            logging.warning(f"No .txt files found in folder {folder_path}.")
            return

        with open(output_csv, 'w') as output_file:
            header_written = False
            for filename in sorted_files:
                file_path = os.path.join(folder_path, filename)
                logging.info(f"Processing {filename}...")

                df = extract_and_validate_peak_table(file_path, peak_table)
                if not df.empty:
                    output_file.write(f"Source File: {filename}\n")
                    if not header_written:
                        df.to_csv(output_file, index=False)
                        header_written = True
                    else:
                        df.to_csv(output_file, index=False, header=False)
                    output_file.write("\n")

        logging.info(f"Combined data with file separators saved to {output_csv}")

    except Exception as e:
        logging.error(f"Error processing files: {e}")


def process_and_filter_file(input_file, target_r_times, tolerance, output_file):
    """
    Filters rows from a combined CSV file based on R.Time values,
    ensuring the source file name is written only once for each set of data.

    :param input_file: Path to the input CSV file with source file separators.
    :param target_r_times: List of target R.Time values to filter around.
    :param tolerance: Tolerance range for filtering.
    :param output_file: Path to save the filtered CSV.
    """
    try:
        with open(input_file, 'r') as file:
            lines = file.readlines()

        current_source_file = None
        filtered_data = []

        for line in lines:
            stripped_line = line.strip()

            if stripped_line.startswith("Source File:"):
                current_source_file = stripped_line.split(": ", 1)[1]
            elif stripped_line and current_source_file:
                columns = stripped_line.split(",")
                if len(columns) >= 3:
                    try:
                        r_time = float(columns[0])  # R.Time should be the first column
                        area = columns[1]          # Area (2nd column)
                        height = columns[2]        # Height (3rd column)

                        if any(target - tolerance <= r_time <= target + tolerance for target in target_r_times):
                            filtered_data.append((current_source_file, [r_time, area, height]))

                    except ValueError:
                        continue

        if not filtered_data:
            print("No data matched the filtering criteria.")
            return

        # Save filtered data to the output file
        with open(output_file, 'w') as output_file:
            output_file.write("Source File,R.Time,Area,Height\n")  # Add header
            previous_source_file = None
            for source_file, data_row in filtered_data:
                # Write the source file name only if it changes
                if source_file != previous_source_file:
                    output_file.write(f"{source_file},,,\n")
                    previous_source_file = source_file

                # Write the data row
                output_file.write(f",{','.join(map(str, data_row))}\n")

        print(f"Filtered data saved to: {output_file.name}")

    except Exception as e:
        logging.error(f"Error processing and filtering files: {e}")