import os
from html import escape

assets_cache = {}

class HtmlElement():

    def __init__(self, tag, args, *, self_closing=False, safe=True):
        self.tag = tag
        self.self_closing = self_closing
        self.safe = safe

        if len(args) > 0 and isinstance(args[0], dict):
            # its an attributes dict
            self.attributes = args[0]
            self.children = args[1:]
        else:
            self.attributes = {}
            self.children = args

        self.children = [*self.children]

        self.css = []
        if "css" in self.attributes:
            self.css = [self.attributes["css"]]
            self.attributes.pop("css")
        self.js = []
        if "js" in self.attributes:
            self.js = [self.attributes["js"]]
            self.attributes.pop("js")

        for child in self.children:
            if not isinstance(child, HtmlElement):
                continue
            for css in child.css:
                if css not in self.css:
                    self.css.append(css)
            for js in child.js:
                if js not in self.js:
                    self.js.append(js)

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
            if isinstance(child, str) and self.safe:
                inner_html += escape(child)
            else:
                inner_html += str(child)

        if self.self_closing:
            return f"<{self.tag}{attributes_str}>"
        else:
            return f"<{self.tag}{attributes_str}>{inner_html}</{self.tag}>"

def read_asset_file(file_type, file_name):
    if file_name in assets_cache:
        return assets_cache[file_name]

    script_dir = os.path.dirname(__file__)
    folder = os.path.join(script_dir, file_type)
    file_path = os.path.join(folder, file_name)

    with open(file_path, "r") as file:
        content = file.read()
    
    assets_cache[file_name] = content
    
    return content

def render(page_title, page_body):
    # turn it into a list if it isnt one,
    # the body is later treated as a list
    if not isinstance(page_body, list):
        page_body = [page_body]

    body_element = body(*page_body)

    head_elements = []
    if page_title:
        head_elements.append(title(page_title))
    css_files = body_element.css
    css_files.append("styles.css")
    css_string = "\n\n".join([read_asset_file("css", css_file) for css_file in css_files])

    head_elements.append(style(css_string))

    js_files = body_element.js
    for js_file in js_files:
        body_element.children.append(script(read_asset_file("js", js_file)))

    return "<!DOCTYPE html>"+ \
        str(html(
            head(
                *head_elements
            ),
            body_element
        ))

def render_err(err):
    return render(page_title="Error", page_body=
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

def h1(*args):
    return HtmlElement("h1", args)

def a(*args):
    return HtmlElement("a", args)

def button(*args):
    return HtmlElement("button", args)

def form(*args):
    return HtmlElement("form", args)

def input(*args):
    return HtmlElement("input", args, self_closing=True)

def label(*args):
    return HtmlElement("label", args)

def textarea(*args):
    return HtmlElement("textarea", args)

def br(*args):
    return HtmlElement("br", args, self_closing=True)

def script(*args, **kwargs):
    if "src" in kwargs:
        return HtmlElement("script", [*args, read_asset_file("js", kwargs["src"])], safe=False)
    return HtmlElement("script", args, safe=False)
