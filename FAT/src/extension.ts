import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as path from 'path';

export function activate(context: vscode.ExtensionContext) {

  const disposable = vscode.commands.registerCommand('fat.analyzeFirmware', () => {

    vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: "Analyzing Firmware...", cancellable: false },
      async () => {

        // 1) Check workspace
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
          vscode.window.showErrorMessage('No workspace folder open.');
          return;
        }

        // 2) Build absolute paths
        const workspaceRoot = workspaceFolders[0];
        const workspacePath = workspaceRoot.uri.fsPath;
        
        // If rda_disassembler_enhanced.py is in the *same folder* as extension.ts, do:
        // const scriptPath = path.join(workspacePath, 'src', 'rda_disassembler_enhanced.py');
        // If it's at the top-level of your workspace folder, just do:
        const scriptPath = path.join(workspacePath, 'rda_disassembler_enhanced.py');

        const firmwarePath = path.join(workspacePath, 'firmware', 'latest_firmware.bin');
        const logPath = path.join(workspacePath, 'firmware', 'disassembly.log');
        const reportScriptPath = path.join(workspacePath, 'generate_report.py');
        const reportPath = path.join(workspacePath, 'firmware', 'report.md');

        // 3) Run the disassembler with correct working directory
        exec(`python3 "${scriptPath}" "${firmwarePath}"`, { cwd: workspacePath }, (err) => {
          if (err) {
            vscode.window.showErrorMessage(`Firmware analysis failed: ${err.message}`);
            return;
          }

          // 4) Then run the report generator
          exec(`python3 "${reportScriptPath}" "${logPath}" "${reportPath}"`, { cwd: workspacePath }, (reportErr) => {
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
      }
    );
  });

  context.subscriptions.push(disposable);
}

export function deactivate() {}