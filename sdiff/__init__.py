from .parser import parse
from .compare import compare
from .renderer import TextRenderer

def diff(text1, text2, renderer=TextRenderer()):
    tree1 = parse(text1)
    tree2 = parse(text2)

    errors = compare(tree1, tree2)
    return renderer.render(tree1), renderer.render(tree2), errors
