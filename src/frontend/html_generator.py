from html import escape

class HtmlElement():

    def __init__(self, tag, args, *, self_closing=False):
        self.tag = tag
        self.self_closing = self_closing

        if len(args) > 0 and isinstance(args[0], dict):
            # its an attributes dict
            self.attributes = args[0]
            self.children = args[1:]
        else:
            self.attributes = {}
            self.children = args

    def __str__(self):
        attributes_str = ""
        for key, val in self.attributes.items():
            key = escape(key)
            val = escape(val)
            attributes_str += f" {key}=\"{val}\""
        
        inner_html = ""
        for child in self.children:
            if child is None:
                continue
            if isinstance(child, str):
                inner_html += escape(child)
            else:
                inner_html += str(child)

        if self.self_closing:
            return f"<{self.tag}{attributes_str}>"
        else:
            return f"<{self.tag}{attributes_str}>{inner_html}</{self.tag}>"

def site(*, page_title=None, css=None, page_body):
    # turn it into a list if it isnt one,
    # the body is later treated as a list
    if not isinstance(page_body, list):
        page_body = [page_body]

    head_elements = []
    if page_title:
        head_elements.append(title(page_title))
    if css:
        head_elements.append(style(css))

    return "<!DOCTYPE html>"+ \
        str(html(
            head(
                *head_elements
            ),
            body(*page_body)
        ))

def render_err(err):
    return site(page_title="Error", page_body=
        div(
            p("Error :("),
            p(str(err))
        )
    )

def html(*args):
    return HtmlElement("html", args)

def head(*args):
    return HtmlElement("head", args)

def title(*args):
    return HtmlElement("title", args)

def style(*args):
    return HtmlElement("style", args)

def body(*args):
    return HtmlElement("body", args)

def div(*args):
    return HtmlElement("div", args)

def p(*args):
    return HtmlElement("p", args)

def a(*args):
    return HtmlElement("a", args)

def button(*args):
    return HtmlElement("button", args)

def form(*args):
    return HtmlElement("form", args)

def input(*args):
    return HtmlElement("input", args, self_closing=True)

def textarea(*args):
    return HtmlElement("textarea", args)

def br(*args):
    return HtmlElement("br", args, self_closing=True)