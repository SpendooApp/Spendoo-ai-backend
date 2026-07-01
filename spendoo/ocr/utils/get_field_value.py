def get_field_value(field):
    
    if not field:
        return None
    if field.type == "string":
        return field.value_string
    elif field.type == "array":
        return [get_field_value(item) for item in (field.value_array or [])]
    elif field.type == "object":
        return {k: get_field_value(v) for k, v in (field.value_object or {}).items()}
    elif field.type == "number":
        return field.value_number
    elif field.type == "integer":
        return field.value_integer
    return field.content


def format_response(result):
    
    extracted_json = {} 

    if result.documents:
        for document in result.documents:
            for field_name, field in document.fields.items():
                extracted_json[field_name] = get_field_value(field)

    clean_items = []

    if "Items" in extracted_json and extracted_json["Items"]:
        for item in extracted_json["Items"]:
            clean_item = {
                "name": item.get("Description"),
                "total_price": item.get("TotalPrice") if item.get("TotalPrice") is not None else item.get("Price"),
            }
            clean_items.append(clean_item)

    filtered_response = {
        "items": clean_items,
        "total": extracted_json.get("Total")
    }
    
    return filtered_response