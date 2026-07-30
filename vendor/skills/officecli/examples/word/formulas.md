# Math / Formula Showcase

Generates a Word document with 67 equations spanning algebra, calculus, linear algebra, statistics, number theory, chemistry, physics, advanced LaTeX notation, and a coverage-completeness catalog. Three files:

- **formulas.sh** — builds the document with `officecli` (67 equations).
- **formulas.docx** — generated output; open in Word to see OMML-rendered equations.
- **formulas.md** — this file.

## Regenerate

```bash
cd examples/word
bash formulas.sh
# → formulas.docx
```

## I. Algebra

Fundamental algebraic identities using fractions, radicals, sums, and binomials.

```bash
# 1. Quadratic Formula
officecli add formulas.docx /body --type equation \
  --prop 'formula=x = \frac{-b \pm \sqrt{b^{2} - 4ac}}{2a}'

# 2. Binomial Theorem
officecli add formulas.docx /body --type equation \
  --prop 'formula=(a+b)^{n} = \sum_{k=0}^{n} \binom{n}{k} a^{n-k} b^{k}'

# 3. Euler's Identity
officecli add formulas.docx /body --type equation \
  --prop 'formula=e^{i\pi} + 1 = 0'
```

**Features:** `formula` (LaTeX-ish math string, converted to OMML), `\frac`, `\sqrt`, `\sum`, `\binom`, superscripts/subscripts (`^{}`/`_{}`), `\pm`, `\pi`

## II. Calculus

Limits, integrals, series, and transforms.

```bash
# 4. Limit Definition of Derivative
officecli add formulas.docx /body --type equation \
  --prop 'formula=f^{\prime}(x) = \lim_{\Delta x \rightarrow 0} \frac{f(x + \Delta x) - f(x)}{\Delta x}'

# 5. Gaussian Integral
officecli add formulas.docx /body --type equation \
  --prop 'formula=\int_{-\infty}^{+\infty} e^{-x^{2}} dx = \sqrt{\pi}'

# 6. Taylor Series Expansion
officecli add formulas.docx /body --type equation \
  --prop 'formula=f(x) = \sum_{n=0}^{\infty} \frac{f^{(n)}(a)}{n!} (x-a)^{n}'

# 7. Newton-Leibniz Formula
officecli add formulas.docx /body --type equation \
  --prop 'formula=\int_{a}^{b} f(x) dx = F(b) - F(a)'

# 8. Triple Integral (Spherical Coordinates)
officecli add formulas.docx /body --type equation \
  --prop 'formula=\iiint_{V} f(r, \theta, \phi) r^{2} \sin\theta \, dr \, d\theta \, d\phi'

# 9. Fourier Transform
officecli add formulas.docx /body --type equation \
  --prop 'formula=\hat{f}(\xi) = \int_{-\infty}^{+\infty} f(x) e^{-2\pi i x \xi} dx'
```

**Features:** `\lim`, `\int`, `\iiint`, `\infty`, `\rightarrow`, `\Delta`, `\prime`, `\theta`, `\phi`, `\sin`, `\hat`, `\xi`, `\pi`, spacing commands (`\,`)

## III. Linear Algebra

Matrix characteristic equations.

```bash
# 10. Matrix Characteristic Equation
officecli add formulas.docx /body --type equation \
  --prop 'formula=\det(A - \lambda I) = 0'
```

**Features:** `\det`, `\lambda`

## IV. Probability and Statistics

Bayes' theorem, normal distribution, and variance.

```bash
# 11. Bayes' Theorem
officecli add formulas.docx /body --type equation \
  --prop 'formula=P(A|B) = \frac{P(B|A) \cdot P(A)}{P(B)}'

# 12. Normal Distribution PDF
officecli add formulas.docx /body --type equation \
  --prop 'formula=f(x) = \frac{1}{\sigma \sqrt{2\pi}} e^{-\frac{(x-\mu)^{2}}{2\sigma^{2}}}'

# 13. Variance Formula
officecli add formulas.docx /body --type equation \
  --prop 'formula=\sigma^{2} = \frac{1}{N} \sum_{i=1}^{N} (x_{i} - \mu)^{2}'
```

**Features:** `\sigma`, `\mu`, `\cdot`, `\pi` (nested fractions in exponents)

## V. Number Theory and Series

Zeta function and Stirling's approximation.

