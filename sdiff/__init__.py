from .parser import parse
from .compare import compare
from .renderer import TextRenderer
from .links import links_diff


def diff(text1, text2, renderer=TextRenderer()):
    tree1 = parse(text1)
    tree2 = parse(text2)
    errors = compare(tree1, tree2)

    link_error = links_diff(text1, text2)
    if link_error:
        errors.append(link_error)

    return renderer.render(tree1), renderer.render(tree2), errors
