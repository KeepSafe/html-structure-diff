from sdiff.model import Root, Node


class HtmlRenderer(object):

    def render(self, tree: Root):
        result = tree.original(self)
        return '<pre>\n%s\n</pre>' % result.strip()

    def render_node(self, node, text):
        if node.meta.get('style') == 'ins':
            return '<ins>%s</ins>' % text
        if node.meta.get('style') == 'del':
            return '<del>%s</del>' % text
        return text


class TextRenderer(object):

    def render(self, tree: Root):
        result = tree.original(self)
        return result.strip()

    def render_node(self, node: Node, text):
        return text
