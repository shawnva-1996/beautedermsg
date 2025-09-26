import os
import json
from bs4 import BeautifulSoup
import pandas as pd
import re

def parse_product_details(description_html):
    """
    Parses the HTML content within the description to extract structured details
    like Benefits, Ingredients, How To Use, etc.
    """
    if not description_html:
        return {}

    desc_soup = BeautifulSoup(description_html, 'html.parser')
    details_sections = {}

    # Extract the main description text that comes before the detailed sections
    main_description = desc_soup.find('p')
    details_sections['description'] = main_description.get_text(separator=' ', strip=True) if main_description else ''

    # Extract content from <details> tags which hold structured information
    for details_tag in desc_soup.find_all('details'):
        summary = details_tag.find('summary')
        if not summary:
            continue

        # Use the headline span as the section title, e.g., "Benefits", "Ingredients"
        headline_span = summary.find('span', class_='headline')
        headline = headline_span.get_text(strip=True).lower().replace(' ', '_') if headline_span else 'general_details'
        
        content_div = details_tag.find('div', class_='indent-content')
        if content_div:
            # Join all text elements within the content section for a clean output
            texts = [element.get_text(separator=' ', strip=True) for element in content_div.find_all(['p', 'li', 'h3', 'h4', 'h5', 'h6'])]
            details_sections[headline] = '\n'.join(texts).strip()
            
    return details_sections


def parse_html_file(file_content):
    """Parses a single HTML file's content to extract all product data."""
    soup = BeautifulSoup(file_content, 'html.parser')
    products_list = []
    
    # Each product is contained within a <li class="productgrid--item"> tag
    product_items = soup.find_all('li', class_='productgrid--item')

    for item in product_items:
        script_tag = item.find('script', type='application/json', attrs={'data-product-data': ''})
        if not script_tag:
            continue

        try:
            # The product data is stored as a JSON object inside the script tag
            product_json = json.loads(script_tag.string)
            
            # Extract basic product information
            product_id = product_json.get('id')
            title = product_json.get('title')
            handle = product_json.get('handle')
            product_url = f"https://beautederm.sg/collections/all/products/{handle}"
            price = product_json.get('price', 0) / 100.0  # Price is in cents, convert to dollars
            is_available = product_json.get('available', False)
            
            # Extract structured details from the description HTML
            parsed_details = parse_product_details(product_json.get('description'))

            # Consolidate all extracted data into a single dictionary
            product_info = {
                'product_id': product_id,
                'title': title,
                'price ($)': f"{price:.2f}",
                'stock_status': 'In Stock' if is_available else 'Sold Out',
                'product_type': product_json.get('type'),
                'vendor': product_json.get('vendor'),
                'tags': ', '.join(product_json.get('tags', [])),
                'description': parsed_details.get('description'),
                'benefits': parsed_details.get('benefits'),
                'how_to_use': parsed_details.get('how_to_use', parsed_details.get('directions_for_use')),
                'ingredients': parsed_details.get('ingredients'),
                'specifications': parsed_details.get('details', parsed_details.get('specification')),
                'care_instructions': parsed_details.get('care'),
                'inclusions': parsed_details.get('inclusions'),
                'product_url': product_url,
                'primary_image_url': product_json.get('featured_image'),
            }
            products_list.append(product_info)

        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Skipping an item due to a parsing error: {e}")
            continue
            
    return products_list

def main():
    """Processes all HTML files in the directory and saves the output to a CSV file."""
    # List of HTML files to process
    html_files = [
        'body_care.html', 'face_care_1.html', 'face_care_2.html', 
        'health_wellness.html', 'home_care.html', 'makeup.html', 'mens_care.html'
    ]
    
    all_products = []
    processed_ids = set()

    print("Starting product extraction...")
    for filename in html_files:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                print(f"Processing '{filename}'...")
                content = f.read()
                products_from_file = parse_html_file(content)
                
                # Add products only if they haven't been seen before
                for product in products_from_file:
                    if product['product_id'] not in processed_ids:
                        all_products.append(product)
                        processed_ids.add(product['product_id'])
        except FileNotFoundError:
            print(f"Error: File not found -> '{filename}'. Please ensure it is in the same directory.")
        except Exception as e:
            print(f"An unexpected error occurred while processing {filename}: {e}")

    if not all_products:
        print("No products were extracted. Please check the HTML files.")
        return

    # Convert the list of product dictionaries to a Pandas DataFrame
    df = pd.DataFrame(all_products)
    
    # Define a logical order for the columns in the final CSV
    column_order = [
        'product_id', 'title', 'price ($)', 'stock_status', 'product_type', 
        'vendor', 'tags', 'description', 'benefits', 'how_to_use', 
        'ingredients', 'specifications', 'inclusions', 'care_instructions', 
        'product_url', 'primary_image_url'
    ]
    # Reorder DataFrame columns, including only those that were actually found
    df = df.reindex(columns=[col for col in column_order if col in df.columns])

    output_filename = 'beautederm_products.csv'
    try:
        df.to_csv(output_filename, index=False, encoding='utf-8')
        print(f"\n✅ Success! Extracted {len(df)} unique products.")
        print(f"Data has been saved to '{output_filename}'")
    except Exception as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    main()