```bash
# 14. Riemann Zeta Function
officecli add formulas.docx /body --type equation \
  --prop 'formula=\zeta(s) = \sum_{n=1}^{\infty} \frac{1}{n^{s}}'

# 15. Stirling's Approximation
officecli add formulas.docx /body --type equation \
  --prop 'formula=n! \approx \sqrt{2\pi n} \left(\frac{n}{e}\right)^{n}'
```

**Features:** `\zeta`, `\approx`, `\left(`, `\right)` (auto-sized delimiters)

## VI. Chemistry

Chemical equations with subscripts, arrows, and thermodynamic notation.

```bash
# 16. Copper Sulfate Crystal Dissolution
officecli add formulas.docx /body --type equation \
  --prop 'formula=CuSO_{4} \cdot 5H_{2}O \rightarrow Cu^{2+} + SO_{4}^{2-} + 5H_{2}O'

# 17. Thermochemical Equation (Methane Combustion)
officecli add formulas.docx /body --type equation \
  --prop 'formula=CH_{4}(g) + 2O_{2}(g) \rightarrow CO_{2}(g) + 2H_{2}O(l) \quad \Delta H = -890.3 \, kJ/mol'

# 18. Chemical Equilibrium Constant
officecli add formulas.docx /body --type equation \
  --prop 'formula=K_{eq} = \frac{[C]^{c} [D]^{d}}{[A]^{a} [B]^{b}}'

# 19. Esterification Reaction (Reversible Arrow)
officecli add formulas.docx /body --type equation \
  --prop 'formula=CH_{3}COOH + C_{2}H_{5}OH \rightleftharpoons CH_{3}COOC_{2}H_{5} + H_{2}O'

# 20. Henderson-Hasselbalch Equation
officecli add formulas.docx /body --type equation \
  --prop 'formula=pH = pK_{a} + \log \frac{[A^{-}]}{[HA]}'

# 21. Van der Waals Equation
officecli add formulas.docx /body --type equation \
  --prop 'formula=\left(P + \frac{a n^{2}}{V^{2}}\right)(V - nb) = nRT'

# 22. Arrhenius Equation
officecli add formulas.docx /body --type equation \
  --prop 'formula=k = A e^{-\frac{E_{a}}{RT}}'
```

**Features:** `\rightarrow`, `\rightleftharpoons` (reversible arrow), `\quad` (wide space), `\Delta`, ion superscripts (`^{2+}`, `^{2-}`), `\log`

## VII. Physics

Maxwell's equations, relativity, and quantum mechanics.

```bash
# 23. Maxwell's Equations (Differential Form — 4 equations)
officecli add formulas.docx /body --type equation \
  --prop 'formula=\nabla \cdot E = \frac{\rho}{\epsilon_{0}}'
officecli add formulas.docx /body --type equation \
  --prop 'formula=\nabla \cdot B = 0'
officecli add formulas.docx /body --type equation \
  --prop 'formula=\nabla \times E = -\frac{\partial B}{\partial t}'
officecli add formulas.docx /body --type equation \
  --prop 'formula=\nabla \times B = \mu_{0} J + \mu_{0} \epsilon_{0} \frac{\partial E}{\partial t}'

# 24. Einstein Field Equations
officecli add formulas.docx /body --type equation \
  --prop 'formula=R_{\mu\nu} - \frac{1}{2} R g_{\mu\nu} + \Lambda g_{\mu\nu} = \frac{8\pi G}{c^{4}} T_{\mu\nu}'

# 25. Schrodinger Equation
officecli add formulas.docx /body --type equation \
  --prop 'formula=i\hbar \frac{\partial}{\partial t} \Psi(r, t) = \hat{H} \Psi(r, t)'

# 26. Dirac Equation
officecli add formulas.docx /body --type equation \
  --prop 'formula=(i\gamma^{\mu} \partial_{\mu} - m) \psi = 0'

# 27. Euler-Lagrange Equation
officecli add formulas.docx /body --type equation \
  --prop 'formula=\frac{d}{dt} \frac{\partial L}{\partial \dot{q}_{i}} - \frac{\partial L}{\partial q_{i}} = 0'

# 28. Heisenberg Uncertainty Principle
officecli add formulas.docx /body --type equation \
  --prop 'formula=\Delta x \cdot \Delta p \geq \frac{\hbar}{2}'

# 29. Planck's Black-Body Radiation Formula
officecli add formulas.docx /body --type equation \
  --prop 'formula=B(\nu, T) = \frac{2h\nu^{3}}{c^{2}} \cdot \frac{1}{e^{\frac{h\nu}{k_{B} T}} - 1}'

# 30. Lorentz Transformation
officecli add formulas.docx /body --type equation \
  --prop 'formula=t^{\prime} = \gamma \left(t - \frac{vx}{c^{2}}\right), \quad \gamma = \frac{1}{\sqrt{1 - \frac{v^{2}}{c^{2}}}}'
```

