/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	var __webpack_modules__ = ([
/* 0 */
/***/ (function(__unused_webpack_module, exports, __webpack_require__) {


var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", ({ value: true }));
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(__webpack_require__(1));
const child_process_1 = __webpack_require__(2);
const path = __importStar(__webpack_require__(3));
const fs = __importStar(__webpack_require__(4));
function activate(context) {
    console.log('Firmware Analysis Tool "FAT" is now active.');
    context.subscriptions.push(vscode.commands.registerCommand('fat.analyzeFirmware', () => runAnalysisAndShowCFG()));
    context.subscriptions.push(vscode.commands.registerCommand('fat.analyzeSelectedBinary', () => runAnalysisOnSelectedBinary()));
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        return;
    }
    const workspacePath = workspaceFolders[0].uri.fsPath;
    const firmwarePath = path.join(workspacePath, 'firmware', 'latest_firmware.bin');
    if (fs.existsSync(firmwarePath)) {
        runAnalysisAndShowCFG();
    }
    else {
        vscode.window.showInformationMessage('FAT: No firmware/latest_firmware.bin found. Use "Run Firmware Analysis" or "Analyze Selected Binary..." to pick a binary.');
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
async function runAnalysisAndShowCFG(binaryPath) {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        vscode.window.showErrorMessage('No workspace folder open.');
        return;
    }
    const workspacePath = workspaceFolders[0].uri.fsPath;
    const cliPath = path.join(workspacePath, 'cli.py');
    const defaultFirmwarePath = path.join(workspacePath, 'firmware', 'latest_firmware.bin');
    const firmwarePath = binaryPath || defaultFirmwarePath;
    if (!fs.existsSync(firmwarePath)) {
        vscode.window.showErrorMessage(`Binary not found: ${firmwarePath}. Use "Analyze Selected Binary..." to pick a file.`);
        return;
    }
    const outputDir = path.join(workspacePath, 'firmware');
    const reportPath = path.join(outputDir, 'audit_report.md');
    const cfgDotPath = path.join(outputDir, 'cfg.dot');
    const cfgPngPath = path.join(outputDir, 'cfg.png');
    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'CompLexAI: Analyzing Firmware...',
        cancellable: false
    }, async () => {
        await runCommand(`python3 "${cliPath}" audit "${firmwarePath}" --output-dir "${outputDir}"`, workspacePath);
        if (fs.existsSync(cfgDotPath)) {
            await runCommand(`dot -Tpng "${cfgDotPath}" -o "${cfgPngPath}"`, workspacePath);
        }
        vscode.window.showInformationMessage('CompLexAI: Firmware audit completed!');
        showCFGWebview(cfgPngPath);
        if (fs.existsSync(reportPath)) {
            const doc = await vscode.workspace.openTextDocument(reportPath);
            await vscode.window.showTextDocument(doc, { viewColumn: vscode.ViewColumn.Beside, preview: false });
        }
    });
}
function runCommand(command, cwd) {
    return new Promise((resolve, reject) => {
        (0, child_process_1.exec)(command, { cwd }, (error, stdout, stderr) => {
            if (error) {
                vscode.window.showErrorMessage(`Command failed: ${error.message}`);
                reject(error);
            }
            else {
                resolve();
            }
        });
    });
}
function showCFGWebview(cfgPath) {
    if (!fs.existsSync(cfgPath)) {
        return;
    }
    const panel = vscode.window.createWebviewPanel('firmwareCFG', 'Firmware Control Flow Graph', vscode.ViewColumn.One, { enableScripts: true });
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
function deactivate() {
    console.log('Firmware Analysis Tool "FAT" deactivated.');
}


/***/ }),
/* 1 */
/***/ ((module) => {

module.exports = require("vscode");

/***/ }),
/* 2 */
/***/ ((module) => {

module.exports = require("child_process");

/***/ }),
/* 3 */
/***/ ((module) => {

module.exports = require("path");

/***/ }),
/* 4 */
/***/ ((module) => {

module.exports = require("fs");

/***/ })
/******/ 	]);
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		__webpack_modules__[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/************************************************************************/
/******/ 	
/******/ 	// startup
/******/ 	// Load entry module and return exports
/******/ 	// This entry module is referenced by other modules so it can't be inlined
/******/ 	var __webpack_exports__ = __webpack_require__(0);
/******/ 	module.exports = __webpack_exports__;
/******/ 	
/******/ })()
;
//# sourceMappingURL=extension.js.map