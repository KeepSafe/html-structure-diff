from sdiff.model import *

empty_tree = Root()

paragraph = Root([
    Paragraph([
        Text('dummy text')
    ])
])

header = Root([
    Header(2, [
        Text('dummy text')
    ])
])

header_small = Root([
    Header(4, [
        Text('dummy text')
    ])
])

list_header_header = Root([
    List([
        ListItem([
            Header(2, [
                Text('dummy text')
            ])
        ]),
        ListItem([
            Header(2, [
                Text('dummy text')
            ])
        ])
    ])
])

paragraph_link = Root([
    Paragraph([
        Link('dummy link')
    ])
])

paragraph_link_link = Root([
    Paragraph([
        Link('dummy link 1'),
        Link('dummy link 2')
    ])
])

paragraph_text_link_text = Root([
    Paragraph([
        Text('dummy text 1'),
        Link('dummy link'),
        Text('dummy text 2')
    ])
])

paragraph_text_newline_text = Root([
    Paragraph([
        Text('dummy'),
        NewLine(),
        Text('text')
    ])
])
