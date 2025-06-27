import pandas as pd
import os

# Path to the folder containing the sample files
DATA_DIR = '/Users/venkatakhil95/Downloads/Sample Snapshot'

# Filenames
INVENTORY_FILE = os.path.join(DATA_DIR, 'inventory_data.csv')
ORDERS_FILE = os.path.join(DATA_DIR, 'open_order_data.csv')

# Output files
STOCKOUTS_FILE = os.path.join(DATA_DIR, 'current_stockouts.csv')
SHORTED_ORDERS_FILE = os.path.join(DATA_DIR, 'shorted_orders.csv')

# Read inventory and orders
inventory = pd.read_csv(INVENTORY_FILE)
orders = pd.read_csv(ORDERS_FILE)

# Clean column names for easier access
inventory.columns = [c.strip().lower().replace(' ', '_') for c in inventory.columns]
orders.columns = [c.strip().lower().replace(' ', '_') for c in orders.columns]

# Prepare inventory dict: {sku: qty_on_hand}
sku_inventory = {row['sku']: row['qty_on_hand'] for _, row in inventory.iterrows()}

# Sort orders by late_ship_date (ascending), then by order_id for stability
orders['late_ship_date'] = pd.to_datetime(orders['late_ship_date'])
orders = orders.sort_values(['sku', 'late_ship_date', 'order_id'])

# Track stockouts and shorted orders
stockouts = []
shorted_orders = []

# For each SKU, process orders in late_ship_date order
for sku in orders['sku'].unique():
    inv = sku_inventory.get(sku, 0)
    sku_orders = orders[orders['sku'] == sku].copy()
    for idx, order in sku_orders.iterrows():
        qty_needed = order['qty_ordered']
        if inv >= qty_needed:
            inv -= qty_needed
        else:
            short_qty = qty_needed - inv
            shorted_orders.append({
                'order_id': order['order_id'],
                'sku': sku,
                'qty_ordered': qty_needed,
                'qty_fulfilled': max(inv, 0),
                'qty_shorted': short_qty,
                'late_ship_date': order['late_ship_date'].date(),
                'site': order.get('site', ''),
            })
            inv = 0
    # If inventory is 0 after processing, it's a stockout
    if inv == 0:
        stockouts.append({
            'sku': sku,
            'final_qty_on_hand': inv,
            'site': inventory[inventory['sku'] == sku]['site'].iloc[0],
        })

# Save results
stockouts_df = pd.DataFrame(stockouts)
shorted_orders_df = pd.DataFrame(shorted_orders)

stockouts_df.to_csv(STOCKOUTS_FILE, index=False)
shorted_orders_df.to_csv(SHORTED_ORDERS_FILE, index=False)

print(f"current_stockouts saved to {STOCKOUTS_FILE}")
print(f"shorted_orders saved to {SHORTED_ORDERS_FILE}") 