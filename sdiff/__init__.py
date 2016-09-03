from .parser import parse
from .renderer import TextRenderer
from .compare import diff_struct, diff_links


def diff(md1, md2, renderer=TextRenderer()):
    tree1 = parse(md1)
    tree2 = parse(md2)

    tree1, tree2, struct_errors = diff_struct(tree1, tree2)
    # tree1, tree2, links_errors = diff_links(tree1, tree2)

    # errors = struct_errors + links_errors
    errors = struct_errors

    return renderer.render(tree1), renderer.render(tree2), errors
