from copy import deepcopy
from typing import Any, Dict, ForwardRef, List, Optional, Type, Union
from pydantic import BaseModel, Field, create_model
import re

json_type_mapping: dict[str, Type] = {
    "string": str,
    "number": float,
    "integer": int,
    "boolean": bool,
    "object": dict,
    "array": list,
}


def resolve_refs_and_remove_defs(json_obj):
    # Extract $defs
    defs = json_obj.get("$defs", {})

    # Function to recursively resolve $ref
    def _resolve(obj):
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_path = obj["$ref"]
                match = re.match(r"#/\$defs/(\w+)", ref_path)
                if match:
                    def_key = match.group(1)
                    return _resolve(deepcopy(defs.get(def_key, {})))
            return {k: _resolve(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_resolve(i) for i in obj]
        else:
            return obj

    json_obj = _resolve(json_obj)

    # Remove $defs
    json_obj.pop("$defs", None)

    return json_obj


def create_model_from_json_schema(
    schema: dict[str, Any], model_name: str = "DynamicModel"
) -> Type[BaseModel]:
    """Create a Pydantic model from a JSON schema definition."""
    # Store created models to handle references
    created_models: dict[str, Type[BaseModel]] = {}
    forward_refs: dict[str, ForwardRef] = {}

    def process_schema(name: str, schema_def: Dict[str, Any]) -> Type[BaseModel]:
        """Process a schema definition and create a model."""
        if name in created_models:
            return created_models[name]

        # Create forward reference for recursive schemas
        if name not in forward_refs:
            forward_refs[name] = ForwardRef(name)

        # Build fields for the model
        fields = {}
        properties = schema_def.get("properties", {})
        required = set(schema_def.get("required", []))

        for field_name, field_schema in properties.items():
            field_type, default = get_field_type(field_name, field_schema, required)
            fields[field_name] = (
                field_type,
                Field(
                    default=default,
                    description=field_schema.get("description", ""),
                    title=field_schema.get("title", ""),
                    items=field_schema.get("items", None),
                    anyOf=field_schema.get("anyOf", []),
                    enum=field_schema.get("enum", None),
                    properties=field_schema.get("properties", {}),
                ),
            )

        # Create the model
        model = create_model(
            schema_def.get("title", name),
            __doc__=schema_def.get("description", ""),
            **fields,  # type: ignore
        )

        created_models[name] = model
        return model

    def get_field_type(field_name: str, field_schema: Dict[str, Any], required: set):
        """Determine field type and default value."""
        # Handle references
        if "$ref" in field_schema:
            ref_parts = field_schema["$ref"].lstrip("#/").split("/")
            ref_name = ref_parts[-1]

            # Get or create referenced model
            if ref_name not in created_models:
                ref_schema = schema
                for part in ref_parts:
                    ref_schema = ref_schema.get(part, {})
                process_schema(ref_name, ref_schema)

            field_type = created_models[ref_name]
            is_required = field_name in required
            return (
                Optional[field_type] if not is_required else field_type,  # type: ignore
                None if not is_required else ...,
            )

        # Handle anyOf
        if "anyOf" in field_schema:
            is_nullable = any(
                opt.get("type") == "null" for opt in field_schema["anyOf"]
            )
            types = []

            for option in field_schema["anyOf"]:
                if "type" in option and option["type"] != "null":
                    types.append(json_type_mapping.get(option["type"], Any))
                elif "enum" in option:
                    types.append(str)
                elif "$ref" in option:
                    ref_parts = option["$ref"].lstrip("#/").split("/")
                    ref_name = ref_parts[-1]

                    if ref_name not in created_models:
                        ref_schema = schema
                        for part in ref_parts:
                            ref_schema = ref_schema.get(part, {})
                        process_schema(ref_name, ref_schema)

                    types.append(created_models[ref_name])

            field_type = types[0] if len(types) == 1 else Union[tuple(types)]  # type: ignore
            default = field_schema.get("default")
            is_required = field_name in required and default is None

            if is_nullable and not is_required:
                field_type = Optional[field_type]  # type: ignore

            return field_type, ... if is_required else default

        # Handle arrays
        if field_schema.get("type") == "array" and "items" in field_schema:
            item_type, _ = get_field_type("item", field_schema["items"], set())
            field_type = List[item_type]  # type: ignore
        else:
            # Simple types
            json_type = field_schema.get("type", "string")

            # Handle list-type (multiple allowed types in JSON Schema)
            if isinstance(json_type, list):
                # Convert to Union type (consistent with anyOf handling)
                types = []
                for t in json_type:
                    if t != "null":  # Exclude null types as in anyOf handling
                        mapped_type = json_type_mapping.get(t, Any)
                        types.append(mapped_type)

                if len(types) > 1:
                    field_type = Union[tuple(types)]  # type: ignore
                else:
                    field_type = types[0] if types else Any
            else:
                # Original code for simple types
                field_type = json_type_mapping.get(json_type, Any)  # type: ignore

        # Handle optionality and default values
        default = field_schema.get("default")
        is_required = field_name in required and default is None

        if not is_required:
            field_type = Optional[field_type]  # type: ignore
            default = default if default is not None else None
        else:
            default = ...

        return field_type, default

    # Create models for definitions
    if "$defs" in schema:
        for def_name, def_schema in schema["$defs"].items():
            process_schema(def_name, def_schema)

    # Create the root model
    root_model = process_schema(model_name, schema)

    return root_model
