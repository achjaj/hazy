import sympy
import sympy.parsing.latex as symtex


def saveToImg(name, expr):
    f = open(name, "wb")
    sympy.preview(expr, viewer="BytesIO", outputbuffer=f, euler=False)
    f.close()


def saveToDVI(name, expr):
    f = open(name, "wb")
    sympy.preview(expr, viewer="BytesIO", outputbuffer=f, euler=False, output="dvi")
    f.close()


def saveToPDF(name, expr):
    f = open(name, "wb")
    sympy.preview(expr, viewer="BytesIO", outputbuffer=f, euler=False, output="pdf")
    f.close()


def saveToPS(name, expr):
    f = open(name, "wb")
    sympy.preview(expr, viewer="BytesIO", outputbuffer=f, euler=False, output="postscript")
    f.close()


def __saveTo(name, text):
    f = open(name, "w")
    f.write(text)
    f.close()


def saveToLaTex(name, expr):
    __saveTo(name, sympy.latex(expr))


def saveToDot(name, expr):
    __saveTo(name, sympy.printing.dotprint(expr))


def saveToMathML(name, expr):
    __saveTo(name, sympy.printing.mathml(expr))


def saveToASCII(name, expr):
    __saveTo(name, sympy.pretty(expr, use_unicode=False))


def saveToUnicode(name, expr):
    __saveTo(name, sympy.pretty(expr, use_unicode=True))


def saveToText(name, expr):
    __saveTo(name, str(expr))


def compute(data):
    symstrlist = data["symbols"]

    expr = None
    if data["expr"]["format"] == "text":
        expr = sympy.sympify(data["expr"]["value"])
    elif data["expr"]["format"] == "latex":
        expr = symtex.parse_latex(data["expr"]["value"])

    if expr is None:
        raise Exception("Cannot parse expression!")

    foggy = sympy.Add()
    for symstr in symstrlist:
        sym = sympy.sympify(symstr)
        foggy += sympy.diff(expr, sym)**2 * sympy.sympify("u_" + symstr)**2

    foggy = sympy.sqrt(foggy)

    return expr, foggy


def eval(foggy, values):
    numerical = foggy
    for sym in values:
        numerical = numerical.subs({sympy.sympify(sym): values[sym]})
    return sympy.N(numerical)
