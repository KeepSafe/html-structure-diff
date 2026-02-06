from .parser import parse, MdParser, ZendeskHelpMdParser  # noqa
from .renderer import TextRenderer
from .compare import diff_struct, diff_links  # noqa


def diff(md1, md2, renderer=TextRenderer(), parser_cls: type[MdParser] = MdParser):
    """Compare two Markdown strings by structure and return rendered outputs + errors.

    Args:
        md1: Left Markdown string.
        md2: Right Markdown string.
        renderer: Renderer instance used to format the output (TextRenderer by default).
        parser_cls: Parser class to use (MdParser by default).

    Returns:
        (rendered_left, rendered_right, errors)
    """
    tree1 = parse(md1, parser_cls)
    tree2 = parse(md2, parser_cls)

    tree1, tree2, struct_errors = diff_struct(tree1, tree2)
    errors = struct_errors

    return renderer.render(tree1), renderer.render(tree2), errors
