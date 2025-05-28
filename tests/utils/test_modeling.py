"""
Tests for the modeling module, specifically focused on JSON Schema handling.
"""

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
