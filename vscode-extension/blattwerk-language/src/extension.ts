import { execFile } from "child_process";
import * as path from "path";
import * as vscode from "vscode";

type CliSeverity = "warning" | "error" | "info";

type CliRange = {
  start: { line: number; character: number };
  end: { line: number; character: number };
};

type CliDiagnostic = {
  code: string;
  message: string;
  severity: CliSeverity;
  blockIndex?: number | null;
  blockType?: string | null;
  range: CliRange;
};

type CliPayload = {
  source: string;
  file: string;
  diagnostics: CliDiagnostic[];
  error?: string;
};

const DIAGNOSTICS_SOURCE = "blattwerk-validator";

export function activate(context: vscode.ExtensionContext): void {
  const diagnosticsCollection = vscode.languages.createDiagnosticCollection("blattwerk");
  context.subscriptions.push(diagnosticsCollection);

  const pendingValidation = new Map<string, NodeJS.Timeout>();

  const scheduleValidation = (document: vscode.TextDocument, delayMs = 350): void => {
    if (!shouldValidateDocument(document)) {
      diagnosticsCollection.delete(document.uri);
      return;
    }

    const key = document.uri.toString();
    const existing = pendingValidation.get(key);
    if (existing) {
      clearTimeout(existing);
    }

    const handle = setTimeout(() => {
      pendingValidation.delete(key);
      void runValidation(document, diagnosticsCollection);
    }, delayMs);
    pendingValidation.set(key, handle);
  };

  context.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument((document) => scheduleValidation(document, 50)),
    vscode.workspace.onDidSaveTextDocument((document) => scheduleValidation(document, 50)),
    vscode.workspace.onDidCloseTextDocument((document) => {
      diagnosticsCollection.delete(document.uri);
      const key = document.uri.toString();
      const handle = pendingValidation.get(key);
      if (handle) {
        clearTimeout(handle);
        pendingValidation.delete(key);
      }
    }),
    vscode.workspace.onDidChangeTextDocument((event) => scheduleValidation(event.document)),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("blattwerk.validateDocument", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        void vscode.window.showInformationMessage("No active editor document.");
        return;
      }

      await runValidation(editor.document, diagnosticsCollection, true);
      void vscode.window.showInformationMessage("Blattwerk validation finished.");
    }),
  );

  context.subscriptions.push(
    vscode.languages.registerFoldingRangeProvider(
      [{ language: "markdown", scheme: "file" }],
      {
        provideFoldingRanges(document: vscode.TextDocument): vscode.FoldingRange[] {
          return computeFoldingRanges(document);
        },
      },
    ),
  );

  for (const document of vscode.workspace.textDocuments) {
    scheduleValidation(document, 10);
  }
}

export function deactivate(): void {
  // no-op
}

function shouldValidateDocument(document: vscode.TextDocument): boolean {
  if (document.languageId !== "markdown") {
    return false;
  }

  const config = vscode.workspace.getConfiguration("blattwerk");
  const enabled = config.get<boolean>("diagnostics.enable", true);
  if (!enabled) {
    return false;
  }

  const text = document.getText();
  const hasFrontmatter = text.startsWith("---\n") || text.startsWith("---\r\n");
  const hasDirective = /(^|\n)\s*:::(material|info|task|subtask|answer|solution|columns|nextcol|endcolumns|help|hilfe)\b/m.test(text);
  return hasFrontmatter || hasDirective;
}

async function runValidation(
  document: vscode.TextDocument,
  collection: vscode.DiagnosticCollection,
  showErrors = false,
): Promise<void> {
  try {
    const payload = await executeDiagnosticsCli(document);
    const diagnostics = toVscodeDiagnostics(payload.diagnostics, document);
    collection.set(document.uri, diagnostics);

    if (showErrors && payload.error) {
      void vscode.window.showErrorMessage(`Blattwerk diagnostics failed: ${payload.error}`);
    }
  } catch (error) {
    collection.delete(document.uri);
    if (showErrors) {
      const message = error instanceof Error ? error.message : String(error);
      void vscode.window.showErrorMessage(`Blattwerk diagnostics failed: ${message}`);
    }
  }
}

