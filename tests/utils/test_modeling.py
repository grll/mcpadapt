"""
Tests for the modeling module, specifically focused on JSON Schema handling.
"""

import warnings

from mcpadapt.utils.modeling import create_model_from_json_schema


def test_direct_modeling_with_list_type():
    """
    Test the modeling module directly with a schema using list-type notation.
    This test is specifically designed to verify handling of list-type JSON Schema fields.
    """
    # Create a schema with list-type field
    schema = {
        "type": "object",
        "properties": {
            "multi_type_field": {
                "type": ["string", "number"],
                "description": "Field that accepts multiple types",
            },
            "nullable_field": {
                "type": ["string", "null"],
                "description": "Field that is nullable",
            },
        },
    }

    # Create model from schema - should not raise TypeError
    model = create_model_from_json_schema(schema)

    # Verify the model works as expected with string
    instance = model(multi_type_field="test")
    assert instance.multi_type_field == "test"

    # Verify the model works as expected with number
    instance = model(multi_type_field=42)
    assert instance.multi_type_field == 42


def test_model_creation_does_not_pass_invalid_field_keywords():
    """Field() should not receive JSON-schema-only keys as kwargs."""

    schema = {
        "type": "object",
        "properties": {
            "nullable_field": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "null"},
                ],
                "description": "field allowing strings or null",
            },
            "array_field": {
                "type": "array",
                "items": {"type": "string"},
                "description": "array of strings",
            },
            "status": {
                "type": "string",
                "enum": ["ok", "error", "unknown"],
                "description": "status enum",
            },
            "payload": {
                "type": "object",
                "properties": {
                    "value": {"type": "string"},
                },
                "description": "nested object payload",
            },
        },
        "required": ["status"],
    }

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        model = create_model_from_json_schema(schema)
        model_instance = model(
            nullable_field=None,
            array_field=["one", "two"],
            status="ok",
            payload={"value": "x"},
        )

    deprecation_warnings = [
        warning
        for warning in captured
        if issubclass(warning.category, DeprecationWarning)
        and "Field" in str(warning.message)
    ]
    assert not deprecation_warnings
    assert model_instance.status == "ok"
    assert model_instance.array_field == ["one", "two"]
    assert model_instance.payload == {"value": "x"}