**Features:** `\nabla`, `\times`, `\partial`, `\hbar`, `\Psi`, `\hat{H}`, `\gamma`, `\Lambda`, `\mu`, `\nu`, `\epsilon`, `\rho`, `\geq`, `\dot{q}` (dot accent)

## VIII. Advanced Notation

Matrix environments, auto-sized brackets, decorations, math fonts, and color.

```bash
# 31. Matrix (pmatrix — round brackets)
officecli add formulas.docx /body --type equation \
  --prop 'formula=A = \begin{pmatrix} a_{11} & a_{12} & a_{13} \\ a_{21} & a_{22} & a_{23} \\ a_{31} & a_{32} & a_{33} \end{pmatrix}'

# 32. Determinant (vmatrix — vertical bars)
officecli add formulas.docx /body --type equation \
  --prop 'formula=\det(A) = \begin{vmatrix} a & b \\ c & d \end{vmatrix} = ad - bc'

# 33. Identity Matrix (bmatrix — square brackets)
officecli add formulas.docx /body --type equation \
  --prop 'formula=I_{3} = \begin{bmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 1 \end{bmatrix}'

# 34. Piecewise Function (cases)
officecli add formulas.docx /body --type equation \
  --prop 'formula=|x| = \begin{cases} x, & x \geq 0 \\ -x, & x < 0 \end{cases}'

# 35. Auto-sized delimiters
officecli add formulas.docx /body --type equation \
  --prop 'formula=\left[ \frac{a}{b} \right] + \left\{ \frac{c}{d} \right\} + \left| \frac{e}{f} \right| + \left\langle \frac{g}{h} \right\rangle'

# 36. Floor and Ceiling
officecli add formulas.docx /body --type equation \
  --prop 'formula=\left\lfloor \frac{n}{2} \right\rfloor + \left\lceil \frac{n}{2} \right\rceil = n'

# 37. Underbrace and Overbrace
officecli add formulas.docx /body --type equation \
  --prop 'formula=\underbrace{1 + 2 + \cdots + n}_{n \text{ terms}} = \overbrace{\frac{n(n+1)}{2}}^{\text{closed form}}'

# 38. Overset (definition)
officecli add formulas.docx /body --type equation \
  --prop 'formula=f(x) \overset{\text{def}}{=} \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}'

# 39. Math Fonts (mathbb / mathcal / mathbf / mathrm)
officecli add formulas.docx /body --type equation \
  --prop 'formula=\forall x \in \mathbb{R}, \exists \mathcal{L} : \mathbf{v} \mapsto \mathrm{d}\mathbf{v}'

# 40. Cancellation
officecli add formulas.docx /body --type equation \
  --prop 'formula=\frac{(x+1) \cancel{(x-1)}}{\cancel{(x-1)}} = x + 1'

# 41. Cancel-to (limit annotation)
officecli add formulas.docx /body --type equation \
  --prop 'formula=\lim_{x \to \infty} \cancelto{0}{\frac{1}{x}} + 1 = 1'

# 42. Boxed result
officecli add formulas.docx /body --type equation \
  --prop 'formula=\boxed{E = mc^{2}}'

# 43. Accents (bar / vec / tilde / ddot)
officecli add formulas.docx /body --type equation \
  --prop 'formula=\bar{x} = \frac{1}{n} \sum x_{i}, \quad \vec{F} = m\ddot{\vec{r}}, \quad \tilde{f}(\xi)'

# 44. Overline and Underline
officecli add formulas.docx /body --type equation \
  --prop 'formula=\overline{A \cup B} = \overline{A} \cap \overline{B}, \quad \underline{x} \leq x \leq \overline{x}'

# 45-55: Additional advanced notation (hyperbolic trig, operatorname, modular, norms, dots, spacing, color, set theory) ...

# 53. Colored Math
officecli add formulas.docx /body --type equation \
  --prop 'formula=\textcolor{red}{x^{2}} + \textcolor{blue}{2xy} + \textcolor{green}{y^{2}} = \color{purple}{(x+y)^{2}}'
```

