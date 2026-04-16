import * as vscode from 'vscode';

/**
 * Pith VS Code Extension — Template
 *
 * This is a starting point for the community to build upon.
 * See README.md for the planned architecture.
 */

export function activate(context: vscode.ExtensionContext) {
    console.log('Pith extension activated');

    // Command: Optimize Selection
    const optimizeCmd = vscode.commands.registerCommand(
        'pith.optimizeSelection',
        async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }

            const selection = editor.selection;
            const text = editor.document.getText(selection);

            if (!text) {
                vscode.window.showWarningMessage('No text selected');
                return;
            }

            try {
                const optimized = await optimizeText(text);
                editor.edit(editBuilder => {
                    editBuilder.replace(selection, optimized);
                });
                vscode.window.showInformationMessage(
                    `Pith: Optimized (saved ${text.length - optimized.length} chars)`
                );
            } catch (err) {
                vscode.window.showErrorMessage(`Pith optimization failed: ${err}`);
            }
        }
    );

    // Command: Check for Injection
    const checkCmd = vscode.commands.registerCommand(
        'pith.checkInjection',
        async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }

            const text = editor.document.getText(editor.selection) ||
                         editor.document.getText();

            try {
                const result = await checkInjection(text);
                if (result.is_injection) {
                    vscode.window.showWarningMessage(
                        `Pith: Injection detected! Score: ${result.score} — ` +
                        `Patterns: ${result.matched_patterns.join(', ')}`
                    );
                } else {
                    vscode.window.showInformationMessage(
                        'Pith: No injection patterns detected'
                    );
                }
            } catch (err) {
                vscode.window.showErrorMessage(`Pith check failed: ${err}`);
            }
        }
    );

    context.subscriptions.push(optimizeCmd, checkCmd);
}

export function deactivate() {}

// --- Pith API calls ---

interface InjectionResult {
    is_injection: boolean;
    score: number;
    matched_patterns: string[];
}

async function getPithUrl(): Promise<string> {
    const config = vscode.workspace.getConfiguration('pith');
    const mode = config.get<string>('mode', 'local');

    if (mode === 'cloud') {
        return 'https://api.pithtoken.ai';
    }
    const port = config.get<number>('localPort', 8000);
    return `http://localhost:${port}`;
}

async function optimizeText(text: string): Promise<string> {
    const baseUrl = await getPithUrl();

    // TODO: Implement /v1/optimize endpoint call
    // For now, use CLI fallback
    vscode.window.showInformationMessage(
        'Pith: Optimize endpoint not yet implemented. ' +
        'Use `pith optimize "your text"` from terminal.'
    );
    return text;
}

async function checkInjection(text: string): Promise<InjectionResult> {
    const baseUrl = await getPithUrl();

    // TODO: Implement /v1/check endpoint call
    // For now, use CLI fallback
    vscode.window.showInformationMessage(
        'Pith: Check endpoint not yet implemented. ' +
        'Use `pith check "your text"` from terminal.'
    );
    return { is_injection: false, score: 0, matched_patterns: [] };
}
