from sdiff.model import *

def empty_tree():
    return Root()

def pt():
    return Root([
        Paragraph([
            Text('dummy text')
        ])
    ])

def r2t():
    return Root([
        Header(2, [
            Text('dummy text')
        ])
    ])

def r4t():
    return Root([
        Header(4, [
            Text('dummy text')
        ])
    ])

def lm2tm2t():
    return Root([
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

def pa():
    return Root([
        Paragraph([
            Link('dummy link')
        ])
    ])

def paa():
    return Root([
        Paragraph([
            Link('dummy link 1'),
            Link('dummy link 2')
        ])
    ])

def ptat():
    return Root([
        Paragraph([
            Text('dummy text 1'),
            Link('dummy link'),
            Text('dummy text 2')
        ])
    ])

def ptnt():
    return Root([
        Paragraph([
            Text('dummy'),
            NewLine(),
            Text('text')
        ])
    ])

def pta2t():
    return Root([
        Paragraph([
            Text('test '),
            Link('link')
        ]),
        Header(2, [
            Text('heading')
        ])
    ])
