import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as path from 'path';

export function activate(context: vscode.ExtensionContext) {
    console.log('Firmware Analysis Tool "FAT" is now active (auto-start).');

    // 1) Immediately run analysis when the extension activates.
    runAnalysisAndShowCFG();
}

async function runAnalysisAndShowCFG() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        vscode.window.showErrorMessage('No workspace folder open.');
        return;
    }

    const workspacePath = workspaceFolders[0].uri.fsPath;

    // Paths to your Python scripts and files
    const scriptPath = path.join(workspacePath, 'rda_disassembler_enhanced.py');
    const generateReportPath = path.join(workspacePath, 'generate_report.py');
    const firmwarePath = path.join(workspacePath, 'firmware', 'latest_firmware.bin');
    const logPath = path.join(workspacePath, 'firmware', 'disassembly.log');
    const reportPath = path.join(workspacePath, 'firmware', 'report.md');
    const cfgDotPath = path.join(workspacePath, 'firmware', 'cfg.dot');
    const cfgPngPath = path.join(workspacePath, 'firmware', 'cfg.png');

    // 2) Run the firmware analysis
    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "Analyzing Firmware (auto-run)...",
        cancellable: false
    }, async () => {

        // (A) Disassembler
        await runCommand(`python3 "${scriptPath}" "${firmwarePath}"`, workspacePath);

        // (B) Possibly convert cfg.dot to cfg.png:
        //     dot -Tpng cfg.dot -o cfg.png
        // Only do this if you generate .dot automatically.
        // Adjust path if 'dot' is not in your PATH or you need a full path.
        await runCommand(`dot -Tpng "${cfgDotPath}" -o "${cfgPngPath}"`, workspacePath);

        // (C) Generate report
        await runCommand(`python3 "${generateReportPath}" "${logPath}" "${reportPath}"`, workspacePath);

        vscode.window.showInformationMessage('Firmware analysis completed successfully (auto-run)!');

        // 3) Show the CFG image in a webview
        showCFGWebview(cfgPngPath);
    });
}

/**
 * Spawns a shell command & returns a Promise that resolves/fails on completion.
 */
function runCommand(command: string, cwd: string): Promise<void> {
    return new Promise<void>((resolve, reject) => {
        exec(command, { cwd }, (error, stdout, stderr) => {
            if (error) {
                vscode.window.showErrorMessage(`Command failed: ${error.message}`);
                reject(error);
            } else {
                resolve();
            }
        });
    });
}

/**
 * Opens a new webview panel and displays the CFG image.
 */
function showCFGWebview(cfgPath: string) {
    const panel = vscode.window.createWebviewPanel(
        'firmwareCFG',         // internal identifier
        'Firmware Control Flow Graph', // title in the tab
        vscode.ViewColumn.One, // show in the first editor column
        {
            enableScripts: true // if you need JS in the webview
        }
    );

    // Convert local file path to a webview URI
    const cfgUri = panel.webview.asWebviewUri(vscode.Uri.file(cfgPath));

    // Basic HTML that displays the PNG
    panel.webview.html = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Firmware CFG</title>
        </head>
        <body>
            <h2>Control Flow Graph</h2>
            <p>CFG generated automatically during analysis.</p>
            <img src="${cfgUri}" />
        </body>
        </html>
    `;
}

export function deactivate() {
    console.log('Firmware Analysis Tool "FAT" deactivated.');
}