**Features:** `\begin{pmatrix}`, `\begin{vmatrix}`, `\begin{bmatrix}`, `\begin{cases}` (matrix environments), `\left`/`\right` with `[`, `{`, `|`, `\langle`, `\rfloor`, `\rceil` (auto-sized delimiters), `\underbrace`, `\overbrace`, `\overset`, `\cancel`, `\cancelto`, `\boxed`, `\bar`, `\vec`, `\tilde`, `\ddot`, `\overline`, `\underline`, `\mathbb`, `\mathcal`, `\mathbf`, `\mathrm`, `\forall`, `\exists`, `\mapsto`, `\textcolor`, `\color`

## IX. Equation Mode — display vs. inline

The `mode` prop controls whether the equation renders as a block-level element or is embedded inline within the paragraph.

```bash
# mode=display (default): own block-level oMathPara element, centred
officecli add formulas.docx /body --type paragraph \
  --prop text="56. Display mode (default) — centred block equation:"
officecli add formulas.docx /body --type equation \
  --prop 'formula=E = mc^{2}' --prop mode=display

# mode=inline: equation appended to parent paragraph as an oMath child
officecli add formulas.docx /body --type paragraph \
  --prop text="57. Inline mode — equation embedded mid-sentence:"
officecli add formulas.docx /body --type equation \
  --prop 'formula=A = \pi r^{2}' --prop mode=inline
```

**Features:** `mode` (display/inline — `display` wraps in `oMathPara` as a block; `inline` inserts `oMath` as a run inside the current paragraph)

## X. Coverage Completeness — Additional Supported Commands

A representative catalog of supported commands not exercised above: n-ary contour integrals, limit-style operators with under-limits, explicit limits placement, products, binary operators, arrows, additional math fonts, over/under-set, and legacy fraction syntax.

```bash
# 58. N-ary Contour Integrals (oint / oiint / oiiint)
officecli add formulas.docx /body --type equation \
  --prop 'formula=\oint_C \vec{F} \cdot d\vec{r} = \iint_S (\nabla \times \vec{F}) \cdot d\vec{S}, \quad \oiint_S \vec{E} \cdot d\vec{A} = \frac{Q}{\epsilon_0}, \quad \oiiint_V \rho \, dV'

# 59. Limit-style Operators with Under-limits (max / min / sup / inf)
officecli add formulas.docx /body --type equation \
  --prop 'formula=\max_{1 \le i \le n} a_i \geq \min_{1 \le i \le n} a_i, \quad \sup_{x \in S} f(x) \geq \inf_{x \in S} f(x)'

# 60. More Limit Operators (limsup / liminf / argmax / argmin)
officecli add formulas.docx /body --type equation \
  --prop 'formula=\limsup_{n \to \infty} x_n \geq \liminf_{n \to \infty} x_n, \quad \hat{\theta} = \argmax_{\theta} L(\theta) = \argmin_{\theta} (-L(\theta))'

# 61. Named Operators with Limits (det / gcd / Pr)
officecli add formulas.docx /body --type equation \
  --prop 'formula=\det_{A \in M} A, \quad \gcd_{i} a_i, \quad \Pr_{x \sim D}[X = x]'

# 62. Limits Placement Control (\limits / \nolimits)
officecli add formulas.docx /body --type equation \
  --prop 'formula=\lim\limits_{x \to 0} \frac{\sin x}{x} = 1, \quad \sum\nolimits_{i=1}^{n} i = \frac{n(n+1)}{2}'

# 63. N-ary Product (prod)
officecli add formulas.docx /body --type equation \
  --prop 'formula=n! = \prod_{k=1}^{n} k, \quad \prod_{p \text{ prime}} \frac{1}{1 - p^{-s}} = \zeta(s)'

# 64. Binary Operators (div / ast / star / circ / oplus / ominus / otimes / odot / bullet)
officecli add formulas.docx /body --type equation \
  --prop 'formula=a \div b, \quad f \ast g, \quad a \star b, \quad f \circ g, \quad a \oplus b \ominus c, \quad u \otimes v \odot w, \quad x \bullet y'

# 65. Arrows (leftarrow / uparrow / downarrow / leftrightarrow / Rightarrow / Leftarrow / Leftrightarrow / gets / implies)
officecli add formulas.docx /body --type equation \
  --prop 'formula=a \leftarrow b \uparrow c \downarrow d \leftrightarrow e, \quad P \Rightarrow Q, \quad R \Leftarrow S, \quad X \Leftrightarrow Y, \quad n \gets n+1, \quad p \implies q'

# 66. Math Fonts (boldsymbol / mathit) and Over/Under-set
officecli add formulas.docx /body --type equation \
  --prop 'formula=\boldsymbol{\alpha} + \mathit{xyz}, \quad \overset{!}{=} \quad \underset{n \to \infty}{\lim} a_n'

# 67. Relations, Logic, Sets, Trig, and Legacy Fraction
officecli add formulas.docx /body --type equation \
  --prop 'formula=a \neq b \sim c, \quad A \subset B \supset C, \quad p \lor \neg q \wedge r, \quad u \vee v, \quad \ell_1 \parallel \ell_2, \quad \varnothing = \complement_U U, \quad \cos^2 x + \tan x - \ln x, \quad {a \over b}'
```

