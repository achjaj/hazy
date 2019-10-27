import sympy
import sympy.parsing.latex as symtex
import io

def saveToImg(name, expr):
    f = open(name, "wb")
    sympy.preview(expr, viewer="BytesIO", outputbuffer=f)
    f.close()

def saveToLaTex(name, expr):
    f = open(name, "w")
    f.write(sympy.latex(expr))
    f.close()

def compute(data):
    symstrlist = data["symbols"]

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

def eval(foggy, data):
    if not "values" in data:
        return None

    symvalues = data["values"]

    numerical = foggy
    for sym in symvalues:
        numerical = numerical.subs({sympy.sympify(sym): symvalues[sym]})
    return sympy.N(numerical)
