import argparse
import json
import random
import sys
from typing import Any, List, Mapping

DEFAULT_EXAMPLES = {
    "integer": 777,
    "string": "I'm string",
    "number": 0.198,
    "boolean": True,
    "array": [1, 2, 3, "str", 5],
    "object": {"root": {"child": 10}, "name": "I'm name"},
}

STRING_EXAMPLES_WITH_FORMAT = {
    "date": "2017-07-21",
    "date-time": "2017-07-21T17:32:28Z",
    "byte": "U3dhZ2dlciByb2Nrcw==",
    "binary": "\xDE\xAD\xBE\xEF\xDE\xAD\xBE\xEF",
}


def generate_example_for_string(field_schema: Mapping[str, Any]) -> str:
    """
    Return example value for string field type
    """
    if field_schema.get("enum"):
        # select first enum from the list
        return field_schema["enum"][0]
    elif (
        field_schema.get("format")
        and field_schema["format"] in STRING_EXAMPLES_WITH_FORMAT
    ):
        return STRING_EXAMPLES_WITH_FORMAT[field_schema["format"]]

    return DEFAULT_EXAMPLES["string"]


def generate_example_for_integer(field_schema: Mapping[str, Any]) -> int:
    """
    Return example value for integer field type
    """
    if field_schema.get("minimum") is None and field_schema.get("maximum") is None:
        return DEFAULT_EXAMPLES["integer"]

    default_range = 100
    minimun = field_schema.get("minimum")
    maximum = field_schema.get("maximum")
    if minimun is None:
        minimun = maximum - default_range
    elif maximum is None:
        maximum = minimun + default_range

    return random.randint(minimun, maximum)


def generate_example_for_array(field_schema: Mapping[str, Any]) -> List[Any]:
    """
    Return example value for array field type
    """
    if not field_schema.get("items") or not field_schema["items"].get("type"):
        # use default in case of empty `items` or link to $ref
        return DEFAULT_EXAMPLES[field_schema["type"]]

    return [generate_example(field_schema["items"])]


def generate_example_for_object(field_schema: Mapping[str, Any]) -> Mapping[str, Any]:
    """
    Return example value for object field type
    """
    if not field_schema.get("properties"):
        # free-form object, use default example
        return DEFAULT_EXAMPLES[field_schema["type"]]

    example = {}
    # process nested object
    for property_name in field_schema["properties"]:
        example[property_name] = generate_example(
            field_schema["properties"][property_name]
        )

    return example


def generate_example(field_schema: Mapping[str, Any]) -> Any:
    """
    Construct example for input field. Evaluate nested objects with recursion.
    Can be used for `parameters`, `requestBody`, `responses`, `components`
    """
    if not field_schema.get("type"):
        # ignore $ref schemas
        return

    if field_schema["type"] == "object":
        field_schema["example"] = generate_example_for_object(field_schema)
    elif field_schema["type"] == "array":
        field_schema["example"] = generate_example_for_array(field_schema)
    elif field_schema["type"] == "string":
        field_schema["example"] = generate_example_for_string(field_schema)
    elif field_schema["type"] == "integer":
        field_schema["example"] = generate_example_for_integer(field_schema)
    else:
        field_schema["example"] = DEFAULT_EXAMPLES[field_schema["type"]]

    return field_schema["example"]


def parse_parameters(parameters: Mapping[str, Any]):
    """
    Iterate over endpoint parameters schema
    """
    for param in parameters:
        if param.get("schema"):
            generate_example(param["schema"])


def parse_endpoints(path_data: Mapping[str, Any]):
    """
    Iterate over list of endpoints in given path.
    Detect http methods and common parameters that apply to all methods within endpoint
    """
    for http_method in path_data:
        if http_method == "parameters":
            # check for common parameters for all methods
            parse_parameters(path_data.get("parameters", []))
        else:
            parse_parameters(path_data[http_method].get("parameters", []))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--file",
        help="OpenAPI JSON input file",
        type=argparse.FileType("r"),
    )
    parser.add_argument(
        "-o",
        "--output",
        help="output file name and path",
        type=argparse.FileType("w"),
        default=sys.stdout,
    )
    args = parser.parse_args()

    openapi_spec = json.loads(args.file.read())
    for path in openapi_spec["paths"]:
        parse_endpoints(openapi_spec["paths"][path])

    # write results with populated examples to output file/stdout
    args.output.write(json.dumps(openapi_spec, indent=4))
    args.output.close()


if __name__ == "__main__":
    main()