**Features:** `\oint`, `\oiint`, `\oiiint` (n-ary contour integrals), `\max`, `\min`, `\sup`, `\inf`, `\limsup`, `\liminf`, `\argmax`, `\argmin`, `\det`, `\gcd`, `\Pr` (limit-style operators with under-limits), `\limits`, `\nolimits` (limits placement), `\prod` (n-ary product), `\div`, `\ast`, `\star`, `\circ`, `\oplus`, `\ominus`, `\otimes`, `\odot`, `\bullet` (binary operators), `\leftarrow`, `\uparrow`, `\downarrow`, `\leftrightarrow`, `\Rightarrow`, `\Leftarrow`, `\Leftrightarrow`, `\gets`, `\implies` (arrows), `\boldsymbol`, `\mathit` (math fonts), `\underset` (under-set), `\neq`, `\sim`, `\subset`, `\supset`, `\lor`, `\neg`, `\wedge`, `\vee`, `\parallel` (relations/logic), `\varnothing`, `\complement` (sets), `\cos`, `\tan`, `\ln` (trig/functions), `{a \over b}` (legacy fraction syntax)

## XI. Full Symbol & Environment Coverage

This section exhaustively exercises the remaining parser-supported commands —
Greek variants, the full relation/negated-relation set, extended arrows, a large
miscellaneous-symbol block, every math font family, and the remaining math
environments — so nearly the entire command table is demonstrated at least once.

