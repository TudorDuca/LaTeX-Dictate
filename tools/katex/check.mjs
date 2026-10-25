// Reads a JSON array of LaTeX strings on stdin and prints a JSON array of booleans:
// true if KaTeX renders the string in display mode without a parse error.
import katex from "katex";

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  const formulas = JSON.parse(input);
  const ok = formulas.map((f) => {
    try {
      katex.renderToString(f, { displayMode: true, throwOnError: true, strict: "ignore" });
      return true;
    } catch {
      return false;
    }
  });
  process.stdout.write(JSON.stringify(ok));
});
