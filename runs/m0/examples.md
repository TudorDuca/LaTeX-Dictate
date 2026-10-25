# Examples: m0

## equations

### human_0024 (human)

- **reference:** `are\\the\\amplitudes\\of`
- dataset Whisper transcript: the endless of D
- **whisper-raw:** `the Amplice of D`
  - transcript: the Amplice of D
- **paper@dataset-asr:** `\mathcal\\D_{\infty}`
- **paper@whisper-turbo:** `\bar{d}`
  - transcript: the Amplice of D
- **qwen3-4b@whisper-turbo:** `\text{Amplice of } D`
  - transcript: the Amplice of D
- **qwen3-4b@oracle:** `The amplitude of d`
- **qwen2-audio@e2e:** `\sum_{i=1}^{n}\frac{1}{i}`

### tts_0008 (tts)

- **reference:** `t^{\prime}=\gamma\left(\tau+\beta\\x\right)x^{\prime}=\gamma\left(x+\beta\\c\tau\right)`
- dataset Whisper transcript: T prime equals gamma times tau plus gamma times beta times X and X prime equals gamma times X plus gamma times beta times C tau.
- **whisper-raw:** `T prime equals gamma times tau plus gamma times beta times x and x prime equals gamma times x plus gamma times beta times c tau`
  - transcript: T prime equals gamma times tau plus gamma times beta times x and x prime equals gamma times x plus gamma times beta times c tau.
- **paper@dataset-asr:** `t^{\prime}=\gamma(t+\beta\\x)\,,x^{\prime}=\gamma(x+\beta\\c\tau)\,`
- **paper@whisper-turbo:** `t^{\prime}=\gamma(t+\beta\\x)\,,x^{\prime}=\gamma(x+\beta\\ct)\,`
  - transcript: T prime equals gamma times tau plus gamma times beta times x and x prime equals gamma times x plus gamma times beta times c tau.
- **qwen3-4b@whisper-turbo:** `T' = γ τ + γ β x x' = γ x + γ β c τ`
  - transcript: T prime equals gamma times tau plus gamma times beta times x and x prime equals gamma times x plus gamma times beta times c tau.
- **qwen3-4b@oracle:** `t' = γ τ + γ β x x' = γ x + γ β c τ`
- **qwen2-audio@e2e:** `T = \gamma \tau + \gamma \beta x + \gamma \beta x^2 + \beta^2 c^2 \tau`

### human_0026 (human)

- **reference:** `{A_{2}f(x)}\leq\\M^{0}f(x)`
- dataset Whisper transcript: a superscript 2f of x is less than or equal to m superscript 0 times f of x.
- **whisper-raw:** `a superscript to f of x is less than or equal to m superscript 0 times f of x`
  - transcript: a superscript to f of x is less than or equal to m superscript 0 times f of x.
- **paper@dataset-asr:** `A^{2}F(x)\leq\\M^{0}F(x)`
- **paper@whisper-turbo:** `A^{2}F(x)\leq\\M^{0}F(x)`
  - transcript: a superscript to f of x is less than or equal to m superscript 0 times f of x.
- **qwen3-4b@whisper-turbo:** `a^f(x) ≤ m^0 × f(x)`
  - transcript: a superscript to f of x is less than or equal to m superscript 0 times f of x.
- **qwen3-4b@oracle:** `x_{2f} \leq M^0 \cdot f(x)`
- **qwen2-audio@e2e:** `\textit{a supercript 2 f of x is less than or equal to m supercript 0 times f of x}`

### human_0002 (human)

- **reference:** `\sigma^{\pm}=\frac{1}{2}(\sigma^{x}\pm\\i\sigma^{y})`
- dataset Whisper transcript: Sigma plus minus equals 1 over 2 of Sigma superscript X plus minus I times Sigma superscript Y.
- **whisper-raw:** `Sigma plus minus equals 1 over 2 of Sigma superscript X plus minus I times Sigma superscript Y`
  - transcript: Sigma plus minus equals 1 over 2 of Sigma superscript X plus minus I times Sigma superscript Y.
- **paper@dataset-asr:** `\sigma^{\pm}=\frac{1}{2}(\sigma^{x}\pm\\i\sigma^{y})`
- **paper@whisper-turbo:** `\sigma^{\pm}=\frac{1}{2}(\sigma^{x}\pm\\i\sigma^{y})`
  - transcript: Sigma plus minus equals 1 over 2 of Sigma superscript X plus minus I times Sigma superscript Y.
