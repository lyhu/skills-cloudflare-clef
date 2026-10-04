/**
 * Node/TypeScript template: reuse scripts/evaluate.py for HTTP, retries, and
 * validation. Requires Python 3.9+; no npm runtime dependencies.
 * Pass an absolute path to the installed evaluate.py. CLEF_* variables are
 * inherited. execFile passes arguments directly, without invoking a shell.
 */
import { execFile } from "node:child_process";

export type NoulQuestion = { type: "noul"; instructions: string };
export type ChoiceQuestion = { type: "choice"; instructions: string; choices: string[] };
export type ScoreQuestion = { type: "score"; instructions: string; levels: string[] };
export type Question = NoulQuestion | ChoiceQuestion | ScoreQuestion;

export type NoulAnswer = { type: "noul"; noul: number };
export type ChoiceAnswer = {
  type: "choice";
  choice: string;
  confidence: number;
  probabilities: Record<string, number>;
};
export type ScoreAnswer = {
  type: "score";
  score: number;
  confidence: number;
  legend: Record<string, string>;
  probabilities: Record<string, number>;
};
export type ClefError = {
  error: string;
  message: string;
  fallback_used: true;
  http_status?: number;
};
export type ClefResult = NoulAnswer | ChoiceAnswer | ScoreAnswer | ClefError;

export function evaluateClef(scriptPath: string, state: string, question: NoulQuestion): Promise<NoulAnswer | ClefError>;
export function evaluateClef(scriptPath: string, state: string, question: ChoiceQuestion): Promise<ChoiceAnswer | ClefError>;
export function evaluateClef(scriptPath: string, state: string, question: ScoreQuestion): Promise<ScoreAnswer | ClefError>;
export function evaluateClef(scriptPath: string, state: string, question: Question): Promise<ClefResult>;
export function evaluateClef(scriptPath: string, state: string, question: Question): Promise<ClefResult> {
  const args = [scriptPath, `--state=${state}`, "--type", question.type, `--instructions=${question.instructions}`];
  if (question.type === "choice") args.push("--choices", ...question.choices);
  if (question.type === "score") args.push("--levels", ...question.levels);
  return new Promise((resolve) => {
    execFile("python3", args, { encoding: "utf8" }, (error, stdout) => {
      try {
        // The bundled Python CLI validates the full answer before emitting it.
        const result = JSON.parse(stdout) as ClefResult;
        if (result && typeof result === "object" && "error" in result) {
          resolve(result);
        } else if (!error && result?.type === question.type) {
          resolve(result);
        } else {
          throw new Error("The CLI did not return a matching verdict");
        }
      } catch {
        resolve({
          error: "CLEF_CLIENT_ERROR",
          message: "Could not run the Python CLI or parse its output; check Python and scriptPath",
          fallback_used: true,
        });
      }
    });
  });
}
