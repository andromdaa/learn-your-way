"""Generate a small CI smoke-test fixture PDF.

Contains 7 educational sections with substantive body text so the
heuristic chunker reliably produces between 5 and 60 concepts.

Run directly to write ci_smoke.pdf next to this script:
    python tests/fixtures/generate_ci_smoke_pdf.py
"""

from pathlib import Path

from fpdf import FPDF

_SECTIONS: list[tuple[str, str]] = [
    (
        "Introduction to Algebra",
        (
            "Algebra is a branch of mathematics dealing with symbols and the rules for "
            "manipulating those symbols. In elementary algebra, those symbols (today "
            "written as Latin and Greek letters) represent quantities without fixed "
            "values, known as variables. Just as sentences describe relationships "
            "between specific words, in algebra, equations describe relationships "
            "between variables. The field of algebra evolved continuously over several "
            "millennia from ancient civilizations including Babylon and Egypt."
        ),
    ),
    (
        "Variables and Expressions",
        (
            "A variable is a symbol used to represent an unknown or changeable value "
            "in a mathematical expression or equation. Common variable names are x, y, "
            "and z, but any letter can be used. An algebraic expression combines "
            "variables, numbers, and operation signs. For example, 3x + 5 is an "
            "expression where x is a variable and 3 and 5 are constants. Evaluating "
            "an expression means substituting a value for each variable and then "
            "computing the result using the standard order of operations."
        ),
    ),
    (
        "Linear Equations",
        (
            "A linear equation is an equation that forms a straight line when graphed "
            "on a coordinate plane. It contains only constants and variables raised to "
            "the first power. The standard form of a linear equation in one variable "
            "is ax + b = c, where a, b, and c are constants and x is the variable. "
            "Solving a linear equation means finding the value of the variable that "
            "makes the equation true. We isolate the variable by performing the same "
            "operation on both sides of the equation to maintain equality."
        ),
    ),
    (
        "Inequalities",
        (
            "An inequality is a mathematical statement that compares two expressions "
            "using an inequality sign such as less than, greater than, less than or "
            "equal to, or greater than or equal to. Unlike equations, inequalities "
            "typically have infinitely many solutions, which are represented as a "
            "range of values. When solving an inequality, the same rules apply as for "
            "equations with one important exception: multiplying or dividing both sides "
            "by a negative number reverses the direction of the inequality sign."
        ),
    ),
    (
        "Systems of Equations",
        (
            "A system of equations is a set of two or more equations that share the "
            "same variables. The solution to a system is the set of values that satisfy "
            "all equations simultaneously. There are three main methods for solving "
            "systems of linear equations: graphing, substitution, and elimination. "
            "Graphing involves plotting both lines and identifying the point of "
            "intersection. Substitution means solving one equation for a variable and "
            "plugging the result into the second equation. Elimination adds or subtracts "
            "equations to cancel a variable."
        ),
    ),
    (
        "Polynomials",
        (
            "A polynomial is an expression consisting of variables and coefficients "
            "combined using addition, subtraction, and multiplication, with "
            "non-negative integer exponents. Polynomials are classified by their "
            "degree, which is the highest power of the variable. A monomial has one "
            "term, a binomial has two terms, and a trinomial has three terms. Adding "
            "and subtracting polynomials involves combining like terms, which are "
            "terms that have the same variable raised to the same power. Multiplying "
            "polynomials requires applying the distributive property repeatedly."
        ),
    ),
    (
        "Factoring",
        (
            "Factoring is the process of writing a polynomial as a product of simpler "
            "polynomials or other mathematical objects. It is the inverse operation of "
            "expanding. Common factoring techniques include factoring out the greatest "
            "common factor, factoring trinomials into two binomials, difference of "
            "squares, and sum and difference of cubes. Factoring is useful for "
            "simplifying expressions, solving polynomial equations, and finding zeros "
            "of functions. The zero product property states that if a product of "
            "factors equals zero, then at least one factor must equal zero."
        ),
    ),
]


def generate(dest: Path) -> None:
    pdf = FPDF()
    pdf.set_margins(left=15, top=15, right=15)

    for heading, body in _SECTIONS:
        pdf.add_page()
        pdf.set_font("Helvetica", style="B", size=16)
        pdf.cell(0, 10, heading, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 8, body)
        pdf.ln(4)

    pdf.output(str(dest))


if __name__ == "__main__":
    out = Path(__file__).parent / "ci_smoke.pdf"
    generate(out)
    print(f"written: {out}")