- **qwen3-4b@whisper-turbo:** `\sigma_+ - \sigma_- = \frac{1}{2} \sigma^X_+ - i \sigma^Y_+`
  - transcript: Sigma plus minus equals 1 over 2 of Sigma superscript X plus minus I times Sigma superscript Y.
- **qwen3-4b@oracle:** `\sigma_\pm = \frac{1}{2} (\sigma_x \pm i \sigma_y)`
- **qwen2-audio@e2e:** `\sigma^2_x + \mu^2_y`

### human_0016 (human)

- **reference:** `\lim_{{x\to\\4}}\sqrt{x}`
- dataset Whisper transcript: Limit as x approaches 4 of square root of x.
- **whisper-raw:** `Limit as x approaches 4 of square root of x`
  - transcript: Limit as x approaches 4 of square root of x.
- **paper@dataset-asr:** `\lim_{{x\to\\4}}\sqrt{x}`
- **paper@whisper-turbo:** `\lim_{{x\to\\4}}\sqrt{x}`
  - transcript: Limit as x approaches 4 of square root of x.
- **qwen3-4b@whisper-turbo:** `\lim_{x \to 4} \sqrt{x}`
  - transcript: Limit as x approaches 4 of square root of x.
- **qwen3-4b@oracle:** `\lim_{x \to 4} \sqrt{x}`
- **qwen2-audio@e2e:** `\lim_{x\to\infty}\frac{4x^2}{\sqrt x}`

### human_0032 (human)

- **reference:** `\csc\\x=\frac{1}{\sin\\x}`
- dataset Whisper transcript: cos x is equal to 1 divided by sin x.
- **whisper-raw:** `Cosecond x is equal to 1 divided by sin x`
  - transcript: Cosecond x is equal to 1 divided by sin x.
- **paper@dataset-asr:** `\cot\\x=\frac{1}{\tan\\x}`
- **paper@whisper-turbo:** `\csc\\x=\frac{1}{\sin\\x}`
  - transcript: Cosecond x is equal to 1 divided by sin x.
- **qwen3-4b@whisper-turbo:** `\cos(2x) = \frac{1}{\sin(x)}`
  - transcript: Cosecond x is equal to 1 divided by sin x.
- **qwen3-4b@oracle:** `\csc x = \frac{1}{\sin x}`
- **qwen2-audio@e2e:** `\cos(x)=1`

## sentences

### human_0007 (human)

- **reference:** `Then we may add an edge along the segment $ab$, because none of the edges from $A_{0}$ to $B_{1}$ cross it.`
- dataset Whisper transcript: Then we made an edge along the segment AB because none of the edges from A sub 0 to B sub 1 cross it.
- **whisper-raw:** `Then we made an edge along the segment AB because none of the edges from A sub 0 to B sub 1 cross it.`
  - transcript: Then we made an edge along the segment AB because none of the edges from A sub 0 to B sub 1 cross it.
- **paper@dataset-asr:** `Then we make an edge along the segment $ab$ because none of the edges from $a_{0}$ to $b_{1}$ cross it.`
- **paper@whisper-turbo:** `Then we make an edge along the segment $ab$ because none of the edges from $a_{0}$ to $b_{1}$ cross it.`
  - transcript: Then we made an edge along the segment AB because none of the edges from A sub 0 to B sub 1 cross it.
- **qwen3-4b@whisper-turbo:** `Then we made an edge along the segment $AB$ because none of the edges from $A_0$ to $B_1$ cross it.`
  - transcript: Then we made an edge along the segment AB because none of the edges from A sub 0 to B sub 1 cross it.
- **qwen3-4b@oracle:** `Then we may add an edge along the segment line segment $ab$, because none of the edges from $A_0$ to $B_1$ cross it.`
- **qwen2-audio@e2e:** `The sentence is: Then we may take an $h$ along the segment $a$ because none of the edges from $a$ sub $0$ to $b$ sub $1$ cross it.`

### human_0006 (human)

- **reference:** `Both of these expressions use $l=2$ in Prop.\ .`
- dataset Whisper transcript: Both of these expressions use l equals 2 in prop.
- **whisper-raw:** `Both of these expressions use l equals 2 in prop.`
  - transcript: Both of these expressions use l equals 2 in prop.
