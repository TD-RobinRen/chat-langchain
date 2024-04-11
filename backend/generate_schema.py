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
    file_path = Path(f"./schema/studio_components")
    output_path = Path(f"./schema/transformed_components")
    
    json_files = [pos_json for pos_json in os.listdir(file_path) if pos_json.endswith('.json')]

    json_tmp = JsonTemplates()

    original_component_schema = json.loads(Path(f"./template/step_schema.json").read_text())
    
    for js in enumerate(json_files):
        loader = json_tmp.loads(json.dumps(original_component_schema))

        source_file = json.loads(file_path.joinpath(js[1]).read_text(), object_hook=lambda d: deep_delete_key(d, "_ui_"))

        default_exits = delete_unused_key(source_file['default_exits'], ['invisible']) if 'default_exits' in source_file else []
        custom_exits = source_file['custom_exits'] if 'custom_exits' in source_file else {}
        
        exit_schema = generate_exit_schema(default_exits, custom_exits)

        if loader[0]:
            version = source_file['version']
            major_minor_version = '.'.join(version.split('.')[:2])

            result = json_tmp.generate({
                "properties": source_file['properties'],
                "name": source_file['name'],
                "version": f"{major_minor_version}.x",
                "exits": exit_schema
            })
        with open(output_path.joinpath(js[1]), 'w+', encoding='utf-8') as file:
            json.dump(result[1], file, indent=2)
        
def generate_exit_schema(default_exits, custom_exits):
    exit_schema = []
    
    for [i, exit] in enumerate(default_exits):
        json_tmp = JsonTemplates()
        if 'condition' in exit:
            json_tmp.loads(json.dumps(json.loads(Path(f"./template/exit_with_condition_schema.json").read_text())))
            exit_schema.append(
                json_tmp.generate({
                    "exit_name": exit['name'],
                    "condition": exit['condition'],
                    "title": exit["title"] if 'title' in exit else "",
                    "description": exit["description"] if 'description' in exit else ""
                })[1]
            )
        else:
            json_tmp.loads(json.dumps(json.loads(Path(f"./template/exit_schema.json").read_text())))
            exit_schema.append(
                json_tmp.generate({
                    "exit_name": exit['name'],
                    "title": exit["title"],
                    "description": exit["description"]
                })[1]
            )

    if custom_exits:
        json_tmp = JsonTemplates()
        if 'condition' in custom_exits:
            json_tmp.loads(json.dumps(json.loads(Path(f"./template/custom_exit_with_condition_schema.json").read_text())))
            exit_schema.append(
                json_tmp.generate({
                    "condition": custom_exits['condition'],
                    "title": custom_exits["title"] if 'title' in custom_exits else "",
                    "description": custom_exits["description"] if 'description' in custom_exits else ""
                })[1]
            )
        else:
            json_tmp.loads(json.dumps(json.loads(Path(f"./template/custom_exit_schema.json").read_text())))
            exit_schema.append(
                json_tmp.generate({
                    "title": custom_exits["title"],
                    "description": custom_exits["description"]
                })[1]
            )

    return exit_schema
    

if __name__ == "__main__":
    generate_schema()