```bash
# 68. Greek Variants and Extra Letters
officecli add formulas.docx /body --type equation \
  --prop 'formula=\chi, \iota, \kappa, \omega, \tau, \upsilon, \varepsilon, \varphi, \varpi, \varrho, \varsigma, \vartheta, \varkappa, \digamma'

# 69. Relation Symbols
officecli add formulas.docx /body --type equation \
  --prop 'formula=a \cong b \simeq c \asymp d \doteq e, \quad f \propto g, \quad x \prec y \succ z, \quad p \preceq q \succeq r, \quad m \ll n \gg k, \quad \Gamma \models \phi \vdash \psi \dashv \chi \Vdash \omega, \quad u \perp v, \quad \top, \quad a \ni b, \quad S \sqsubset T \sqsubseteq U \sqsupset V \sqsupseteq W, \quad A \subsetneq B \supsetneq C'

# 70. Negated Relations
officecli add formulas.docx /body --type equation \
  --prop 'formula=a \nleq b, \quad c \ngeq d, \quad e \nmid f, \quad A \nsubseteq B, \quad C \nsupseteq D, \quad \nexists x'

# 71. Extended Arrows
officecli add formulas.docx /body --type equation \
  --prop 'formula=a \longleftarrow b \longrightarrow c \longleftrightarrow d, \quad x \longmapsto y, \quad e \hookleftarrow f \hookrightarrow g, \quad p \twoheadrightarrow q \rightsquigarrow r, \quad u \leftharpoonup v \leftharpoondown w \rightharpoonup s \rightharpoondown t, \quad \nearrow \searrow \swarrow \nwarrow, \quad \alpha \curvearrowleft \beta \curvearrowright \gamma, \quad P \impliedby Q'

# 72. Miscellaneous Symbols
officecli add formulas.docx /body --type equation \
  --prop 'formula=\aleph, \beth, \gimel, \daleth, \wp, \Re, \Im, \Sigma, \quad \angle, \measuredangle, \sphericalangle, \triangle, \triangleleft, \triangleright, \quad \square, \blacksquare, \Diamond, \diamond, \diamondsuit, \clubsuit, \heartsuit, \spadesuit, \quad \flat, \sharp, \natural, \dagger, \ddagger, \bigstar, \quad a \amalg b \uplus c \sqcap d \sqcup e \wr f, \quad x \bowtie y \frown z \smile w, \quad p \mp q, \quad \bigtriangledown'

# 73. Math Font Families
officecli add formulas.docx /body --type equation \
  --prop 'formula=\mathfrak{ABCDabcd} \quad \mathsf{ABCDabcd} \quad \mathtt{ABCDabcd} \quad \textbf{ABCDabcd} \quad \textit{ABCDabcd} \quad \textsf{ABCDabcd} \quad \texttt{ABCDabcd}'

# 74. Environments — Bmatrix and Vmatrix
officecli add formulas.docx /body --type equation \
  --prop 'formula=\begin{Bmatrix} a & b \\ c & d \end{Bmatrix} \quad \begin{Vmatrix} a & b \\ c & d \end{Vmatrix}'

# 75. Environments — smallmatrix and array (colspec)
officecli add formulas.docx /body --type equation \
  --prop 'formula=\left(\begin{smallmatrix} 1 & 0 \\ 0 & 1 \end{smallmatrix}\right) \quad \begin{array}{cc} x & y \\ z & w \end{array}'

# 76. Environments — aligned and align (multi alignment points)
officecli add formulas.docx /body --type equation \
  --prop 'formula=\begin{aligned} a &= b \\ c &= d \end{aligned} \qquad \begin{align} a &= b & c &= d \\ e &= f & g &= h \end{align}'

# 77. Environments — gather, split, and substack
officecli add formulas.docx /body --type equation \
  --prop 'formula=\begin{gather} x = 1 \\ y = 2 \end{gather} \qquad \begin{split} a &= b + c \\ &= d \end{split} \qquad \sum_{\substack{i=1 \\ j=1}}^{n} a_{ij}'
```

**Features:**

| Group | Commands |
|-------|----------|
| Greek variants | `\chi` `\iota` `\kappa` `\omega` `\tau` `\upsilon` `\varepsilon` `\varphi` `\varpi` `\varrho` `\varsigma` `\vartheta` `\varkappa` `\digamma` |
| Relations | `\cong` `\simeq` `\asymp` `\doteq` `\propto` `\prec` `\succ` `\preceq` `\succeq` `\ll` `\gg` `\models` `\vdash` `\dashv` `\perp` `\top` `\ni` `\sqsubset` `\sqsubseteq` `\sqsupset` `\sqsupseteq` `\subsetneq` `\supsetneq` `\Vdash` |
| Negated relations | `\nleq` `\ngeq` `\nmid` `\nsubseteq` `\nsupseteq` `\nexists` |
| Extended arrows | `\longleftarrow` `\longrightarrow` `\longleftrightarrow` `\longmapsto` `\hookleftarrow` `\hookrightarrow` `\twoheadrightarrow` `\rightsquigarrow` `\leftharpoonup` `\leftharpoondown` `\rightharpoonup` `\rightharpoondown` `\nearrow` `\searrow` `\swarrow` `\nwarrow` `\curvearrowleft` `\curvearrowright` `\impliedby` |
| Misc symbols | `\aleph` `\beth` `\gimel` `\daleth` `\wp` `\Re` `\Im` `\Sigma` `\angle` `\measuredangle` `\sphericalangle` `\triangle` `\triangleleft` `\triangleright` `\square` `\blacksquare` `\Diamond` `\diamond` `\diamondsuit` `\clubsuit` `\heartsuit` `\spadesuit` `\flat` `\sharp` `\natural` `\dagger` `\ddagger` `\bigstar` `\amalg` `\uplus` `\sqcap` `\sqcup` `\wr` `\bowtie` `\frown` `\smile` `\mp` `\bigtriangledown` |
| Math font families | `\mathfrak` `\mathsf` `\mathtt` `\textbf` `\textit` `\textsf` `\texttt` |
| Environments | `Bmatrix` `Vmatrix` `smallmatrix` `array` (colspec) `aligned` `align` (multi-point) `gather` `split` `substack` |

