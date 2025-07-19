from flask import Flask, render_template, request, json
import fleet_offers
import external_functions
import constants
import pandas as pd

app = Flask(__name__)

def load_json_data(file_path):
    """Loads a JSON file and returns its content."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: The file {file_path} is not a valid JSON file.")
        return None

# Load all pricing and discount data into global variables
print("Loading cloud pricing data...")
config_data = load_json_data('config_file.json')
aws_ec2_data_linux = load_json_data('AWSData/ec2_data_Linux.json')
aws_ec2_data_windows = load_json_data('AWSData/ec2_data_Windows.json')
aws_discount_linux = load_json_data('AWSData/ec2_discount_Linux.json')
aws_discount_windows = load_json_data('AWSData/ec2_discount_Windows.json')
azure_vm_data = load_json_data('AzureData/Azure_data_v2.json')
azure_vm_discount = load_json_data('AzureData/vm_discount.json')
print("Data loading complete.")

# --- End of Optimization Section ---

@app.route('/')
def index():
    """Renders the main input page."""
    # The data is already loaded, so we just render the template.
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    """Handles form submission, runs the optimization, and displays results."""
    if request.method == 'POST':
        # Extract user requirements from the form
        user_requirements = {
            'region': request.form.get('region'),
            'os': request.form.get('os'),
            'vcpu': external_functions.validate_integer(request.form.get('vcpu'), 'vCPU'),
            'memory': external_functions.validate_integer(request.form.get('memory'), 'Memory'),
            'storage': external_functions.validate_integer(request.form.get('storage'), 'Storage'),
            'iops': external_functions.validate_integer(request.form.get('iops'), 'IOPS'),
            'bandwidth': external_functions.validate_integer(request.form.get('bandwidth'), 'Bandwidth'),
            'commitment': request.form.get('commitment', '1'),
            'instances': external_functions.validate_integer(request.form.get('instances'), 'Number of Instances'),
            'utilization': float(request.form.get('utilization', 1.0)),
            'architecture': request.form.get('architecture', 'x86_64'),
            'type': request.form.get('type', 'On-Demand')
        }

        # --- Pass the pre-loaded data to the optimizer ---
        # This avoids reading from disk inside the core logic.
        all_offers = fleet_offers.get_fleet_offers(
            user_requirements,
            config_data,
            aws_ec2_data_linux,
            aws_ec2_data_windows,
            aws_discount_linux,
            aws_discount_windows,
            azure_vm_data,
            azure_vm_discount
        )

        # Save results to a JSON file (optional, but can be useful for debugging)
        with open('fleet_results.json', 'w') as f:
            json.dump(all_offers, f, indent=4)

        # Prepare data for rendering in the template
        if not all_offers:
            return "No suitable instance combinations found for the given requirements."

        # Sort offers by total price
        sorted_offers = sorted(all_offers, key=lambda x: x['total_price'])
        best_offer = sorted_offers[0] if sorted_offers else None

        # Convert fleet composition to a pandas DataFrame for easier rendering in HTML
        for offer in sorted_offers:
            if 'fleet_composition' in offer:
                df = pd.DataFrame(offer['fleet_composition'])
                # Ensure consistent column order
                cols = ['provider', 'instance_type', 'vcpu', 'memory', 'storage', 'price', 'billing_type']
                df = df[cols]
                offer['composition_table'] = df.to_html(classes='min-w-full bg-white border', index=False)

        return render_template('result.html', fleet_offers=sorted_offers, best_offer=best_offer)

if __name__ == '__main__':
    app.run(debug=True)
