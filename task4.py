import argparse
import ast
import sys

examples_variable = "DEFAULT_EXAMPLES"
string_formats_variable = "STRING_EXAMPLES_WITH_FORMAT"
input_file_name = "./task3.py"


def parse_node(node: ast.AST):
    """
    Recursively iterate over variable node and update strings
    """
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            # modify original str
            node.value = f"{node.value} v2"

    elif isinstance(node, ast.Dict):
        for child in node.values:
            parse_node(child)

    elif isinstance(node, ast.List):
        for child in node.elts:
            parse_node(child)


def filter_abstract_synax_tree(root: ast.AST):
    """
    Select only `Assign` nodes and search for variables specific for openapi examples
    """
    assignment_nodes = [node for node in ast.walk(root) if isinstance(node, ast.Assign)]
    for node in assignment_nodes:
        # filter out Subscript nodes
        variable_names = [t.id for t in node.targets if isinstance(t, ast.Name)]

        if examples_variable in variable_names:
            parse_node(node.value)
        elif string_formats_variable in variable_names:
            parse_node(node.value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o",
        "--output",
        help="output file name and path",
        type=argparse.FileType("w"),
        default=sys.stdout,
    )
    args = parser.parse_args()

    task3_file = open(input_file_name, "r")
    root = ast.parse(task3_file.read())
    filter_abstract_synax_tree(root)

    args.output.write(ast.unparse(root))
    args.output.close()


if __name__ == "__main__":
    main()
