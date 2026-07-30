#!/usr/bin/env python3
"""
Formula Showcase — generates formulas.docx exercising the docx `equation`
element: 67 LaTeX formulas across algebra, calculus, linear algebra, probability,
number theory, chemistry, physics, and advanced notation (matrices, cases,
delimiters, accents, big operators, colored math, display vs inline mode),
plus a coverage-completeness section (contour integrals, limit-style operators,
\limits/\nolimits, products, binary operators, arrows, math fonts, legacy
fraction syntax).

SDK twin of formulas.sh (officecli CLI). Both produce an equivalent
formulas.docx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every paragraph and
equation is shipped over the named pipe in a single `doc.batch(...)` round-trip.
Each item is the same `{"command","parent","type","props"}` dict you'd put in an
`officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 formulas.py
"""

import os
import sys

# --- locate the SDK: prefer an installed `officecli-sdk`, else the in-repo copy
try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "sdk", "python"))
    import officecli

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "formulas.docx")


def para(text, **props):
    """One `add paragraph` item in batch-shape."""
    return {"command": "add", "parent": "/body", "type": "paragraph",
            "props": {"text": text, **props}}


def eqn(formula, **props):
    """One `add equation` item in batch-shape."""
    return {"command": "add", "parent": "/body", "type": "equation",
            "props": {"formula": formula, **props}}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = [
        # ==================== Title ====================
        para("Complex Math/Chemistry/Physics Formula Collection",
             style="Heading1", align="center"),

        # ==================== I. Algebra ====================
        para("I. Algebra", style="Heading2"),
        para("1. Quadratic Formula:"),
        eqn(r"x = \frac{-b \pm \sqrt{b^{2} - 4ac}}{2a}"),
        para("2. Binomial Theorem:"),
        eqn(r"(a+b)^{n} = \sum_{k=0}^{n} \binom{n}{k} a^{n-k} b^{k}"),
        para("3. Euler's Identity:"),
        eqn(r"e^{i\pi} + 1 = 0"),

        # ==================== II. Calculus ====================
        para("II. Calculus", style="Heading2"),
        para("4. Limit Definition of Derivative:"),
        eqn(r"f^{\prime}(x) = \lim_{\Delta x \rightarrow 0} \frac{f(x + \Delta x) - f(x)}{\Delta x}"),
        para("5. Gaussian Integral:"),
        eqn(r"\int_{-\infty}^{+\infty} e^{-x^{2}} dx = \sqrt{\pi}"),
        para("6. Taylor Series Expansion:"),
        eqn(r"f(x) = \sum_{n=0}^{\infty} \frac{f^{(n)}(a)}{n!} (x-a)^{n}"),
        para("7. Newton-Leibniz Formula:"),
        eqn(r"\int_{a}^{b} f(x) dx = F(b) - F(a)"),
        para("8. Triple Integral (Spherical Coordinates):"),
        eqn(r"\iiint_{V} f(r, \theta, \phi) r^{2} \sin\theta \, dr \, d\theta \, d\phi"),
        para("9. Fourier Transform:"),
        eqn(r"\hat{f}(\xi) = \int_{-\infty}^{+\infty} f(x) e^{-2\pi i x \xi} dx"),

        # ==================== III. Linear Algebra ====================
        para("III. Linear Algebra", style="Heading2"),
        para("10. Matrix Characteristic Equation:"),
        eqn(r"\det(A - \lambda I) = 0"),

        # ==================== IV. Probability and Statistics ====================
        para("IV. Probability and Statistics", style="Heading2"),
        para("11. Bayes' Theorem:"),
        eqn(r"P(A|B) = \frac{P(B|A) \cdot P(A)}{P(B)}"),
        para("12. Normal Distribution PDF:"),
        eqn(r"f(x) = \frac{1}{\sigma \sqrt{2\pi}} e^{-\frac{(x-\mu)^{2}}{2\sigma^{2}}}"),
        para("13. Variance Formula:"),
        eqn(r"\sigma^{2} = \frac{1}{N} \sum_{i=1}^{N} (x_{i} - \mu)^{2}"),

        # ==================== V. Number Theory and Series ====================
        para("V. Number Theory and Series", style="Heading2"),
        para("14. Riemann Zeta Function:"),
        eqn(r"\zeta(s) = \sum_{n=1}^{\infty} \frac{1}{n^{s}}"),
        para("15. Stirling's Approximation:"),
        eqn(r"n! \approx \sqrt{2\pi n} \left(\frac{n}{e}\right)^{n}"),

        # ==================== VI. Chemistry ====================
        para("VI. Chemistry", style="Heading2"),
        para("16. Copper Sulfate Crystal Dissolution:"),
        eqn(r"CuSO_{4} \cdot 5H_{2}O \rightarrow Cu^{2+} + SO_{4}^{2-} + 5H_{2}O"),
        para("17. Thermochemical Equation (Methane Combustion):"),
        eqn(r"CH_{4}(g) + 2O_{2}(g) \rightarrow CO_{2}(g) + 2H_{2}O(l) \quad \Delta H = -890.3 \, kJ/mol"),
        para("18. Chemical Equilibrium Constant Expression:"),
        eqn(r"K_{eq} = \frac{[C]^{c} [D]^{d}}{[A]^{a} [B]^{b}}"),
        para("19. Esterification Reaction (Reversible):"),
        eqn(r"CH_{3}COOH + C_{2}H_{5}OH \rightleftharpoons CH_{3}COOC_{2}H_{5} + H_{2}O"),
        para("20. Henderson-Hasselbalch Equation:"),
        eqn(r"pH = pK_{a} + \log \frac{[A^{-}]}{[HA]}"),
        para("21. Van der Waals Equation:"),
        eqn(r"\left(P + \frac{a n^{2}}{V^{2}}\right)(V - nb) = nRT"),
        para("22. Arrhenius Equation:"),
        eqn(r"k = A e^{-\frac{E_{a}}{RT}}"),

        # ==================== VII. Physics ====================
        para("VII. Physics", style="Heading2"),
        para("23. Maxwell's Equations (Differential Form):"),
        eqn(r"\nabla \cdot E = \frac{\rho}{\epsilon_{0}}"),
        eqn(r"\nabla \cdot B = 0"),
        eqn(r"\nabla \times E = -\frac{\partial B}{\partial t}"),
        eqn(r"\nabla \times B = \mu_{0} J + \mu_{0} \epsilon_{0} \frac{\partial E}{\partial t}"),
        para("24. Einstein Field Equations:"),
        eqn(r"R_{\mu\nu} - \frac{1}{2} R g_{\mu\nu} + \Lambda g_{\mu\nu} = \frac{8\pi G}{c^{4}} T_{\mu\nu}"),
        para("25. Schrodinger Equation:"),
        eqn(r"i\hbar \frac{\partial}{\partial t} \Psi(r, t) = \hat{H} \Psi(r, t)"),
        para("26. Dirac Equation:"),
        eqn(r"(i\gamma^{\mu} \partial_{\mu} - m) \psi = 0"),
        para("27. Euler-Lagrange Equation:"),
        eqn(r"\frac{d}{dt} \frac{\partial L}{\partial \dot{q}_{i}} - \frac{\partial L}{\partial q_{i}} = 0"),
        para("28. Heisenberg Uncertainty Principle:"),
        eqn(r"\Delta x \cdot \Delta p \geq \frac{\hbar}{2}"),
        para("29. Planck's Black-Body Radiation Formula:"),
        eqn(r"B(\nu, T) = \frac{2h\nu^{3}}{c^{2}} \cdot \frac{1}{e^{\frac{h\nu}{k_{B} T}} - 1}"),
        para("30. Lorentz Transformation:"),
        eqn(r"t^{\prime} = \gamma \left(t - \frac{vx}{c^{2}}\right), \quad \gamma = \frac{1}{\sqrt{1 - \frac{v^{2}}{c^{2}}}}"),

        # ==================== VIII. Advanced Notation ====================
        para("VIII. Advanced Notation", style="Heading2"),
        para("31. Matrix (pmatrix):"),
        eqn(r"A = \begin{pmatrix} a_{11} & a_{12} & a_{13} \\ a_{21} & a_{22} & a_{23} \\ a_{31} & a_{32} & a_{33} \end{pmatrix}"),
        para("32. Determinant (vmatrix):"),
        eqn(r"\det(A) = \begin{vmatrix} a & b \\ c & d \end{vmatrix} = ad - bc"),
        para("33. Bracketed Matrix (bmatrix):"),
        eqn(r"I_{3} = \begin{bmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 1 \end{bmatrix}"),
        para("34. Piecewise Function (cases):"),
        eqn(r"|x| = \begin{cases} x, & x \geq 0 \\ -x, & x < 0 \end{cases}"),
        para("35. Auto-sized Delimiters (various brackets):"),
        eqn(r"\left[ \frac{a}{b} \right] + \left\{ \frac{c}{d} \right\} + \left| \frac{e}{f} \right| + \left\langle \frac{g}{h} \right\rangle"),
        para("36. Floor and Ceiling:"),
        eqn(r"\left\lfloor \frac{n}{2} \right\rfloor + \left\lceil \frac{n}{2} \right\rceil = n"),
        para("37. Underbrace and Overbrace:"),
        eqn(r"\underbrace{1 + 2 + \cdots + n}_{n \text{ terms}} = \overbrace{\frac{n(n+1)}{2}}^{\text{closed form}}"),
        para("38. Overset (definition):"),
        eqn(r"f(x) \overset{\text{def}}{=} \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}"),
        para("39. Math Fonts (mathbb / mathcal / mathbf / mathrm):"),
        eqn(r"\forall x \in \mathbb{R}, \exists \mathcal{L} : \mathbf{v} \mapsto \mathrm{d}\mathbf{v}"),
        para("40. Cancellation:"),
        eqn(r"\frac{(x+1) \cancel{(x-1)}}{\cancel{(x-1)}} = x + 1"),
        para("41. Cancel-to (limit):"),
        eqn(r"\lim_{x \to \infty} \cancelto{0}{\frac{1}{x}} + 1 = 1"),
        para("42. Boxed Result:"),
        eqn(r"\boxed{E = mc^{2}}"),
        para("43. Accents (bar / vec / tilde / ddot):"),
        eqn(r"\bar{x} = \frac{1}{n} \sum x_{i}, \quad \vec{F} = m\ddot{\vec{r}}, \quad \tilde{f}(\xi)"),
        para("44. Overline and Underline:"),
        eqn(r"\overline{A \cup B} = \overline{A} \cap \overline{B}, \quad \underline{x} \leq x \leq \overline{x}"),
        para("45. Hyperbolic and Inverse Trig:"),
        eqn(r"\arctan(x) = \int_{0}^{x} \frac{dt}{1+t^{2}}, \quad \cosh^{2}(x) - \sinh^{2}(x) = 1"),
        para("46. Custom Operator (operatorname):"),
        eqn(r"\operatorname{lcm}(a, b) \cdot \gcd(a, b) = |ab|"),
        para("47. Modular Arithmetic:"),
        eqn(r"a \equiv b \pmod{n} \iff n \mid (a - b), \quad 17 \bmod 5 = 2"),
        para("48. Double Integral with Text:"),
        eqn(r"\iint_{D} f(x,y) \, dA \quad \text{where } D = \{(x,y) : x^{2}+y^{2} \leq 1\}"),
        para("49. Big Operators (bigcup / bigcap / coprod):"),
        eqn(r"\bigcup_{i=1}^{n} A_{i} \supseteq \bigcap_{i=1}^{n} A_{i}, \quad \coprod_{i \in I} X_{i}"),
        para("50. Greek Letters (full uppercase set):"),
        eqn(r"\Gamma, \Theta, \Xi, \Pi, \Phi, \Psi, \Omega \in \{\alpha, \beta, \gamma, \delta, \epsilon, \zeta, \eta, \theta\}"),
        para("51. Dots (ldots / cdots / vdots / ddots):"),
        eqn(r"M = \begin{pmatrix} a_{11} & \cdots & a_{1n} \\ \vdots & \ddots & \vdots \\ a_{m1} & \cdots & a_{mn} \end{pmatrix}, \quad x_{1}, x_{2}, \ldots, x_{n}"),
        para("52. Spacing Control (quad / qquad / thinsp):"),
        eqn(r"a + b \, c \; d \quad e \qquad f"),
        para("53. Colored Math (textcolor / color):"),
        eqn(r"\textcolor{red}{x^{2}} + \textcolor{blue}{2xy} + \textcolor{green}{y^{2}} = \color{purple}{(x+y)^{2}}"),
        para("54. Set Theory:"),
        eqn(r"A \subseteq B \iff \forall x \in A, x \in B; \quad A \setminus B = \{x : x \in A \land x \notin B\}; \quad \emptyset \subset A"),
        para("55. Norm and Inner Product:"),
        eqn(r"\|x\|_{2} = \sqrt{\langle x, x \rangle} = \sqrt{\sum_{i=1}^{n} x_{i}^{2}}"),

        # ============ IX. Equation Mode (display vs inline) ============
        para("IX. Equation Mode — display vs inline", style="Heading2"),
        # mode=display (default): equation gets its own block-level oMathPara element
        para("56. Display mode (default) — centred block equation:"),
        eqn(r"E = mc^{2}", mode="display"),
        # mode=inline: equation is appended to the parent paragraph as an oMath child
        para("57. Inline mode — equation embedded mid-sentence:"),
        eqn(r"A = \pi r^{2}", mode="inline"),

        # ====== X. Coverage Completeness — Additional Supported Commands ======
        para("X. Coverage Completeness — Additional Supported Commands",
             style="Heading2"),
        para("58. N-ary Contour Integrals (oint / oiint / oiiint):"),
        eqn(r"\oint_C \vec{F} \cdot d\vec{r} = \iint_S (\nabla \times \vec{F}) \cdot d\vec{S}, \quad \oiint_S \vec{E} \cdot d\vec{A} = \frac{Q}{\epsilon_0}, \quad \oiiint_V \rho \, dV"),
        para("59. Limit-style Operators with Under-limits (max / min / sup / inf):"),
        eqn(r"\max_{1 \le i \le n} a_i \geq \min_{1 \le i \le n} a_i, \quad \sup_{x \in S} f(x) \geq \inf_{x \in S} f(x)"),
        para("60. More Limit Operators (limsup / liminf / argmax / argmin):"),
        eqn(r"\limsup_{n \to \infty} x_n \geq \liminf_{n \to \infty} x_n, \quad \hat{\theta} = \argmax_{\theta} L(\theta) = \argmin_{\theta} (-L(\theta))"),
        para("61. Named Operators with Limits (det / gcd / Pr):"),
        eqn(r"\det_{A \in M} A, \quad \gcd_{i} a_i, \quad \Pr_{x \sim D}[X = x]"),
        para("62. Limits Placement Control (\\limits / \\nolimits):"),
        eqn(r"\lim\limits_{x \to 0} \frac{\sin x}{x} = 1, \quad \sum\nolimits_{i=1}^{n} i = \frac{n(n+1)}{2}"),
        para("63. N-ary Product (prod):"),
        eqn(r"n! = \prod_{k=1}^{n} k, \quad \prod_{p \text{ prime}} \frac{1}{1 - p^{-s}} = \zeta(s)"),
        para("64. Binary Operators (div / ast / star / circ / oplus / ominus / otimes / odot / bullet):"),
        eqn(r"a \div b, \quad f \ast g, \quad a \star b, \quad f \circ g, \quad a \oplus b \ominus c, \quad u \otimes v \odot w, \quad x \bullet y"),
        para("65. Arrows (leftarrow / uparrow / downarrow / leftrightarrow / Rightarrow / Leftarrow / Leftrightarrow / gets / implies):"),
        eqn(r"a \leftarrow b \uparrow c \downarrow d \leftrightarrow e, \quad P \Rightarrow Q, \quad R \Leftarrow S, \quad X \Leftrightarrow Y, \quad n \gets n+1, \quad p \implies q"),
        para("66. Math Fonts (boldsymbol / mathit) and Over/Under-set:"),
        eqn(r"\boldsymbol{\alpha} + \mathit{xyz}, \quad \overset{!}{=} \quad \underset{n \to \infty}{\lim} a_n"),
        para("67. Relations, Logic, Sets, Trig, and Legacy Fraction (\\neq / \\sim / \\subset / \\lor / \\neg / \\wedge / \\parallel / \\varnothing / \\complement / \\cos / \\tan / \\ln / {a \\over b}):"),
        eqn(r"a \neq b \sim c, \quad A \subset B \supset C, \quad p \lor \neg q \wedge r, \quad u \vee v, \quad \ell_1 \parallel \ell_2, \quad \varnothing = \complement_U U, \quad \cos^2 x + \tan x - \ln x, \quad {a \over b}"),

        # ====== XI. Full Symbol & Environment Coverage ======
        para("XI. Full Symbol & Environment Coverage", style="Heading2"),
        # Greek variants — \chi \iota \kappa \omega \tau \upsilon \varepsilon \varphi \varpi \varrho \varsigma \vartheta \varkappa \digamma
        para("68. Greek Variants and Extra Letters:"),
        eqn(r"\chi, \iota, \kappa, \omega, \tau, \upsilon, \varepsilon, \varphi, \varpi, \varrho, \varsigma, \vartheta, \varkappa, \digamma"),
        # Relations — \cong \simeq \asymp \doteq \propto \prec \succ \preceq \succeq \ll \gg \models \vdash \dashv \perp \top \ni \sqsubset \sqsubseteq \sqsupset \sqsupseteq \subsetneq \supsetneq \Vdash
        para("69. Relation Symbols:"),
        eqn(r"a \cong b \simeq c \asymp d \doteq e, \quad f \propto g, \quad x \prec y \succ z, \quad p \preceq q \succeq r, \quad m \ll n \gg k, \quad \Gamma \models \phi \vdash \psi \dashv \chi \Vdash \omega, \quad u \perp v, \quad \top, \quad a \ni b, \quad S \sqsubset T \sqsubseteq U \sqsupset V \sqsupseteq W, \quad A \subsetneq B \supsetneq C"),
        # Negated relations — \nleq \ngeq \nmid \nsubseteq \nsupseteq \nexists
        para("70. Negated Relations:"),
        eqn(r"a \nleq b, \quad c \ngeq d, \quad e \nmid f, \quad g \nparallel h, \quad A \nsubseteq B, \quad C \nsupseteq D, \quad \nexists x"),
        # Arrows — \longleftarrow \longrightarrow \longleftrightarrow \longmapsto \hookleftarrow \hookrightarrow \twoheadrightarrow \rightsquigarrow \leftharpoonup \leftharpoondown \rightharpoonup \rightharpoondown \nearrow \searrow \swarrow \nwarrow \curvearrowleft \curvearrowright \impliedby
        para("71. Extended Arrows:"),
        eqn(r"a \longleftarrow b \longrightarrow c \longleftrightarrow d, \quad x \longmapsto y, \quad e \hookleftarrow f \hookrightarrow g, \quad p \twoheadrightarrow q \rightsquigarrow r, \quad u \leftharpoonup v \leftharpoondown w \rightharpoonup s \rightharpoondown t, \quad \nearrow \searrow \swarrow \nwarrow, \quad \alpha \curvearrowleft \beta \curvearrowright \gamma, \quad P \impliedby Q"),
        # Misc symbols — \aleph \beth \gimel \daleth \wp \Re \Im \Sigma \angle \measuredangle \sphericalangle \triangle \triangleleft \triangleright \square \blacksquare \Diamond \diamond \diamondsuit \clubsuit \heartsuit \spadesuit \flat \sharp \natural \dagger \ddagger \bigstar \amalg \uplus \sqcap \sqcup \wr \bowtie \frown \smile \mp \bigtriangledown
        para("72. Miscellaneous Symbols:"),
        eqn(r"\aleph, \beth, \gimel, \daleth, \wp, \Re, \Im, \Sigma, \quad \angle, \measuredangle, \sphericalangle, \triangle, \triangleleft, \triangleright, \quad \square, \blacksquare, \Diamond, \diamond, \diamondsuit, \clubsuit, \heartsuit, \spadesuit, \quad \flat, \sharp, \natural, \dagger, \ddagger, \bigstar, \quad a \amalg b \uplus c \sqcap d \sqcup e \wr f, \quad x \bowtie y \frown z \smile w, \quad p \mp q, \quad \bigtriangledown"),
        # Math font families — \mathfrak \mathsf \mathtt \textbf \textit \textsf \texttt
        para("73. Math Font Families (Fraktur / sans / mono / bold / italic text):"),
        eqn(r"\mathfrak{ABCDabcd} \quad \mathsf{ABCDabcd} \quad \mathtt{ABCDabcd} \quad \textbf{ABCDabcd} \quad \textit{ABCDabcd} \quad \textsf{ABCDabcd} \quad \texttt{ABCDabcd}"),
        # Environments — Bmatrix Vmatrix
        para("74. Environments — Bmatrix and Vmatrix:"),
        eqn(r"\begin{Bmatrix} a & b \\ c & d \end{Bmatrix} \quad \begin{Vmatrix} a & b \\ c & d \end{Vmatrix}"),
        # Environments — smallmatrix array (colspec)
        para("75. Environments — smallmatrix and array (colspec):"),
        eqn(r"\left(\begin{smallmatrix} 1 & 0 \\ 0 & 1 \end{smallmatrix}\right) \quad \begin{array}{cc} x & y \\ z & w \end{array}"),
        # Environments — aligned align (multi alignment points)
        para("76. Environments — aligned and align (multi alignment points):"),
        eqn(r"\begin{aligned} a &= b \\ c &= d \end{aligned} \qquad \begin{align} a &= b & c &= d \\ e &= f & g &= h \end{align}"),
        # Environments — gather split substack
        para("77. Environments — gather, split, and substack:"),
        eqn(r"\begin{gather} x = 1 \\ y = 2 \end{gather} \qquad \begin{split} a &= b + c \\ &= d \end{split} \qquad \sum_{\substack{i=1 \\ j=1}}^{n} a_{ij}"),
    ]

    doc.batch(items)
    print(f"  added {len(items)} paragraphs/equations")

print(f"Generated: {FILE}")