- **paper@dataset-asr:** `Both of these expressions use $l=2$ in Prop.~.`
- **paper@whisper-turbo:** `Both of these expressions use $l=2$ in Prop.~.`
  - transcript: Both of these expressions use l equals 2 in prop.
- **qwen3-4b@whisper-turbo:** `Both of these expressions use $l = 2$ in prop.`
  - transcript: Both of these expressions use l equals 2 in prop.
- **qwen3-4b@oracle:** `Both of these expressions use $l = 2$ in Prop.`
- **qwen2-audio@e2e:** `The sentence is: Both of these expressions use $l = 2$ in prop.`

### human_0004 (human)

- **reference:** `An understanding of the conformal weights equation of the graviton/photon/dilaton perturbations, solved for in this paper, is of crucial importance to the eventual goal of constructing a holographic dual to our customizable $\mathrm{AdS}_{2}\times\\S^{2}$ bulk.`
- dataset Whisper transcript: An understanding of the conformal weights equation of the graviton-photon dilation perturbations solved for in this paper is of crucial importance to the eventual goal of constructing a holographic dual to our customizable anti-de-sitter 2x2 dimensional sphere book.
- **whisper-raw:** `An understanding of the conformal weights equation of the graviton-photon dilation perturbations solved for in this paper is of crucial importance to the eventual goal of constructing a holographic dual to our customizable anti-desiter two-times two-dimensional sphere book.`
  - transcript: An understanding of the conformal weights equation of the graviton-photon dilation perturbations solved for in this paper is of crucial importance to the eventual goal of constructing a holographic dual to our customizable anti-desiter two-times two-dimensional sphere book.
- **paper@dataset-asr:** `An understanding of the conformal weights equation of the graviton, $\phi$, and the gravitron, $\pi$, perturbations solved for in this paper is of crucial importance to the future goal of constructing a holographic dual to our theory on $AdS_{2}\times\\S^{2}$.`
- **paper@whisper-turbo:** `An understanding of the conformal weights equation of the graviton, $\phi$, and the gravitron, $\pi$, dilatation perturbations solved for in this paper is of crucial importance to the future goal of constructing a holographic dual to our theory on $S^{2}\times\\S^{2}$, as it will allow us to identify the appropriate boundary conditions for the gravitons and the gravitron fields.`
  - transcript: An understanding of the conformal weights equation of the graviton-photon dilation perturbations solved for in this paper is of crucial importance to the eventual goal of constructing a holographic dual to our customizable anti-desiter two-times two-dimensional sphere book.
- **qwen3-4b@whisper-turbo:** `An understanding of the conformal weights equation of the graviton-photon dilation perturbations solved for in this paper is of crucial importance to the eventual goal of constructing a holographic dual to our customizable anti-desiter two-times two-dimensional sphere book.`
  - transcript: An understanding of the conformal weights equation of the graviton-photon dilation perturbations solved for in this paper is of crucial importance to the eventual goal of constructing a holographic dual to our customizable anti-desiter two-times two-dimensional sphere book.
- **qwen3-4b@oracle:** `An understanding of the conformal weights equation of the graviton/photon/dilaton perturbations, solved for in this paper, is of crucial importance to the eventual goal of constructing a holographic dual to our customizable anti-de Sitter two-time two-dimensional sphere bulk.`
- **qwen2-audio@e2e:** `An understanding of the conformal weights equation of the gravitational photogeneration perturbation solved for in this paper is of crucial importance to the eventual goal of constructing a holographic dual to our customizable anti-de Sitter two times two dimensional sphere book.`

### human_0003 (human)

- **reference:** `Although the CDFs are well scaled using the scaling variable $\tilde{v}$, the statistical precision is insufficient to discuss whether the form of the distribution function deviates from the classical theory.`
- dataset Whisper transcript: While through the capital C, capital D, capital Fs are well scaled using the scaling variable V tilde, the statistical precision is infuriacent to discuss whether the form of the distribution function deviates from the classical theory.
- **whisper-raw:** `While the C, D, Fs are well scaled using the scaling variable V tilde, the statistical precision is infuriasing to discuss whether the form of the distribution function deviates from the classical theory.`
  - transcript: While the C, D, Fs are well scaled using the scaling variable V tilde, the statistical precision is infuriasing to discuss whether the form of the distribution function deviates from the classical theory.
