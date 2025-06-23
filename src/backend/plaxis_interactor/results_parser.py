"""
Parses output files or API responses from PLAXIS to extract results.
PRD Ref: Task 3.8
"""

from ..models import AnalysisResults # Relative import
from typing import List, Dict, Any, Optional
import csv # For example if PLAXIS outputs CSV

def parse_load_penetration_curve(output_file_path: Optional[str] = None, raw_api_data: Optional[Any] = None) -> Optional[List[Dict[str, float]]]:
    """
    Parses data to extract load-penetration curve points.
    This is a STUB. It needs to handle actual PLAXIS output format (text file, CSV, API object).

    Args:
        output_file_path: Path to the file containing curve data (e.g., a CSV or text file).
        raw_api_data: Direct data object from PLAXIS API if that's the source.

    Returns:
        A list of dictionaries, e.g., [{'penetration': val, 'load': val}, ...], or None if parsing fails.
    """
    curve_data: List[Dict[str, float]] = []
    print(f"Parsing load-penetration curve from file '{output_file_path}' or API data: {raw_api_data is not None}.")

    if output_file_path:
        try:
            with open(output_file_path, 'r', newline='') as f:
                # Attempt to sniff CSV dialect, or assume standard comma-separated
                # dialect = csv.Sniffer().sniff(f.read(1024))
                # f.seek(0)
                # reader = csv.DictReader(f, dialect=dialect)

                # For simplicity, assume comma delimiter and common headers.
                # Actual PLAXIS output might be space-delimited or fixed-width.
                # Headers might be like "Displacement-z (m)", "Force-z (kN)"
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    print(f"Warning: File '{output_file_path}' is empty or has no header.")
                    return None

                # Try to find relevant column indices (case-insensitive partial match)
                pen_idx, load_idx = -1, -1
                for i, col_name in enumerate(header):
                    col_lower = col_name.lower()
                    if ("pen" in col_lower or "disp" in col_lower or "uz" in col_lower) and pen_idx == -1 : # Prioritize 'pen'
                        pen_idx = i
                    if ("load" in col_lower or "force" in col_lower or "fz" in col_lower or "sumfz" in col_lower) and load_idx == -1: # Prioritize 'load'
                        load_idx = i

                if pen_idx == -1 or load_idx == -1:
                    print(f"Warning: Could not determine penetration/load columns from header in '{output_file_path}': {header}")
                    return None # Or try default indices if desperate

                for row_num, row_values in enumerate(reader):
                    if len(row_values) <= max(pen_idx, load_idx):
                        print(f"Warning: Skipping malformed row {row_num+1} in '{output_file_path}': {row_values}")
                        continue
                    try:
                        penetration = float(row_values[pen_idx])
                        load = float(row_values[load_idx])
                        curve_data.append({"penetration": abs(penetration), "load": abs(load)}) # Assuming positive values are typical for plots
                    except (ValueError, TypeError) as e:
                        print(f"Warning: Skipping row {row_num+1} in '{output_file_path}' due to data conversion error: {row_values} - {e}")
                        continue

            if not curve_data:
                 print(f"Warning: No valid data rows parsed from '{output_file_path}'.")
                 return None
            print(f"Successfully parsed {len(curve_data)} points from file '{output_file_path}'.")
            return curve_data
        except FileNotFoundError:
            print(f"Error: Output file '{output_file_path}' not found for load-penetration curve.")
            return None
        except Exception as e: # Catch other CSV errors or IO errors
            print(f"Error reading or parsing CSV file '{output_file_path}': {e}")
            return None

    elif raw_api_data:
        # This part is highly dependent on how the PLAXIS API (g_o object) returns curve data.
        # It might be a list of tuples, a list of objects, etc.
        # Example: if g_o.getcurveresults returns a list of (x,y) tuples
        # if isinstance(raw_api_data, list) and all(isinstance(item, tuple) and len(item) == 2 for item in raw_api_data):
        #     for pen, load_val in raw_api_data:
        #         curve_data.append({"penetration": float(pen), "load": float(load_val)})
        #     print(f"Successfully parsed {len(curve_data)} points from API data.")
        #     return curve_data
        print("STUB: Parsing load-penetration curve from raw_api_data is not yet fully implemented. Requires PLAXIS Output API knowledge.")
        # Fallback to stub data for conceptual flow
        return [{"penetration": 0.0, "load": 0.0}, {"penetration": 0.1, "load": 100.0}]

    else:
        print("Error: No data source (file path or API data) provided for load-penetration curve.")
        return None


