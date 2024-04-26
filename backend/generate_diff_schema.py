import os
import json
from pathlib import Path
from json_template import JsonTemplates

def deep_delete_key(obj, key_to_delete):
    if key_to_delete in obj:
        del obj[key_to_delete]
    return obj

def delete_unused_key(data, key_to_delete):
    return list(filter(lambda x: x['type'] not in key_to_delete, data))

def generate_schema():
    file_path = Path(f"./schema/transformed_components")
    output_path = Path(f"./schema/transformed_components_for_diff")
    
    json_files = [pos_json for pos_json in os.listdir(file_path) if pos_json.endswith('.json')]
    
    for js in json_files:
        with open(file_path / js, 'r') as f:
            data = json.load(f)

        # Get the 'const' value from 'definitions' -> 'ComponentInfo' -> 'properties' -> 'name'
        const_value = data.get('definitions', {}).get('ComponentInfo', {}).get('properties', {}).get('name', {}).get('const', '')

        # If 'const' value is not found, continue with the next file
        if not const_value:
            continue

        filtered_data = filter_json(data)

        # Use the 'const' value for the output file name
        output_file = f"{const_value}.json"

        with open(output_path / output_file, 'w') as f:
            json.dump(filtered_data, f, ensure_ascii=False, indent=4)


def filter_json(obj):
    if isinstance(obj, dict):
        filtered_dict = {k: filter_json(v) for k, v in obj.items() if isinstance(v, (dict, list))}
        filtered_dict = {k: v for k, v in filtered_dict.items() if v}  # Remove empty dictionaries and lists
        if not filtered_dict and not any(k in obj for k in ['title', 'description', '$ref', 'name']):
            return None
        filtered_dict.update((k, v) for k, v in obj.items() if k in ['title', 'description', '$ref', 'name'])
        return filtered_dict
    elif isinstance(obj, list):
        filtered_list = [filter_json(x) for x in obj]
        filtered_list = [v for v in filtered_list if v is not None]  # Remove items that do not contain 'title', 'description', or '$ref'
        if not filtered_list or not any(isinstance(v, dict) and any(k in v for k in ['title', 'description', '$ref', 'name']) for v in filtered_list):
            return None
        return filtered_list
    elif isinstance(obj, str):
        return obj if obj in ['title', 'description', '$ref'] else None  # Remove strings that are not 'title', 'description', or '$ref'
    else:
        return obj


if __name__ == "__main__":
    generate_schema()