- **paper@dataset-asr:** `While the $CD$FS are well scale using the scaling variable $\tilde{v}$, the statistical precision is necessarily small to discuss whether the form of the distribution function deviates from the classical theory.`
- **paper@whisper-turbo:** `While the CDSS are well scale using the scaling variable $\tilde{v}$, the statistical precision is insufficient to discuss whether the form of the distribution function deviates from the classical theory.`
  - transcript: While the C, D, Fs are well scaled using the scaling variable V tilde, the statistical precision is infuriasing to discuss whether the form of the distribution function deviates from the classical theory.
- **qwen3-4b@whisper-turbo:** `While the C, D, Fs are well scaled using the scaling variable $\tilde{V}$, the statistical precision is frustrating to discuss whether the form of the distribution function deviates from the classical theory.`
  - transcript: While the C, D, Fs are well scaled using the scaling variable V tilde, the statistical precision is infuriasing to discuss whether the form of the distribution function deviates from the classical theory.
- **qwen3-4b@oracle:** `Although the CDFs are well scaled using the scaling variable $\tilde{v}$, the statistical precision is insufficient to discuss whether the form of the distribution function deviates from the classical theory.`
- **qwen2-audio@e2e:** `Through the capital $C$, capital $G$, capital $E_{\text{fs}}$, and scaled using the scaling variable $V_{\text{chill}}$, the statistical precision is influenced to discuss whether the form of the distribution function differs from the classical theory.`

### human_0002 (human)

- **reference:** `The resulting system encodes the property that $h$ is a sum-of-squares.`
- dataset Whisper transcript: The resulting system includes the probability that h is the sum of squares.
- **whisper-raw:** `The resulting system includes the probability that h is the sum of squares.`
  - transcript: The resulting system includes the probability that h is the sum of squares.
- **paper@dataset-asr:** `The resulting system includes the probability that $H$ is a sum of squares.`
- **paper@whisper-turbo:** `The resulting system includes the probability that $H$ is a sum of squares.`
  - transcript: The resulting system includes the probability that h is the sum of squares.
- **qwen3-4b@whisper-turbo:** `The resulting system includes the probability that $h$ is the sum of squares.`
  - transcript: The resulting system includes the probability that h is the sum of squares.
- **qwen3-4b@oracle:** `The resulting system encodes the property that $h$ is a sum-of-squares.`
- **qwen2-audio@e2e:** `The resulting system includes the four proper planes that $ash$ is a sum of squares.`

### human_0009 (human)

- **reference:** `In processes like $N+N\to\\l+l$, the number density of initial particles are not small.`
- dataset Whisper transcript: In processes like N plus N goes to L plus L, the number density of initial particles are not small.
- **whisper-raw:** `In processes like N plus N goes to L plus L, the number density of initial particles are not small.`
  - transcript: In processes like N plus N goes to L plus L, the number density of initial particles are not small.
- **paper@dataset-asr:** `In processes like $p^{+}p^{-}\to\\l^{+}l^{-}$ the number density of initial particles are not small.`
- **paper@whisper-turbo:** `In processes like $p^{+}p^{-}\to\\l^{+}l^{-}$ the number density of initial particles are not small.`
  - transcript: In processes like N plus N goes to L plus L, the number density of initial particles are not small.
- **qwen3-4b@whisper-turbo:** `In processes like $N + N \to L + L$, the number density of initial particles are not small.`
  - transcript: In processes like N plus N goes to L plus L, the number density of initial particles are not small.
- **qwen3-4b@oracle:** `In processes like $n + n \to l + l$, the number density of initial particles are not small.`
- **qwen2-audio@e2e:** `In processes like $ capital N plus capital N goes to $ a plus $ m$, the number density of initial particles are not small.`

## own

### f07 (own)

- **reference:** `f'(x)=\lim_{h\to 0}\frac{f(x+h)-f(x)}{h}`
- **whisper-raw:** `f prime of x is equal to the limit when h goes to 0 of f of a x plus h minus f of x divided by h`
  - transcript: f prime of x is equal to the limit when h goes to 0 of f of a x plus h minus f of x divided by h.
