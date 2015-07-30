class HtmlRenderer(object):
    def render(self, tree):
        result = ''
        for node in tree:
            result += node.original(self)
        return '<pre>\n%s\n</pre>' % result.strip()

    def render_node(self, node, text):
        if node.style == 'ins':
            return '<ins>%s</ins>' % text
        if node.style == 'del':
            return '<del>%s</del>' % text
        return text

class TextRenderer(object):
    def render(self, tree):
        result = ''
        for node in tree:
            result += node.original(self)
        return result.strip()

    def render_node(self, node, text):
        return text