function executeDiagnosticsCli(document: vscode.TextDocument): Promise<CliPayload> {
  const config = vscode.workspace.getConfiguration("blattwerk");
  const pythonCommand = config.get<string>("diagnostics.pythonCommand", "python");
  const cliModule = config.get<string>("diagnostics.cliModule", "app.cli.blatt_diagnostics_cli");
  const extraArgs = config.get<string[]>("diagnostics.extraArgs", []);

  const workspaceFolder = vscode.workspace.getWorkspaceFolder(document.uri);
  const cwd = workspaceFolder?.uri.fsPath ?? path.dirname(document.uri.fsPath);

  const args = ["-m", cliModule, "--file", document.uri.fsPath, ...extraArgs];

  return new Promise<CliPayload>((resolve, reject) => {
    execFile(
      pythonCommand,
      args,
      { cwd, windowsHide: true, maxBuffer: 1024 * 1024 },
      (error, stdout, stderr) => {
        if (error) {
          reject(new Error(stderr || error.message));
          return;
        }

        try {
          const payload = JSON.parse(stdout) as CliPayload;
          resolve(payload);
        } catch (parseError) {
          const parseMessage = parseError instanceof Error ? parseError.message : String(parseError);
          reject(new Error(`Invalid diagnostics JSON: ${parseMessage}`));
        }
      },
    );
  });
}

function toVscodeDiagnostics(items: CliDiagnostic[], document: vscode.TextDocument): vscode.Diagnostic[] {
  return items.map((item) => {
    const range = toRange(item.range, document);
    const diagnostic = new vscode.Diagnostic(range, item.message, toSeverity(item.severity));
    diagnostic.source = DIAGNOSTICS_SOURCE;
    diagnostic.code = item.code;
    return diagnostic;
  });
}

function toRange(range: CliRange, document: vscode.TextDocument): vscode.Range {
  const maxLine = Math.max(0, document.lineCount - 1);
  const safeStartLine = clamp(range.start.line, 0, maxLine);
  const safeEndLine = clamp(range.end.line, safeStartLine, maxLine);

  const startLineLength = document.lineAt(safeStartLine).text.length;
  const endLineLength = document.lineAt(safeEndLine).text.length;

  const startCharacter = clamp(range.start.character, 0, startLineLength);
  const endCharacter = clamp(range.end.character, startCharacter, endLineLength);

  return new vscode.Range(
    new vscode.Position(safeStartLine, startCharacter),
    new vscode.Position(safeEndLine, endCharacter),
  );
}

function toSeverity(value: CliSeverity): vscode.DiagnosticSeverity {
  switch (value) {
    case "error":
      return vscode.DiagnosticSeverity.Error;
    case "info":
      return vscode.DiagnosticSeverity.Information;
    default:
      return vscode.DiagnosticSeverity.Warning;
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function computeFoldingRanges(document: vscode.TextDocument): vscode.FoldingRange[] {
  const ranges: vscode.FoldingRange[] = [];
  const blockStack: number[] = [];
  const frontmatterLines: number[] = [];

  for (let i = 0; i < document.lineCount; i += 1) {
    const line = document.lineAt(i).text.trim();

    if (line === "---") {
      frontmatterLines.push(i);
      if (frontmatterLines.length === 2) {
        const start = frontmatterLines[0];
        const end = frontmatterLines[1];
        if (end > start + 1) {
          ranges.push(new vscode.FoldingRange(start, end, vscode.FoldingRangeKind.Region));
        }
      }
      continue;
    }

    if (/^:::(\w+).*:::$/.test(line)) {
      continue;
    }

    if (/^:::(\w+)/.test(line)) {
      blockStack.push(i);
      continue;
    }

    if (line === ":::") {
      const start = blockStack.pop();
      if (typeof start === "number" && i > start + 1) {
        ranges.push(new vscode.FoldingRange(start, i, vscode.FoldingRangeKind.Region));
      }
    }
  }

  return ranges;
}