def parse_final_penetration(curve_data: Optional[List[Dict[str, float]]] = None, raw_api_data: Optional[Any] = None) -> Optional[float]:
    """
    Extracts the final penetration depth, typically from load-penetration curve data or direct API result.
    Args:
        curve_data: Parsed load-penetration curve data.
        raw_api_data: Direct data object from PLAXIS API (e.g., a specific result query).
    Returns:
        The final penetration depth as a float, or None if not found.
    """
    print(f"Parsing final penetration depth from curve data or API data: {raw_api_data is not None}.")
    if curve_data and len(curve_data) > 0:
        # Assuming the last point in the curve data represents the final state
        final_pen = curve_data[-1].get("penetration")
        if final_pen is not None:
            print(f"Extracted final penetration from curve data: {final_pen}")
            return float(final_pen)

    elif raw_api_data:
        # Example: if API directly returns the value
        # if isinstance(raw_api_data, (float, int)): return float(raw_api_data)
        # if isinstance(raw_api_data, dict): return float(raw_api_data.get('final_penetration_Uz')) # Hypothetical
        print("STUB: Parsing final penetration from raw_api_data is not yet fully implemented.")
        return 0.5 # Stub value for now

    print("Warning: Could not determine final penetration depth.")
    return None


def parse_peak_resistance(curve_data: Optional[List[Dict[str, float]]] = None, raw_api_data: Optional[Any] = None) -> Optional[float]:
    """
    Extracts the peak vertical resistance, typically from load-penetration curve data or direct API result.
    Args:
        curve_data: Parsed load-penetration curve data.
        raw_api_data: Direct data object from PLAXIS API.
    Returns:
        The peak resistance as a float, or None if not found.
    """
    print(f"Parsing peak resistance from curve data or API data: {raw_api_data is not None}.")
    if curve_data and len(curve_data) > 0:
        max_load = 0.0
        try:
            # Find the maximum load value in the curve
            max_load = max(item.get("load", 0.0) for item in curve_data)
            print(f"Extracted peak resistance from curve data: {max_load}")
            return float(max_load)
        except (TypeError, ValueError) as e:
            print(f"Error processing curve data for peak resistance: {e}")

    elif raw_api_data:
        # Example: if API directly returns the value
        # if isinstance(raw_api_data, (float, int)): return float(raw_api_data)
        # if isinstance(raw_api_data, dict): return float(raw_api_data.get('max_load_Fz')) # Hypothetical
        print("STUB: Parsing peak resistance from raw_api_data is not yet fully implemented.")
        return 1200.75 # Stub value for now

    print("Warning: Could not determine peak resistance.")
    return None

# TODO: Add more parsers as needed for other results specified in PRD 4.1.6
# For example, if PLAXIS can output specific text files for summary results:
# def parse_summary_file(file_path: str) -> Dict[str, Any]:
#     summary = {}
#     try:
#         with open(file_path, 'r') as f:
#             for line in f:
#                 if ":" in line:
#                     key, value = line.split(":", 1)
#                     try:
#                         summary[key.strip()] = float(value.strip())
#                     except ValueError:
#                         summary[key.strip()] = value.strip()
#         return summary
#     except FileNotFoundError:
#         print(f"Error: Summary file '{file_path}' not found.")
#         return {}
#     except Exception as e:
#         print(f"Error parsing summary file '{file_path}': {e}")
#         return {}

if __name__ == '__main__':
    print("--- Testing Results Parser ---")

    # Create a dummy CSV file for load-penetration curve
    dummy_csv_path = "dummy_load_pen_curve.csv"
    with open(dummy_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["penetration", "load"]) # Header
        writer.writerow([0.0, 0.0])
        writer.writerow([0.1, 150.5])
        writer.writerow([0.2, 350.0])
        writer.writerow([0.3, 500.25])

    print("\nTesting parse_load_penetration_curve from CSV:")
    curve = parse_load_penetration_curve(output_file_path=dummy_csv_path)
    if curve:
        print(f"Parsed curve data ({len(curve)} points): {curve[:2]}...") # Print first 2 points
        assert len(curve) == 4
        assert curve[1]["load"] == 150.5
    else:
        print("Failed to parse dummy CSV.")

    import os
    if os.path.exists(dummy_csv_path):
        os.remove(dummy_csv_path)

    print("\nTesting parse_load_penetration_curve with no source:")
    no_source_curve = parse_load_penetration_curve()
    if no_source_curve is None:
        print("PASS: No source handled correctly.")
    else:
        print(f"FAIL: Expected None, got {no_source_curve}")

    print("\nTesting parse_load_penetration_curve with API data (stubbed path):")
    api_curve = parse_load_penetration_curve(raw_api_data="dummy_api_object_placeholder")
    if api_curve:
        print(f"Parsed API curve data (stubbed): {api_curve}")
    else:
        print("Failed to parse API curve data.")


    print("\nTesting parse_final_penetration (stub):")
    pen = parse_final_penetration()
    print(f"Parsed final penetration (stub): {pen}")
    assert pen == 0.5

    print("\nTesting parse_peak_resistance (stub):")
    res = parse_peak_resistance()
    print(f"Parsed peak resistance (stub): {res}")
    assert res == 1200.75

    print("--- End of Results Parser Tests ---")
