import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

export function activate(context: vscode.ExtensionContext) {
    console.log('Firmware Analysis Tool "FAT" is now active.');
    context.subscriptions.push(
        vscode.commands.registerCommand('fat.analyzeFirmware', () => runAnalysisAndShowCFG())
    );
    context.subscriptions.push(
        vscode.commands.registerCommand('fat.analyzeSelectedBinary', () => runAnalysisOnSelectedBinary())
    );

    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        return;
    }
    const workspacePath = workspaceFolders[0].uri.fsPath;
    const firmwarePath = path.join(workspacePath, 'firmware', 'latest_firmware.bin');
    if (fs.existsSync(firmwarePath)) {
        runAnalysisAndShowCFG();
    } else {
        vscode.window.showInformationMessage(
            'FAT: No firmware/latest_firmware.bin found. Use "Run Firmware Analysis" or "Analyze Selected Binary..." to pick a binary.'
        );
    }
}

async function runAnalysisOnSelectedBinary() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        vscode.window.showErrorMessage('No workspace folder open.');
        return;
    }
    const picked = await vscode.window.showOpenDialog({
        canSelectMany: false,
        openLabel: 'Select binary to analyze',
        filters: { 'Binaries': ['bin', 'elf', 'so'], 'All': ['*'] }
    });
    if (!picked || picked.length === 0) {
        return;
    }
    await runAnalysisAndShowCFG(picked[0].fsPath);
}

async function runAnalysisAndShowCFG(binaryPath?: string) {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        vscode.window.showErrorMessage('No workspace folder open.');
        return;
    }

    const workspacePath = workspaceFolders[0].uri.fsPath;
    const scriptPath = path.join(workspacePath, 'rda_disassembler_enhanced.py');
    const generateReportPath = path.join(workspacePath, 'generate_report.py');
    const defaultFirmwarePath = path.join(workspacePath, 'firmware', 'latest_firmware.bin');
    const firmwarePath = binaryPath || defaultFirmwarePath;

    if (!fs.existsSync(firmwarePath)) {
        vscode.window.showErrorMessage(`Binary not found: ${firmwarePath}. Use "Analyze Selected Binary..." to pick a file.`);
        return;
    }

    const logPath = path.join(workspacePath, 'firmware', 'disassembly.log');
    const reportPath = path.join(workspacePath, 'firmware', 'report.md');
    const cfgDotPath = path.join(workspacePath, 'firmware', 'cfg.dot');
    const cfgPngPath = path.join(workspacePath, 'firmware', 'cfg.png');

    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Analyzing Firmware...',
        cancellable: false
    }, async () => {
        await runCommand(`python3 "${scriptPath}" "${firmwarePath}"`, workspacePath);
        await runCommand(`dot -Tpng "${cfgDotPath}" -o "${cfgPngPath}"`, workspacePath);
        await runCommand(`python3 "${generateReportPath}" "${logPath}" "${reportPath}" "${cfgDotPath}"`, workspacePath);

        vscode.window.showInformationMessage('Firmware analysis completed successfully!');

        showCFGWebview(cfgPngPath);

        if (fs.existsSync(reportPath)) {
            const doc = await vscode.workspace.openTextDocument(reportPath);
            await vscode.window.showTextDocument(doc, { viewColumn: vscode.ViewColumn.Beside, preview: false });
        }
    });
}

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

function showCFGWebview(cfgPath: string) {
    if (!fs.existsSync(cfgPath)) {
        return;
    }
    const panel = vscode.window.createWebviewPanel(
        'firmwareCFG',
        'Firmware Control Flow Graph',
        vscode.ViewColumn.One,
        { enableScripts: true }
    );
    const cfgUri = panel.webview.asWebviewUri(vscode.Uri.file(cfgPath));
    panel.webview.html = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Firmware CFG</title>
        </head>
        <body>
            <h2>Control Flow Graph</h2>
            <p>CFG generated during analysis.</p>
            <img src="${cfgUri}" />
        </body>
        </html>
    `;
}

export function deactivate() {
    console.log('Firmware Analysis Tool "FAT" deactivated.');
}