- **paper@whisper-turbo:** `f^{\prime}(x)=\lim_{h\to\\0}\frac{f(x+h)-f(x)}{h}`
  - transcript: f prime of x is equal to the limit when h goes to 0 of f of a x plus h minus f of x divided by h.
- **qwen3-4b@whisper-turbo:** `f'(x) = \lim_{h \to 0} \frac{f(a x + h) - f(x)}{h}`
  - transcript: f prime of x is equal to the limit when h goes to 0 of f of a x plus h minus f of x divided by h.
- **qwen2-audio@e2e:** `\lim_{h\to 0}\frac{f(x+h)-f(x)}{h}`

### f17 (own)

- **reference:** `\|x\|_{2}=\sqrt{\sum_{i=1}^{n}x_{i}^{2}}`
- **whisper-raw:** `2 norm of x equals the square root of the sum from i equals 1 to n of xi squared`
  - transcript: 2 norm of x equals the square root of the sum from i equals 1 to n of xi squared.
- **paper@whisper-turbo:** `\|x\|_{2}=\sqrt{\sum_{i=1}^{n}x_{i}^{2}}`
  - transcript: 2 norm of x equals the square root of the sum from i equals 1 to n of xi squared.
- **qwen3-4b@whisper-turbo:** `\|x\| = \sqrt{\sum_{i=1}^n x_i^2}`
  - transcript: 2 norm of x equals the square root of the sum from i equals 1 to n of xi squared.
- **qwen2-audio@e2e:** `\sqrt{\sum_{i=1}^{n} x_i^2}`

### f05 (own)

- **reference:** `\sqrt{x^{2}+1}`
- **whisper-raw:** `Square root of x squared plus 1`
  - transcript: Square root of x squared plus 1.
- **paper@whisper-turbo:** `\sqrt{x^{2}+1}`
  - transcript: Square root of x squared plus 1.
- **qwen3-4b@whisper-turbo:** `\sqrt{x^2 + 1}`
  - transcript: Square root of x squared plus 1.
- **qwen2-audio@e2e:** `x^2+1`

### f10 (own)

- **reference:** `\binom{n}{k}=\frac{n!}{k!(n-k)!}`
- **whisper-raw:** `n choose k is equal to n factorial divided by k factorial times n minus k factorial`
  - transcript: n choose k is equal to n factorial divided by k factorial times n minus k factorial.
- **paper@whisper-turbo:** `\binom{n}{k}=\frac{n!}{k!\\(n-k)!}`
  - transcript: n choose k is equal to n factorial divided by k factorial times n minus k factorial.
- **qwen3-4b@whisper-turbo:** `\binom{n}{k} = \frac{n!}{k!(n-k)!}`
  - transcript: n choose k is equal to n factorial divided by k factorial times n minus k factorial.
- **qwen2-audio@e2e:** `\frac{n!}{k! (n-k)!}`

### f18 (own)

- **reference:** `\hat{\beta}=(X^{\top}X)^{-1}X^{\top}y`
- **whisper-raw:** `Beta hat equals x transpose times x inverse times x transpose y`
  - transcript: Beta hat equals x transpose times x inverse times x transpose y.
- **paper@whisper-turbo:** `\hat{\beta}=X^{T}X^{-1}X^{T}Y`
  - transcript: Beta hat equals x transpose times x inverse times x transpose y.
- **qwen3-4b@whisper-turbo:** `\hat{\beta} = (\mathbf{x}^T \mathbf{x})^{-1} \mathbf{x}^T \mathbf{y}`
  - transcript: Beta hat equals x transpose times x inverse times x transpose y.
- **qwen2-audio@e2e:** `\beta = x^{\transpose} \cdot x^{-1} \cdot x^{\transpose}`

### f13 (own)

- **reference:** `\mathbb{E}[X]=\sum_{x}x\,p(x)`
- **whisper-raw:** `E equals the sum over x of x times P`
  - transcript: E equals the sum over x of x times P .
- **paper@whisper-turbo:** `E=\sum_{x}xP(x)`
  - transcript: E equals the sum over x of x times P .
- **qwen3-4b@whisper-turbo:** `E = \sum x \cdot P`
  - transcript: E equals the sum over x of x times P .
- **qwen2-audio@e2e:** `\sum_{x}^{n} x^2`
