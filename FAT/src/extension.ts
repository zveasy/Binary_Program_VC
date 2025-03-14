import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as path from 'path';

export function activate(context: vscode.ExtensionContext) {
    console.log('Firmware Analysis Tool "FAT" is now active.');

    let disposable = vscode.commands.registerCommand('fat.analyzeFirmware', () => {
        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "Analyzing Firmware...",
            cancellable: false
        }, async () => {
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (!workspaceFolders || workspaceFolders.length === 0) {
                vscode.window.showErrorMessage('No workspace folder open.');
                return;
            }

            const workspaceRoot: vscode.WorkspaceFolder = workspaceFolders[0];
            const workspacePath: string = workspaceRoot.uri.fsPath;

            const firmwarePath = path.join(workspacePath, 'firmware', 'latest_firmware.bin');
            const reportPath = path.join(workspacePath, 'firmware', 'report.md');

            exec(`python3 rda_disassembler_enhanced.py ${firmwarePath}`, (err) => {
                if (err) {
                    vscode.window.showErrorMessage(`Firmware analysis failed: ${err.message}`);
                    return;
                }

                exec(`python3 generate_report.py firmware/disassembly.log ${reportPath}`, (reportErr) => {
                    if (reportErr) {
                        vscode.window.showErrorMessage(`Report generation failed: ${reportErr.message}`);
                    } else {
                        vscode.window.showInformationMessage('Firmware analysis completed successfully!');
                        vscode.workspace.openTextDocument(reportPath).then(doc => {
                            vscode.window.showTextDocument(doc);
                        });
                    }
                });
            });
        });
    });

    context.subscriptions.push(disposable);
}

export function deactivate() {}