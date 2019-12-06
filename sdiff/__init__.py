from typing import Type

from .parser import parse, MdParser, ZendeskHelpMdParser
from .renderer import TextRenderer
from .compare import diff_struct, diff_links  # noqa


def diff(md1, md2, renderer=TextRenderer(), parser_cls: Type[MdParser] = MdParser):
    tree1 = parse(md1, parser_cls)
    tree2 = parse(md2, parser_cls)

    tree1, tree2, struct_errors = diff_struct(tree1, tree2)
    # tree1, tree2, links_errors = diff_links(tree1, tree2)

    # errors = struct_errors + links_errors
    errors = struct_errors

    return renderer.render(tree1), renderer.render(tree2), errors