This section exercises every command the parser recognizes; `\nparallel`
(∦, "not parallel") is included — its forward mapping was added so it now
parses and round-trips symmetrically with the reverse dump.

## Complete Feature Coverage

| Feature | Section |
|---------|---------|
| `formula` (LaTeX-ish math string → OMML) | All sections |
| `mode=display` (block-level oMathPara, centred) | IX |
| `mode=inline` (inline oMath within paragraph) | IX |
| Fractions (`\frac`), radicals (`\sqrt`), sums/integrals (`\sum`, `\int`, `\iiint`) | I, II |
| Binomial (`\binom`), limits (`\lim`), derivatives (`\prime`, `\partial`, `\dot`) | I, II |
| Greek letters (full set: α–Ω, upper and lower) | II, VII, VIII |
| Chemical arrows (`\rightarrow`, `\rightleftharpoons`) | VI |
| Matrix environments (pmatrix, vmatrix, bmatrix, cases) | VIII |
| Auto-sized delimiters (`\left`/`\right` with `[`, `{`, `\langle`, `\lfloor`, `\lceil`) | V, VIII |
| Decorations (`\underbrace`, `\overbrace`, `\overset`, `\cancel`, `\cancelto`, `\boxed`) | VIII |
| Accents (`\bar`, `\vec`, `\tilde`, `\ddot`, `\overline`, `\underline`) | VIII |
| Math fonts (`\mathbb`, `\mathcal`, `\mathbf`, `\mathrm`) | VIII |
| Colored math (`\textcolor`, `\color`) | VIII |
| Spacing control (`\,`, `\;`, `\quad`, `\qquad`) | II, VI, VIII |
| N-ary contour integrals (`\oint`, `\oiint`, `\oiiint`) | X |
| Limit-style operators (`\max`, `\min`, `\sup`, `\inf`, `\limsup`, `\liminf`, `\argmax`, `\argmin`, `\det`, `\gcd`, `\Pr`) | X |
| Limits placement (`\limits`, `\nolimits`), product (`\prod`) | X |
| Binary operators (`\div`, `\ast`, `\star`, `\circ`, `\oplus`, `\ominus`, `\otimes`, `\odot`, `\bullet`) | X |
| Arrows (`\leftarrow`, `\uparrow`, `\downarrow`, `\leftrightarrow`, `\Rightarrow`, `\Leftarrow`, `\Leftrightarrow`, `\gets`, `\implies`) | X |
| Additional math fonts (`\boldsymbol`, `\mathit`), over/under-set (`\underset`) | X |
| Relations/logic/sets (`\neq`, `\sim`, `\subset`, `\supset`, `\lor`, `\neg`, `\wedge`, `\vee`, `\parallel`, `\varnothing`, `\complement`) | X |
| Trig/functions (`\cos`, `\tan`, `\ln`), legacy fraction (`{a \over b}`) | X |
| Greek variants (`\chi`, `\varepsilon`, `\varphi`, `\varkappa`, `\digamma`, …) | XI |
| Full relation set (`\cong`, `\simeq`, `\prec`, `\succ`, `\sqsubseteq`, `\Vdash`, …) and negated relations (`\nleq`, `\nmid`, `\nsubseteq`, `\nexists`, …) | XI |
| Extended arrows (`\longmapsto`, `\hookrightarrow`, `\twoheadrightarrow`, `\rightsquigarrow`, harpoons, diagonals, `\curvearrowleft`, `\impliedby`) | XI |
| Miscellaneous symbols (`\aleph`, `\wp`, `\Re`, `\angle`, `\blacksquare`, suits, `\dagger`, `\bowtie`, `\bigtriangledown`, …) | XI |
| Math font families (`\mathfrak`, `\mathsf`, `\mathtt`, `\textbf`, `\textit`, `\textsf`, `\texttt`) | XI |
| Extra environments (`Bmatrix`, `Vmatrix`, `smallmatrix`, `array`, `aligned`, `align`, `gather`, `split`, `substack`) | XI |

## Inspect the Generated File

```bash
# List all equations in the document
officecli query formulas.docx equation

# Inspect a specific equation node
officecli get formulas.docx "/body/oMathPara[1]"

# Get the second equation (inline mode is an oMath, not oMathPara)
officecli get formulas.docx "/body/p[last()]/oMath[1]"
```
