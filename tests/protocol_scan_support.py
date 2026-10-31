"""Derive consumed protocol tags from actual interpreter comparisons, not a tag list."""

import ast


def key(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def receiver(node):
    return (
        node.id
        if isinstance(node, ast.Name)
        else node.attr if isinstance(node, ast.Attribute) else None
    )


def values(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [(node.value, node)]
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return [value for item in node.elts for value in values(item)]
    return []


def consumption(tree):
    consumed = {name: set() for name in ("levels", "shapes", "roles", "semantic_roles")}
    heading_keys, heading_dispatch, dispatched_nodes = set(), set(), set()
    fields = {"level": "levels", "shape": "shapes", "role": "roles"}
    scopes = [
        node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    for scope in scopes:
        aliases = {}

        def domain(node):
            if isinstance(node, ast.Subscript):
                return fields.get(key(node.slice))
            return aliases.get(node.id) if isinstance(node, ast.Name) else None

        for node in ast.walk(scope):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        aliases[target.id] = domain(node.value)
            if isinstance(node, ast.Subscript):
                name = receiver(node.value)
                if name in {"semantic", "child_roles"} and key(node.slice):
                    consumed["semantic_roles"].add(key(node.slice))
                if name == "heading_roles" and key(node.slice):
                    heading_keys.add(key(node.slice))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "get" and receiver(node.func.value) in {
                    "semantic",
                    "child_roles",
                }:
                    if node.args and key(node.args[0]):
                        consumed["semantic_roles"].add(key(node.args[0]))
            if not isinstance(node, ast.Compare):
                continue
            for left, right in zip([node.left, *node.comparators], node.comparators):
                for candidate, literals in ((left, right), (right, left)):
                    category = domain(candidate)
                    if category == "roles":
                        if (
                            isinstance(literals, ast.Subscript)
                            and receiver(literals.value) == "heading_roles"
                        ):
                            heading_dispatch.add(key(literals.slice))
                        if (
                            isinstance(literals, ast.Call)
                            and isinstance(literals.func, ast.Attribute)
                            and literals.func.attr == "values"
                            and receiver(literals.func.value) == "heading_roles"
                        ):
                            heading_dispatch.add("*")
                    if category:
                        for value, literal in values(literals):
                            consumed[category].add(value)
                            dispatched_nodes.add(literal)
    return consumed, heading_keys, heading_dispatch, dispatched_nodes


def assert_agreement(sources, protocol, not_consumed):
    consumed = {name: set() for name in ("levels", "shapes", "roles", "semantic_roles")}
    heading_keys, heading_dispatch = set(), set()
    for source in sources:
        tree = ast.parse(source)
        current, current_headings, current_dispatch, dispatched_nodes = consumption(tree)
        heading_keys.update(current_headings)
        heading_dispatch.update(current_dispatch)
        for category, tags in current.items():
            consumed[category].update(tags)
        all_tags = set().union(*(set(protocol[name]) for name in ("levels", "shapes", "roles")))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in all_tags:
                assert node in dispatched_nodes, (
                    "Protocol tag outside interpreter dispatch",
                    node.value,
                )
    assert heading_keys == set(protocol["heading_roles"]), (heading_keys, protocol["heading_roles"])
    if "*" not in heading_dispatch:
        assert heading_dispatch == heading_keys, ("Missing heading-role dispatch", heading_dispatch)
    consumed["roles"].update(protocol["heading_roles"].values())
    for category, tags in consumed.items():
        exported = set(protocol[category])
        documented = set(not_consumed.get(category, {}))
        assert not tags - exported, ("Unexported consumed tag", category, tags - exported)
        assert not tags & documented, (
            "Stale not-consumed documentation",
            category,
            tags & documented,
        )
        assert exported == tags | documented, (
            "Protocol dispatch coverage",
            category,
            exported - tags - documented,
        )
    return consumed
